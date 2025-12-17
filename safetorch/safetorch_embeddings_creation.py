import sys
import os
import csv
import torch
import random
import pickle
import angr
import yaml
import numpy as np
from typing import Dict, Tuple, Optional
from pathlib import Path

from utils.function_normalizer import FunctionNormalizer
from utils.instructions_converter import InstructionsConverter
from utils.capstone_disassembler import disassemble
from safetorch.safe_network import SAFE
from safetorch.parameters import Config

# use conda env safe37

# Constants
CALLDEPTH = 2                  # Analyzes the current function and its direct calls up to two levels deep.
CONTEXT_SENSITIVITY_LEVEL = 2  # Considers different calling contexts for functions for precise behavior analysis.
NORMALIZE = True               # Simplifies the CFG structure by removing unnecessary nodes and edges.
KEEP_STATE = True              # Preserves all input states during analysis for debugging and exploration.



def set_random_seeds(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def load_and_convert_pkl(file_path, label=False):
    try:
        with open(file_path, 'rb') as file:
            data = pickle.load(file)

            # Check if the loaded data is a dictionary
            if not isinstance(data, dict):
                raise ValueError("The loaded data is not a dictionary.")

            filename = os.path.basename(file_path)

            if label:
                # Assuming data is a dictionary with string keys and (hex, int) values
                converted_data = {
                    key: (int(value[0], 16), int(value[1]), filename)
                    for key, value in data.items()
                }
                print(f"Loaded dictionary of {len(converted_data)} functions!")    
                return converted_data
            else:
                # If not labeled, still attach filename to each item
                converted_data = {
                    key: (value[0], filename) if isinstance(value, tuple) else (value, filename)
                    for key, value in data.items()
                }
                print(f"Loaded dictionary of {len(converted_data)} functions!")    
                return converted_data

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"Error: {e}")



def init_safe_model(
    model_path: str,
    vocab_path: str,
    max_instruction: int,
    device: torch.device
) -> Tuple[SAFE, InstructionsConverter, FunctionNormalizer]:
    cfg = Config()
    net = SAFE(cfg).to(device)
    sd = torch.load(model_path, map_location=device)
    net.load_state_dict(sd)
    net.eval()
    conv = InstructionsConverter(vocab_path)
    norm = FunctionNormalizer(max_instruction=max_instruction)
    return net, conv, norm


def embed_function(
    asm_bytes: bytes,
    arch: str,
    bits: int,
    net: SAFE,
    conv: InstructionsConverter,
    norm: FunctionNormalizer,
    device: torch.device
) -> torch.Tensor:
    # disassemble
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_MODE_64
        mode = CS_MODE_64 if bits == 64 else CS_MODE_32
        md = Cs(CS_ARCH_X86, mode)
        instrs = [f"{insn.mnemonic} {insn.op_str}".strip() for insn in md.disasm(asm_bytes, 0)]
        if not instrs:
            raise RuntimeError
    except Exception:
        instrs = disassemble(asm_bytes.hex(), arch, bits) or []
    if not instrs:
        raise RuntimeError("No instructions")
    ids = conv.convert_to_ids(instrs)
    padded, lengths = norm.normalize_functions([ids])
    seq = padded[0]
    length0 = int(lengths[0])
    tensor = torch.LongTensor(seq).to(device)
    with torch.no_grad():
        emb = net(tensor, [length0])
    return emb.squeeze(0).cpu()

def append_embeddings_to_csv(
    results: Dict[str, Tuple[str, int, Optional[int], torch.Tensor]],
    csv_path: Path
):
    """
    Append one executable’s embeddings to a CSV.
    Columns: exe,name,filename,address,label,emb_0,...,emb_{D-1}
    """
    # Determine embedding dimension from first entry
    first_emb = next(iter(results.values()))[3]
    D = first_emb.shape[0]

    # Prepare CSV header
    fieldnames = ["filename", "name", "address", "label"] + [f"emb_{i}" for i in range(D)]
    file_exists = csv_path.exists()

    # Ensure out dir exists
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        for name, (filename, addr, label, emb) in results.items():
            row = {
                "filename": filename,
                "name": name,
                "address": addr,
                "label": label
            }
            # Flatten embedding
            for i, v in enumerate(emb.tolist()):
                row[f"emb_{i}"] = v
            writer.writerow(row)

    print(f"Appended {len(results)} rows to {csv_path}")

def extract_and_save(
    exe_path: Path,
    dict_path: Path,
    net: SAFE,
    conv: InstructionsConverter,
    norm: FunctionNormalizer,
    device: torch.device,
    out_dir: Path,
):
    # load mapping
    mapping = load_and_convert_pkl(str(dict_path), label=True)
    # run embeddings
    proj = angr.Project(str(exe_path), load_options={"auto_load_libs": False})
    results = {}

    for i, (name, info) in enumerate(mapping.items()):
        address, label, filename = info

        print(f"--- ITER {i}: {name} @0x{address:x} ({filename}), label={label}")

        # Initialize blank state
        state = proj.factory.blank_state(
            addr=address, 
            state_add_options=angr.options.ZERO_FILL_UNCONSTRAINED_REGISTERS
        )

        # Build CFG for the function
        cfg = proj.analyses.CFGEmulated(
            starts=[address], 
            initial_state=state, 
            context_sensitivity_level=CONTEXT_SENSITIVITY_LEVEL, 
            normalize=NORMALIZE, 
            call_depth=CALLDEPTH, 
            state_add_options=angr.options.refs, 
            keep_state=KEEP_STATE
        )  
        # Extract raw bytes via CFG basic blocks rather than contiguous memory
        func_cfg = cfg.kb.functions.get(address)

        raw_bytes = bytearray()
        for block in func_cfg.blocks:
            try:
                raw_bytes.extend(block.bytes)
            except KeyError as e:
                print(f"Warning: skipping block at {hex(block.addr)} due to missing memory: {e}")
                continue
        raw = bytes(raw_bytes)
        if not raw:
            print(f"Warning: no raw bytes extracted for {name}, skipping.")
            continue

        # Embedding the function
        emb = embed_function(
            raw, proj.arch.name, proj.arch.bits,
            net, conv, norm, device
        )
        print(f"emb shape: {emb.shape}")
        # Store results
        results[name] = (filename, address, label, emb)
    
    # Save to a CSV file:
    csv_file = out_dir / "all_function_embeddings.csv"
    append_embeddings_to_csv(results, csv_file)


def safetorch_batch_embeddings(paths_executables, path_labeled_dictionaries):
    set_random_seeds(42)
    device = "cpu"
    # Initialize the SAFE model and its components
    net, conv, norm = init_safe_model(
        model_path="./safetorch/model/SAFEtorch.pt", 
        vocab_path="./safetorch/model/word2id.json",
        max_instruction=150, 
        device=device
    )

    # Process each executable
    out_dir = Path("./safetorch/outputs/")
    out_dir.mkdir(parents=True, exist_ok=True)
    for exe_dir in paths_executables:
        exe_dir = Path(exe_dir)
        for exe_file in exe_dir.iterdir():
            if not exe_file.is_file() or exe_file.stat().st_mode & 0o111 == 0:
                continue  # skip non-executables
            dict_file = Path(path_labeled_dictionaries) / (exe_file.name + ".pkl")
            if not dict_file.exists():
                continue
            print(f"Processing {exe_file} with dict {dict_file} --------------------------------------")
            # Extract and save embeddings
            extract_and_save(
                exe_path=exe_file, 
                dict_path=dict_file,
                net=net, 
                conv=conv, 
                norm=norm, 
                device=device,
                out_dir=out_dir
            )

if __name__ == "__main__":
    
    # Paths to executables to process
    paths_executables = [
        "./Binaries/CParserXML/Executables",
        "./Binaries/picohttpparser/Executables",
        "./Binaries/CSimpleJSONParser/Executables",
        "./Binaries/cJSON/Executables",
        "./Binaries/Benoitc_HTTP_Parser/Executables",
        "./Binaries/Yacc_Calculator_tutorial/Executables",   
        "./Binaries/network-packet-analyzer/Executables",
        "./Binaries/elf-parser/Executables",
        "./Binaries/pcap_parser/Executables",
        "./Binaries/Packcc/Executables",
    ]
    # Path to labeled dictionaries
    path_labeled_dictionaries = "./Dictionaries_Labeled_Datas/"
    # Run the Safetorch embeddings
    safetorch_batch_embeddings(paths_executables, path_labeled_dictionaries)
