import os
import pickle
from typing import List, Dict, Tuple, Optional

import angr
import torch

from utils.function_normalizer import FunctionNormalizer
from utils.instructions_converter import InstructionsConverter
from utils.capstone_disassembler import disassemble
from safetorch.safe_network import SAFE
from safetorch.parameters import Config



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
    

def main():
    # Paths for binary file
    bin_path = "/home/marcos/Projects/Continuous_Parserhunter/data/raw/binaries/yacc_calculator_tutorial/Executables/"
    BINARY_PATH = bin_path + "calc"
    # Pickle path for function dictionary
    pkl_path = "/home/marcos/Projects/Continuous_Parserhunter/data/processed/dicts_functions/dict_list_labeled_functions/"
    PKL_PATH = pkl_path + "calc.pkl" 

    MODEL_PATH = "safetorch/model/SAFEtorch.pt"
    VOCAB_PATH = "safetorch/model/word2id.json"
    OUTPUT_PATH = "safetorch/outputs/function_embeddings.pt"
    MAX_INSTRUCTION = 150
    DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # Load function list (with labels)
    dict_functions = load_and_convert_pkl_with_name(PKL_PATH, label=True)

    safe_net, converter, normalizer = init_safe_model(
        MODEL_PATH, VOCAB_PATH, max_instruction=MAX_INSTRUCTION, device=DEVICE
    )

    embeddings = extract_embeddings(
        BINARY_PATH,
        safe_net,
        converter,
        normalizer,
        DEVICE,
        dict_functions=dict_functions,
        dictionary_labeled=True,
        context_sensitivity_level=2,
        normalize=True,
        call_depth=2,
        keep_state=True
    )

    print(f"len(embeddings): {len(embeddings)}")

    save_embeddings(embeddings, OUTPUT_PATH)

if __name__ == '__main__':
    main()


    # bin_path = "/home/marcos/Projects/Continuous_Parserhunter/data/raw/binaries/yacc_calculator_tutorial/Executables/"
    # BINARY_PATH = bin_path + "calc"
    # pkl_path = "/home/marcos/Projects/Continuous_Parserhunter/data/processed/dicts_functions/dict_list_labeled_functions/"
    # PKL_PATH = pkl_path + "calc.pkl"  # your pickled dict




# # Function to clean individual instructions by removing unwanted characters.
# def clean_instruction(instruction: str) -> str:
#     """
#     Cleans an instruction by removing unwanted symbols except square brackets (used for memory access).
#     """
#     pattern = r'[{}<>!@#$%^&*_=|/~`",;:?]'  # Removed [] from the pattern to keep them
#     cleaned_instruction = re.sub(pattern, '', instruction).strip()
#     return cleaned_instruction

# # Function to replace hex values and integers with generic placeholders.
# def replace_hex_and_int(instruction: str) -> str:
#     """
#     Replaces hex addresses and integer values with generic placeholders.
#     """
#     # Replace hex values (including optional + or - signs)
#     instruction = re.sub(r'(?<!\w)[+-]?0x[a-fA-F0-9]+(?!\w)', 'ADDR', instruction)
    
#     # Replace integer values (including optional + or - signs)
#     instruction = re.sub(r'(?<!\w)[+-]?\d+(?!\w)', 'INT', instruction)
#     return instruction


#     def extract_assembly_code_from_node(angr_node):
#         '''
#         Extract the assembly code from an Angr CFG node and return a string of assembly code.
#         Parameters:
#             angr_node (angr.analyses.cfg.CFGNode): The CFG node.
#         Returns:
#             assembly_code (str): A string of assembly code.
#         '''
#         # If there is no block at all, bail out early
#         if angr_node.block is None:
#             return ""
#         try:
#             assembly_code = ""
#             for instr in angr_node.block.capstone.insns:
#                 # extract the mnemonic and operands
#                 mnemonic = instr.mnemonic           # e.g., "mov"
#                 op_str = instr.op_str               # e.g., "eax, 0x0"
#                 # concatenate the mnemonic and operands
#                 instruct = mnemonic + " " + op_str
#                 assembly_code += instruct + "\n"    # e.g., "mov eax, 0x0\n"
#         except KeyError:
#             # No bytes mapped for this block’s address — skip it
#             return ""
#         return assembly_code  # bb1, bb2, bb3, bb4, ...



#     # Function to clean and transform assembly code by processing each instruction.
#     def clean_and_transform_assembly(assembly_codes: str) -> str:
#         '''
#         Clean the assembly code and transform hex and integer values into placeholders.
#         '''
#         # Split the block into individual instructions
#         instructions = re.findall(r'[^;\n]+', assembly_codes)  # Split by lines or semicolons

#         # Clean and transform each instruction
#         cleaned_instructions = []
#         for instr in instructions:
#             cleaned_instr = clean_instruction(instr.strip())
#             transformed_instr = replace_hex_and_int(cleaned_instr)
#             cleaned_instructions.append(transformed_instr)
        
#         # Join the cleaned instructions back into a block, preserving newlines
#         cleaned_block = '\n'.join(cleaned_instructions)
#         return cleaned_block



#     def get_node_embedding(node, path_python_executable, path_script_asm2vec):
#         # Extract the assembly code from the angr node
#         assembly_code = extract_assembly_code_from_node(node) # assembly_code = [bb1, bb2, ...]
#         # Clean and transform the assembly codes
#         cleaned_assembly_codes = clean_and_transform_assembly(assembly_code) # list of cleaned basic blocks 
#         # Get the embedding for the assembly code using asm2vec
#         embedding = ams2vec_inference(cleaned_assembly_codes, path_python_executable, path_script_asm2vec)
#     return embedding


#        for node in cfg.graph.nodes():
#         # Address of the node
#         addr = hex(node.addr)
#         # Check if the address has been visited
#         if addr not in visited_addresses:
#             # Get the node embedding
#             features = get_node_embedding(node, path_python_executable, path_script_asm2vec)

