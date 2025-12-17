import os
import angr
import random
import numpy as np
import torch
import pickle
import csv
import re
from llm_client import LLMClient



REQUIREMENTS = (
    "A function belongs to the PARSER class if it satisfies ALL of the following "
    "characteristics, OR at minimum the FINAL requirement (Composition):\n"
    "1. Input Handling: The function operates on a pointer/buffer/file descriptor containing unstructured input.\n"
    "2. Internal State: It maintains internal parsing-related state across calls or during processing.\n"
    "3. Decision-Making: It performs conditional branching based on input and internal state.\n"
    "4. Data Structure Creation: It constructs or updates a data structure representing recognized input.\n"
    "5. Outcome: It produces a boolean or a built data structure as the recognition output.\n"
    "6. Composition: The function's behavior is defined as a composition of other parsers or sub-parsers.\n"
)

# Angr configuration
CALLDEPTH = 2                  # Analyzes the current function and its direct calls up to two levels deep.
CONTEXT_SENSITIVITY_LEVEL = 2  # Considers different calling contexts for functions for precise behavior analysis.
NORMALIZE = True               # Simplifies the CFG structure by removing unnecessary nodes and edges.
KEEP_STATE = True              # Preserves all input states during analysis for debugging and exploration.

def set_random_seeds(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

def extract_numeric_label(text):
    """
    Extract only a single numeric label 0 or 1 from LLM output.
    The LLM may return sentences, explanations, or formatting.
    This function isolates the first valid 0 or 1 it finds.

    Returns:
        '0', '1', or 'unknown'
    """
    if text is None:
        return "unknown"

    # Extract ALL numbers from text
    numbers = re.findall(r"\b[01]\b", text)

    if not numbers:
        return "unknown"

    # normally keep only the first occurrence
    return numbers[0]

def extract_vex_ir(func) -> str | None:
    """
    Extract a clean, continuous VEX IR string for the entire function.
    Ignores block addresses and headers, only keeps the IR instructions.
    """
    if func is None or not hasattr(func, "blocks"):
        return None

    try:
        lines = []
        for block in func.blocks:
            vex = getattr(block, "vex", None)
            if vex is None:
                continue
            for stmt in vex.statements:
                lines.append(str(stmt))

        if not lines:
            return None
        return "\n".join(lines)
    except Exception as e:
        print(f"[VEX] Extraction FAILED for function at 0x{func.addr:x}: {e}")
        return None



def get_predicted_functions(project, functions_addresses, filename, llm_client):
    """
    Analyze each function in an Angr project, extract its assembly,
    query the LLM, and return prediction dicts including real labels.
    """

    predicted_functions = []
    iteration = 1

    for name, (address, true_label) in functions_addresses.items():
        print(f"\n------------------------- ITERATION {iteration}) function name: {name} | address: {hex(address)} -------------------------")
        iteration += 1

        # Build CFG
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

        func = cfg.functions.get(address)
        if func is None:
            print(f"Function {name} not found in CFG. Skipping.")
            continue

        # ----------------------------------------------------
        # Extract Vex IR Code
        # ----------------------------------------------------
        vex_ir_code = extract_vex_ir(func)

        print(f"The VEX IR code of function {name} at {hex(address)}:\n{vex_ir_code}\n")
        
        # ----------------------------------------------------
        # LLM Classification on VEX IR Code
        # ----------------------------------------------------
        if vex_ir_code:
            prompt = (
                "You are a binary analysis assistant. I will give you the VEX IR code of a function.\n"
                "Your task is to classify whether the function is a PARSER function or not based on the following requirements.\n\n"
                f"Classification requirements:\n{REQUIREMENTS}\n\n"
                "Your output MUST follow these strict rules:\n"
                "- Output ONLY a single character: '1' if the function satisfies ALL requirements or at least the final one (Composition).\n"
                "- Output '0' if the function does NOT satisfy the criteria.\n"
                "- NO explanations.\n"
                "- NO extra text.\n"
                "- NO formatting. Only '0' or '1'.\n\n"
                f"VEX IR code:\n{vex_ir_code}\n\n"
                "Prediction (ONLY '0' or '1'):"
            )

            response = llm_client.generate(prompt)
            print(f"LLM response: {response}")
            predicted_label = extract_numeric_label(response)

        else:
            predicted_label = "unknown"

        print(f"Predicted label for function {name} at {hex(address)}: {predicted_label}")

        predicted_functions.append({
            "filename": filename,
            "function_name": name,
            "address": hex(address),
            "vex_ir_code": vex_ir_code if vex_ir_code else "",
            "predicted_label": predicted_label,
            "true_label": true_label
        })

    print("\n--------------------------------------------------------------------")
    print(f"Total predicted functions: {len(predicted_functions)}")
    return predicted_functions


def initialize_output_csv(path_csv):
    if not os.path.exists(path_csv):
        with open(path_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "filename",
                "function_name",
                "address",
                "vex_ir_code",
                "predicted_label",
                "true_label"
            ])


def append_predictions_to_csv(predictions, path_csv):
    with open(path_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        for entry in predictions:
            writer.writerow([
                entry["filename"],
                entry["function_name"],
                entry["address"],
                entry["vex_ir_code"],
                entry["predicted_label"],
                entry["true_label"],
            ])

    print(f"Appended {len(predictions)} predictions to {path_csv}")


def load_and_convert_pkl(file_path, labeled=False):
    try:
        with open(file_path, "rb") as file:
            data = pickle.load(file)

        if not isinstance(data, dict):
            raise ValueError("The loaded PKL file must contain a dictionary.")

        if labeled:
            # Convert {"foo": ("0x401000", 1)} → {"foo": (0x401000, 1)}
            converted = {k: (int(v[0], 16), int(v[1])) for k, v in data.items()}
            print(f"Loaded dictionary of {len(converted)} labeled functions.")
            return converted

        print(f"Loaded dictionary of {len(data)} functions.")
        return data

    except Exception as e:
        print(f"Error loading {file_path}: {e}")


def automatize_prediction_pipeline(path_bash_script, path_labeled_dicts, path_out_csv, llm_client):
    """
    Process all executables in the bash script,
    predict labels via LLM, save all results in one CSV.
    """

    script_dir = os.path.dirname(os.path.abspath(path_bash_script))
    dict_dir = os.path.abspath(path_labeled_dicts)

    initialize_output_csv(path_out_csv)

    executable_count = 0

    with open(path_bash_script, "r") as f:
        for line in f:
            if not (line.startswith("gcc") or line.startswith("clang")):
                continue

            tokens = line.split()
            if "-o" not in tokens:
                continue

            output_idx = tokens.index("-o") + 1
            executable_file = tokens[output_idx]
            executable_count += 1

            path_binary = os.path.join(script_dir, "Executables", executable_file)
            path_dict = os.path.join(dict_dir, executable_file + ".pkl")

            print("\n==============================")
            print(f"{executable_count}) Executable: {executable_file}")
            print(f"Binary: {path_binary}")
            print(f"Labeled dict: {path_dict}")
            print("==============================\n")

            project = angr.Project(path_binary, load_options={"auto_load_libs": False})

            # Load labeled dict: {function_name: (address, true_label)}
            functions_to_analyze = load_and_convert_pkl(path_dict, labeled=True)

            predicted_funcs = get_predicted_functions(
                project=project,
                functions_addresses=functions_to_analyze,
                filename=executable_file,
                llm_client=llm_client
            )

            append_predictions_to_csv(predicted_funcs, path_out_csv)

    print("\n------------------------------------------")
    print(f"Finished processing {executable_count} executables.")
    print("------------------------------------------")


# ===========================================================
#  ENTRY POINT
# ===========================================================

def main(path_bash_scripts, llm_client):
    OUTPUT_CSV = "../Results/llm_classification_qwen3_coder_30b/global_predictions_vex_ir_code.csv"

    for script in path_bash_scripts:
        automatize_prediction_pipeline(
            path_bash_script=script,
            path_labeled_dicts="../Dictionaries_Labeled_Datas",
            path_out_csv=OUTPUT_CSV,
            llm_client=llm_client
        )


if __name__ == "__main__":
    scripts = [
        "../Binaries/CParserXML/compile_script.sh",
        "../Binaries/picohttpparser/compile_script.sh",
        "../Binaries/CSimpleJSONParser/compile_script.sh",
        "../Binaries/cJSON/compile_script.sh",
        "../Binaries/Benoitc_HTTP_Parser/compile_script.sh",
        "../Binaries/Yacc_Calculator_tutorial/compile_script.sh",
        "../Binaries/network-packet-analyzer/compile_script.sh",
        "../Binaries/elf-parser/compile_script.sh",
        "../Binaries/pcap_parser/compile_script.sh",
        "../Binaries/Packcc/compile_script.sh",
    ]

    llm = LLMClient(model="qwen3-coder:30b") # "mistral" or "codellama:34b" or "qwen3-coder:30b"
    main(scripts, llm)
