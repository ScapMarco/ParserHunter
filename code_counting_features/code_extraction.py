import os
import pickle
import random
import csv
import re
from pathlib import Path

from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import torch
import angr

# use conda env test-3.10.0-env

# Constants
CALLDEPTH = 2                  # Analyzes the current function and its direct calls up to two levels deep.
CONTEXT_SENSITIVITY_LEVEL = 2  # Considers different calling contexts for functions for precise behavior analysis.
NORMALIZE = True               # Simplifies the CFG structure by removing unnecessary nodes and edges.
KEEP_STATE = True              # Preserves all input states during analysis for debugging and exploration.


# --- small textual heuristics used to compute PARC3-like features from vex_ir + decompiled_c ---
HEX_RE = re.compile(r'0x[0-9a-fA-F]+')
BLOCK_HEADER_RE = re.compile(r'---\s*BLOCK\s*(0x[0-9a-fA-F]+)\s*---')
SWITCH_RE = re.compile(r'\bswitch\b', re.IGNORECASE)
CASE_RE = re.compile(r'\bcase\b', re.IGNORECASE)
IF_RE = re.compile(r'\bif\s*\(', re.IGNORECASE)
LOOP_RE = re.compile(r'\b(for|while)\s*\(|\bdo\s*\{', re.IGNORECASE)

def _safe_str(s):
    return "" if s is None or (isinstance(s, float) and np.isnan(s)) else str(s)

def _count_block_headers(vex_ir_text: str) -> int:
    if not vex_ir_text:
        return 0
    return len(BLOCK_HEADER_RE.findall(vex_ir_text))

def _detect_switch(decompiled_c: str, vex_ir: str) -> bool:
    d = _safe_str(decompiled_c)
    v = _safe_str(vex_ir)
    if SWITCH_RE.search(d):
        return True
    if CASE_RE.search(d):
        return True
    if re.search(r'\b(jump table|jumptable|indirect_jump|indirect jmp)\b', v, re.IGNORECASE):
        return True
    return False

def _detect_loop_from_text(decompiled_c: str, vex_ir: str) -> bool:
    d = _safe_str(decompiled_c)
    v = _safe_str(vex_ir)
    if LOOP_RE.search(d):
        return True
    # simple VEX heuristic: presence of goto/jump to earlier block address
    headers = BLOCK_HEADER_RE.findall(v)
    if len(headers) >= 2:
        # if any hex address referenced in VEX equals an earlier header, guess a loop exists
        header_addrs = [int(h, 16) for h in headers]
        all_targets = [int(x, 16) for x in HEX_RE.findall(v)]
        # if any target points to a header earlier in order, treat as loop (heuristic)
        if any(t in header_addrs for t in all_targets):
            return True
    # fallback: 'goto' presence plus multiple addresses
    if re.search(r'\bgoto\b', v, re.IGNORECASE) and len(HEX_RE.findall(v)) >= 2:
        return True
    return False

def _compute_br_fact_from_decompiled(decompiled_c: str, vex_ir: str) -> int:
    d = _safe_str(decompiled_c)
    v = _safe_str(vex_ir)
    br_candidates = []
    # if-statements -> at least 2 branches
    if IF_RE.search(d):
        br_candidates.append(2)
    # else-if increases branching
    else_if_count = len(re.findall(r'\belse\s+if\s*\(', d, re.IGNORECASE))
    if else_if_count > 0:
        br_candidates.append(2 + else_if_count)
    # switch -> number of cases
    if SWITCH_RE.search(d) or re.search(r'\bswitch\b', v, re.IGNORECASE):
        num_cases = len(CASE_RE.findall(d))
        if num_cases > 0:
            br_candidates.append(num_cases)
        else:
            if re.search(r'jumptable|jump table|indirect_jump', v, re.IGNORECASE):
                br_candidates.append(4)  # heuristic guess
    return int(max(br_candidates)) if br_candidates else 0

def _count_callers_in_decompiled(all_decompiled: List[str], target_fullname: str) -> int:
    """
    Count occurrences of the function being called in other decompiled bodies.
    Use both full name and short name (after last dot) heuristics.
    """
    shortname = target_fullname.split('.')[-1] if isinstance(target_fullname, str) and '.' in target_fullname else target_fullname
    patt_short = re.compile(r'\b' + re.escape(shortname) + r'\s*\(', re.IGNORECASE)
    patt_full = re.compile(r'\b' + re.escape(target_fullname) + r'\s*\(', re.IGNORECASE)
    cnt = 0
    for body in all_decompiled:
        if not body:
            continue
        if patt_short.search(body) or patt_full.search(body):
            cnt += 1
    return cnt

def load_and_convert_pkl(file_path, label=False):
    try:
        with open(file_path, 'rb') as file:
            data = pickle.load(file)

            # Check if the loaded data is a dictionary
            if not isinstance(data, dict):
                raise ValueError("The loaded data is not a dictionary.")

            if label:
                # Assuming data is a dictionary with string keys and (hex, int) values
                converted_data = {key: ( int(value[0], 16), int(value[1]) ) for key, value in data.items()}
                print(f"Loaded dictionary of {len(converted_data)} functions!")    
                return converted_data
            else:
                print(f"Loaded dictionary of {len(data)} functions!")    
                return data

            
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"Error: {e}")


def extract_vex_from_function(project: angr.Project, cfg: angr.analyses.CFGEmulated, address: int) -> List[Dict[str, Any]]:
    """
    Extract VEX (IRSB) for each basic block of the function starting at `address`.
    Returns a list of dicts: [{"addr": block_addr, "irsb": vex_text}, ...]
    Errors are handled per-block; failures won't stop the function.
    """
    results: List[Dict[str, Any]] = []

    # try to retrieve function via CFG knowledgebase first (safer)
    func = cfg.kb.functions.get(address, None)
    if func is None:
        print(f"Function at address {hex(address)} not found.")
        return None

    for block in getattr(func, "blocks", []): # in func.blocks we have the basic blocks
        try:
            irsb = project.factory.block(block.addr).vex  # Get the VEX IR block (IRSB)
            # Convert the IRSB to a string representation 
            block_text = str(irsb)
        except Exception as e:
            # if we can't build the block or VEX, record the error text for that block
            block_text = f"<ERROR extracting block {hex(block.addr)}: {e}>"
            print(f"[extract_vex_from_function] Warning: failed to extract block {hex(block.addr)}: {e}")

        results.append({"addr": block.addr, "irsb": block_text})

    return results


def extract_code_data(project: angr.Project,
                      functions_addresses: Dict[str, Tuple[int, Optional[Any]]],
                      dictionary_labeled: bool = True) -> List[Dict[str, Any]]:
    """
    For each function entry in functions_addresses (mapping name -> (address, label) if labeled),
    extract:
      - decompiled C (string)
      - per-block VEX IRSBs (list of dicts with addr & irsb text)
      - a combined vex_ir string (all blocks joined with a separator)
    Returns a list of dicts, one per function, containing keys:
      ["file_name", "name", "address", "label", "vex_blocks", "vex_ir_code",
       "decompiled_c_code", "num_blocks", "success", "error_message"]
    """
    extracted: List[Dict[str, Any]] = []
    iteration = 0

    for name, value in functions_addresses.items():
        if dictionary_labeled:
            address, label = value
        else:
            address = value
            label = None

        print(f"\n--- ITER {iteration} | Name: {name} | Addr: {hex(address)} -----------------------------------------------------------")
        iteration += 1

        entry: Dict[str, Any] = {
            "name": name,
            "address": address,
            "label": label,
            "vex_blocks": [],
            "vex_ir_code": "",
            "decompiled_c_code": "",
            "num_blocks": 0,
            "success": False,
            "error_message": None,
        }

        try:
            start_state = project.factory.blank_state(
                addr=address,
                state_add_options=angr.options.ZERO_FILL_UNCONSTRAINED_REGISTERS
            )

            cfg = project.analyses.CFGEmulated(
                starts=[address],
                initial_state=start_state,
                context_sensitivity_level=CONTEXT_SENSITIVITY_LEVEL,
                normalize=NORMALIZE,
                call_depth=CALLDEPTH,
                state_add_options=angr.options.refs,
                keep_state=KEEP_STATE
            )

            # Retrieve the function you want to decompile (by name or address)
            func = cfg.functions[address]
            # Extract Decompile code
            try:
                # Run the experimental decompiler analysis on the function
                # to extract the decompiled pseudo C code
                decompiler = project.analyses.Decompiler(func)
                decompiled_text = decompiler.codegen.text if getattr(decompiler, "codegen", None) else ""
                entry["decompiled_c_code"] = decompiled_text
                print(f"[decompiler] extracted len: {len(decompiled_text)}")
            except Exception as decomp_err:
                entry["decompiled_c_code"] = ""
                print(f"[decompiler] Warning: decompiler failed for {name}@{hex(address)}: {decomp_err}")

            # Extract VEX IR blocks
            try:
                vex_blocks = extract_vex_from_function(project, cfg, address)
                entry["vex_blocks"] = vex_blocks
                entry["num_blocks"] = len(vex_blocks)

                # Create a combined textual representation for CSV storage
                combined_blocks = []
                for b in vex_blocks:
                    combined_blocks.append(f"--- BLOCK {hex(b['addr'])} ---\n{b['irsb']}")
                entry["vex_ir_code"] = "\n\n".join(combined_blocks)
                print(f"[vex] extracted num blocks: {entry['num_blocks']}")
            except Exception as vex_err:
                entry["vex_blocks"] = []
                entry["vex_ir_code"] = f"<ERROR extracting vex blocks: {vex_err}>"
                entry["num_blocks"] = 0
                print(f"[vex] Warning: failed to extract vex for {name}@{hex(address)}: {vex_err}")

            # mark as success if at least one piece of data extracted
            entry["success"] = bool(entry["decompiled_c_code"] or entry["num_blocks"] > 0)
        except Exception as e:
            # top-level function extraction error
            entry["error_message"] = str(e)
            print(f"[extract_code_data] ERROR extracting function {name}@{hex(address)}: {e}")

        extracted.append(entry)

    return extracted


def create_and_save_extracted_datas_list(path_binary: str,
                                         path_dictionary: str,
                                         path_output_file: str) -> List[Dict[str, Any]]:
    """
    Extracts VEX + decompiled C for each function, computes PARC3-like textual features,
    and APPENDS the results as rows into a single CSV file at path_output_file.
    Returns the list of extracted entries (each entry now contains the new feature fields).
    """
    # reproducibility seeds
    torch.manual_seed(42)
    random.seed(42)
    np.random.seed(42)

    # Create Angr project (do not auto-load libs)
    project = angr.Project(thing=path_binary, load_options={"auto_load_libs": False})
    file_name = os.path.basename(path_binary)

    # Load the dictionary (assumes load_and_convert_pkl exists and returns name->(addr,label) if label=True)
    functions_to_analyze = load_and_convert_pkl(path_dictionary, label=True)

    # Extract data (list of dicts)
    extracted_datas = extract_code_data(project=project,
                                       functions_addresses=functions_to_analyze,
                                       dictionary_labeled=True)

    # Add file_name to each entry so CSV shows source executable
    for e in extracted_datas:
        e["file_name"] = file_name

    # Precompute list of decompiled bodies to estimate call counts (within this binary)
    all_decompiled = [_safe_str(e.get("decompiled_c_code", "")) for e in extracted_datas]

    # Compute PARC3-like features from textual data and add them into each entry
    for e in extracted_datas:
        try:
            vex_text = _safe_str(e.get("vex_ir_code", ""))
            decomp_text = _safe_str(e.get("decompiled_c_code", ""))

            # bb_cnt: prefer existing num_blocks field if valid, else count headers
            nb = None
            try:
                nb_val = e.get("num_blocks", None)
                if nb_val is not None and str(nb_val).strip() != "":
                    nb = int(nb_val)
            except Exception:
                nb = None
            if nb is None or nb <= 0:
                nb = _count_block_headers(vex_text) or 0
            e["bb_cnt_parc3"] = int(nb)

            # switch detection
            has_switch = _detect_switch(decomp_text, vex_text)
            e["switch_parc3"] = 1 if has_switch else 0

            # loop detection and switch_loop
            has_loop = _detect_loop_from_text(decomp_text, vex_text)
            e["switch_loop_parc3"] = 1 if (has_switch and has_loop) else 0

            # br_fact
            e["br_fact_parc3"] = int(_compute_br_fact_from_decompiled(decomp_text, vex_text))

            # in_edges: heuristic = max frequency of referenced hex addrs in vex text
            addr_counts = {}
            for h in HEX_RE.findall(vex_text):
                addr_counts[h] = addr_counts.get(h, 0) + 1
            e["in_edges_parc3"] = int(max(addr_counts.values())) if addr_counts else 0

            # call_cnt: approximate by scanning other decompiled bodies in this extracted_datas
            fullname = e.get("name", "")
            # exclude self when counting
            other_decompiled = [b for b in all_decompiled if b != decomp_text]
            e["call_cnt_parc3"] = int(_count_callers_in_decompiled(other_decompiled, fullname))

            e["feat_error"] = None
        except Exception as ex:
            e["bb_cnt_parc3"] = 0
            e["switch_parc3"] = 0
            e["switch_loop_parc3"] = 0
            e["br_fact_parc3"] = 0
            e["in_edges_parc3"] = 0
            e["call_cnt_parc3"] = 0
            e["feat_error"] = str(ex)

    # Ensure output directory exists
    out_path = Path(path_output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # CSV fields (store combined vex_ir_code and decompiled_c_code) + new PARC3 columns
    csv_fieldnames = [
        "file_name", "name", "address", "label",
        "num_blocks", "bb_cnt_parc3", "call_cnt_parc3", "in_edges_parc3",
        "br_fact_parc3", "switch_parc3", "switch_loop_parc3",
        "success", "error_message", "feat_error",
        "vex_ir", "decompiled_c"
    ]

    # If file doesn't exist, write header; otherwise append rows
    file_exists = os.path.exists(path_output_file)

    with open(path_output_file, mode="a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_fieldnames, quoting=csv.QUOTE_ALL)
        if not file_exists:
            writer.writeheader()

        rows_written = 0
        for entry in extracted_datas:
            writer.writerow({
                "file_name": file_name,
                "name": entry.get("name"),
                "address": hex(entry.get("address")) if entry.get("address") is not None else "",
                "label": entry.get("label"),
                "num_blocks": entry.get("num_blocks", 0),
                "bb_cnt_parc3": entry.get("bb_cnt_parc3", 0),
                "call_cnt_parc3": entry.get("call_cnt_parc3", 0),
                "in_edges_parc3": entry.get("in_edges_parc3", 0),
                "br_fact_parc3": entry.get("br_fact_parc3", 0),
                "switch_parc3": entry.get("switch_parc3", 0),
                "switch_loop_parc3": entry.get("switch_loop_parc3", 0),
                "success": entry.get("success", False),
                "error_message": entry.get("error_message", ""),
                "feat_error": entry.get("feat_error", ""),
                "vex_ir": entry.get("vex_ir_code", ""),
                "decompiled_c": entry.get("decompiled_c_code", ""),
            })
            rows_written += 1

    print(f"[+] Appended {rows_written} rows from '{file_name}' (with PARC3 features) to: {path_output_file}")

    # return structured data for further programmatic use
    return extracted_datas


def automatize_create_and_save_extracted_datas_list(path_bash_script, path_labeled_dictionaries, path_out_files, combined_filename="combined_extracted.csv"):
    """
    For each executable referenced in path_bash_script, extract its functions
    and append the rows to the single CSV file (path_out_files/combined_filename).
    """
    script_dir = os.path.dirname(os.path.abspath(path_bash_script))
    dictionary_dir = os.path.abspath(path_labeled_dictionaries)
    out_files_dir = os.path.abspath(path_out_files)
    executable_count = 0

    # Combined CSV path for this run (all executables processed by this script will append here)
    combined_csv_path = os.path.join(out_files_dir, combined_filename)
    # Ensure output directory exists (create now so create_and_save... can assume it exists)
    os.makedirs(out_files_dir, exist_ok=True)

    # Read the bash script file
    with open(path_bash_script, 'r') as file:
        for line in file:
            if line.startswith('gcc') or line.startswith('clang'):
                tokens = line.split()
                # Find the index of the '-o' option
                output_index = tokens.index('-o') + 1 if '-o' in tokens else -1
                if output_index != -1 and output_index < len(tokens):
                    executable_count += 1
                    # Extract the executable file name
                    executable_file = tokens[output_index]
                    # Create the full path to the executable
                    path_binary = os.path.join(script_dir, 'Executables', executable_file)
                    # Create the dictionary file name
                    dictionary_file = executable_file + '.pkl'
                    # Create the full path to the labeled dictionary
                    path_dictionary = os.path.join(dictionary_dir, dictionary_file)

                    print()
                    print(f"AUTOMATIZE CREATE AND SAVE EXTRACTED LLVM DATAS LIST --------------------------------")
                    print(f"{executable_count}) executable file name: {executable_file}")
                    print(f"    {executable_count}) executable path: {path_binary}")
                    print(f"    {executable_count}) labeled dictionary path: {path_dictionary}")
                    print(f"    Appending rows to combined CSV: {combined_csv_path}")
                    print()

                    # Call the extractor which appends rows to the central CSV
                    try:
                        create_and_save_extracted_datas_list(path_binary=path_binary,
                                                            path_dictionary=path_dictionary,
                                                            path_output_file=combined_csv_path)
                    except Exception as e:
                        print(f"[automatize] ERROR extracting {executable_file}: {e}")

    print()
    print(f"END AUTOMATIZE CREATE AND SAVE GEOMETRIC DATAS LIST --------------------------------")
    print(f"    Total executables processed in script {os.path.basename(path_bash_script)}: {executable_count}")
    print(f"    Combined CSV location: {combined_csv_path}")

    
########################################################################################################################################################################################################################

def main(path_bash_scripts):
    for path_bash_script in path_bash_scripts:
        automatize_create_and_save_extracted_datas_list(
            path_bash_script=path_bash_script, 
            path_labeled_dictionaries="./Dictionaries_Labeled_Datas",
            path_out_files="./llvm_counting_features/outputs",
        )


if __name__ == "__main__":
    # Path to the bash scripts
    path_bash_scripts = [
        "./Binaries/CParserXML/compile_script.sh",
        "./Binaries/picohttpparser/compile_script.sh",
        "./Binaries/CSimpleJSONParser/compile_script.sh",
        "./Binaries/cJSON/compile_script.sh",
        "./Binaries/Benoitc_HTTP_Parser/compile_script.sh",
        "./Binaries/Yacc_Calculator_tutorial/compile_script.sh",   
        "./Binaries/network-packet-analyzer/compile_script.sh",
        "./Binaries/elf-parser/compile_script.sh",
        "./Binaries/pcap_parser/compile_script.sh",
        "./Binaries/Packcc/compile_script.sh",
    ]
    main(path_bash_scripts)