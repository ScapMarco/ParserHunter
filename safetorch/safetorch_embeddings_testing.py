import sys
import os
import torch
import random
import pickle 
import angr
import numpy as np
from typing import List, Dict, Tuple, Optional
from utils.function_normalizer import FunctionNormalizer
from utils.instructions_converter import InstructionsConverter
from utils.capstone_disassembler import disassemble
from safetorch.safe_network import SAFE
from safetorch.parameters import Config

# Add the parent directory to the path for module resolution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.utils import load_config

# use conda env safe37

def set_random_seeds(seed=42):
    """Sets random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def load_and_convert_pkl_with_name(
    file_path: str,
    label: bool = False
) -> Dict[str, Tuple]:
    """
    Load a pickled dict of functions and convert entries:
    - If label=True: values are (hex_str, numeric_label)
      -> returns {name: (address_int, float_label, filename)}
    - Else: values are address or tuple with address
      -> returns {name: (address_int_or_tuple, filename)}
    """
    try:
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
        if not isinstance(data, dict):
            raise ValueError("The loaded data is not a dictionary.")

        filename = os.path.basename(file_path)
        converted = {}
        if label:
            for key, value in data.items():
                addr_hex, lbl = value
                addr = int(addr_hex, 16)
                converted[key] = (addr, float(lbl), filename)
        else:
            for key, value in data.items():
                if isinstance(value, tuple):
                    addr = value[0]
                else:
                    addr = value
                converted[key] = (addr, filename)

        print(f"Loaded dictionary of {len(converted)} functions from {filename}!")
        return converted

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return {}
    except Exception as e:
        print(f"Error loading dict: {e}")
        return {}
    

def init_safe_model(
    model_path: str,
    vocab_path: str,
    max_instruction: int = 150,
    device: torch.device = torch.device('cpu')
) -> Tuple[SAFE, InstructionsConverter, FunctionNormalizer]:
    config = Config()
    safe_net = SAFE(config).to(device)
    state_dict = torch.load(model_path, map_location=device)
    safe_net.load_state_dict(state_dict)
    safe_net.eval()

    converter = InstructionsConverter(vocab_path)
    normalizer = FunctionNormalizer(max_instruction=max_instruction)

    return safe_net, converter, normalizer

def embed_function(
    asm_bytes: bytes,
    arch: str,
    bits: int,
    safe_net: SAFE,
    converter: InstructionsConverter,
    normalizer: FunctionNormalizer,
    device: torch.device = torch.device('cpu')
) -> torch.Tensor:
    """
    Disassemble raw bytes via Capstone (with fallback to utils.disassemble),
    normalize to fixed-length, then embed via SAFE.
    """
    # 1) Disassemble
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_MODE_64
        mode = CS_MODE_64 if bits == 64 else CS_MODE_32
        md = Cs(CS_ARCH_X86, mode)
        instructions = []
        for insn in md.disasm(asm_bytes, 0):
            txt = insn.mnemonic
            if insn.op_str:
                txt += " " + insn.op_str
            instructions.append(txt)
        if not instructions:
            raise RuntimeError("Capstone returned no instructions")
    except Exception:
        hex_str = asm_bytes.hex()
        instructions = disassemble(hex_str, arch, bits) or []

    if not instructions:
        raise RuntimeError("Failed to disassemble function bytes")

    # 2) Convert & normalize
    ids = converter.convert_to_ids(instructions)
    padded, lengths = normalizer.normalize_functions([ids])

    # 3) Prepare inputs for SAFE
    seq = padded[0]           # Python list of length max_instruction
    length0 = lengths[0]      # Python int
    tensor = torch.LongTensor(seq).to(device)    # shape (max_instruction,)
    length_list = [int(length0)]                 # list of one int

    # 4) Embed
    with torch.no_grad():
        emb = safe_net(tensor, length_list)

    return emb.squeeze(0).cpu()


def extract_embeddings(
    binary_path: str,
    safe_net: SAFE,
    converter: InstructionsConverter,
    normalizer: FunctionNormalizer,
    device: torch.device = torch.device('cpu'),
    dict_functions: Optional[Dict[str, Tuple[int, Optional[int], str]]] = None,
    dictionary_labeled: bool = False,
    context_sensitivity_level: int = 2,
    normalize: bool = True,
    call_depth: int = 2,
    keep_state: bool = True
) -> Dict[str, Tuple[int, Optional[int], torch.Tensor]]:
    proj = angr.Project(binary_path, load_options={"auto_load_libs": False})
    results: Dict[str, Tuple[int, Optional[int], torch.Tensor]] = {}

    print(f"Extracting embeddings for {len(dict_functions)} functions...")
    for i, (name, info) in enumerate(dict_functions.items()):
        if dictionary_labeled:
            address, label, filename = info
        else:
            address, filename = info
            label = None

        print(f"--- ITER {i}: {name} @0x{address:x} ({filename}), label={label}")

        # Initialize blank state
        start_state = proj.factory.blank_state(
            addr=address, 
            state_add_options=angr.options.ZERO_FILL_UNCONSTRAINED_REGISTERS
        )

        # Build CFG for the function
        cfg = proj.analyses.CFGEmulated(
            starts=[address], 
            initial_state=start_state, 
            context_sensitivity_level=context_sensitivity_level, 
            normalize=normalize, 
            call_depth=call_depth, 
            state_add_options=angr.options.refs, 
            keep_state=keep_state
        )  
        # Extract raw bytes via CFG basic blocks rather than contiguous memory
        func_cfg = cfg.kb.functions.get(address)
        raw_bytes = bytearray()
        for block in func_cfg.blocks:
            # Each block is an angr.block.Block
            raw_bytes.extend(block.bytes)
        raw = bytes(raw_bytes)

        print(f"Disassembled {name}, concatenated {len(raw)} raw bytes")

        # Embed
        emb = embed_function(
            raw, proj.arch.name, proj.arch.bits,
            safe_net, converter, normalizer, device
        )
        print(f"Function {name} embedding shape: {emb.shape}")
        results[name] = (filename, address, label, emb)

    return results

def save_embeddings(
    embeddings: Dict[str, Tuple[str, int, Optional[int], torch.Tensor]],
    out_path: str
) -> None:
    """
    embeddings: dict of
      name -> (filename, address, label, embedding_tensor)
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    names, filenames, addresses, labels, embs = [], [], [], [], []
    for name, (filename, addr, label, emb) in embeddings.items():
        names.append(name)
        filenames.append(filename)
        addresses.append(addr)
        labels.append(label)
        embs.append(emb)

    data = {
        'names': names,
        'filenames': filenames,
        'addresses': addresses,
        'labels': labels,
        'embeddings': torch.stack(embs)
    }
    torch.save(data, out_path)
    print(f"Saved {len(names)} embeddings to {out_path}")
   


def safetorch_embeddings(angr_config, safetorch_config):
    """Trains and tests the MLP model using GridSearchCV."""
    # Load Angr configuration
    calldepth = angr_config["calldepth"]
    context_sensitivity_level = angr_config["context_sensitivity_level"]
    normalize = angr_config["normalize"]
    keep_state = angr_config["keep_state"]

    # Load SafeTorch configuration
    model_path = safetorch_config["model_path"]
    vocab_path = safetorch_config["vocab_path"]
    max_instruction = safetorch_config["max_instruction"]
    device = safetorch_config["device"]
    output_path = safetorch_config["output_path"]

    path_labeled_dictionaries = safetorch_config["path_labeled_dictionaries"]
    paths_executables = safetorch_config["paths_executables"]


    safe_net, converter, normalizer = init_safe_model(
        model_path, vocab_path, max_instruction=max_instruction, device=device
    )


    # Load datasets
    train_datasets = load_and_convert_pkl_with_name(file_path=, label=True)

    embeddings = extract_embeddings(
        binary_path,
        safe_net,
        converter,
        normalizer,
        device,
        dict_functions=dict_functions,
        dictionary_labeled=True,
        context_sensitivity_level=context_sensitivity_level,
        normalize=normalize,
        call_depth=calldepth,
        keep_state=keep_state
    )

    save_embeddings(embeddings, output_path)



def main():
    """Main execution function."""
    # Set the seed value for replicability
    set_random_seeds(seed=42)
    # Load the configuration files
    config = load_config("config/config.yaml")
    angr_config = config["angr_analysis"]           # Load data config
    safetorch_config = config["safetorch"]      # Load safetorch config

    # Make embeddings using the trained safetorch model
    safetorch_embeddings(angr_config, safetorch_config)
    

if __name__ == "__main__":
    main()

# Loaded 10 training datasets.
#   - ./data/processed/pikle_datas/training_pikle_datas/benoitc_HTTP: 267 functions
#   - ./data/processed/pikle_datas/training_pikle_datas/cJSON: 1991 functions
#   - ./data/processed/pikle_datas/training_pikle_datas/cparserXML: 289 functions
#   - ./data/processed/pikle_datas/training_pikle_datas/csimpleJSONparser: 531 functions
#   - ./data/processed/pikle_datas/training_pikle_datas/picohttpparser: 705 functions
#   - ./data/processed/pikle_datas/training_pikle_datas/yacc_calculator_tutorial: 239 functions
#   - ./data/processed/pikle_datas/training_pikle_datas/elf_parser: 493 functions
#   - ./data/processed/pikle_datas/training_pikle_datas/network_packet_analyzer: 354 functions
#   - ./data/processed/pikle_datas/training_pikle_datas/packcc: 1604 functions
#   - ./data/processed/pikle_datas/training_pikle_datas/pcap_parser: 266 functions
