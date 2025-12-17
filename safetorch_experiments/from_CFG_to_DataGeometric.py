import torch
from torch_geometric.data import Data
import networkx as nx
import os
import subprocess
import ast
import matplotlib.pyplot as plt
import angr 


# Constants
CALLDEPTH = 2                  # Analyzes the current function and its direct calls up to two levels deep.
CONTEXT_SENSITIVITY_LEVEL = 2  # Considers different calling contexts for functions for precise behavior analysis.
NORMALIZE = True               # Simplifies the CFG structure by removing unnecessary nodes and edges.
KEEP_STATE = True              # Preserves all input states during analysis for debugging and exploration.

# Small cache so the model is loaded only once for all nodes.
_safetorch_cache = {
    "net": None,
    "conv": None,
    "norm": None,
    "device": None,
    "dim": None
}

def safetorch_inference(assembly_code, path_python_executable=None, path_script_embedding_model=None):
    """
    Use the local SAFE model to get an embedding for the provided assembly code string.
    - assembly_code: string with one instruction per line (as produced by extract_assembly_code_from_node).
    - path_python_executable, path_script_embedding_model: kept for compatibility with your existing calls,
      but are NOT used (we load the local safetorch model).
    Returns:
      - embedding as a list of floats (length = SAFE embedding dim).
      - never returns None; for empty input returns a zero-vector of appropriate length.
    """
    import torch
    # lazy import/init of model + converters
    global _safetorch_cache

    # Default model/vocab paths used by your original pipeline
    model_path = "./safetorch/model/SAFEtorch.pt"
    vocab_path = "./safetorch/model/word2id.json"
    max_instruction = 150
    device = "cpu"

    # Initialize model & helpers once
    if _safetorch_cache["net"] is None:
        try:
            from safetorch.safetorch.safe_network import SAFE
            from safetorch.safetorch.parameters import Config
            from safetorch.utils.function_normalizer import FunctionNormalizer
            from safetorch.utils.instructions_converter import InstructionsConverter
            
        except Exception as e:
            # give a helpful error if imports fail
            raise RuntimeError(f"Failed to import SAFE or utilities: {e}")

        cfg = Config()
        net = SAFE(cfg).to(device)
        sd = torch.load(model_path, map_location=device)
        net.load_state_dict(sd)
        net.eval()
        conv = InstructionsConverter(vocab_path)
        norm = FunctionNormalizer(max_instruction=max_instruction)

        _safetorch_cache.update({
            "net": net,
            "conv": conv,
            "norm": norm,
            "device": device,
            "dim": None
        })

    net = _safetorch_cache["net"]
    conv = _safetorch_cache["conv"]
    norm = _safetorch_cache["norm"]

    # Convert assembly string into a list of instruction strings
    # e.g. "mov eax, ebx\nadd eax, 1\nret\n" -> ["mov eax, ebx", "add eax, 1", "ret"]
    instrs = [line.strip() for line in assembly_code.splitlines() if line.strip()]

    # If we have no instructions, return a zero-vector of the known embedding dimension.
    # If the dim is unknown (first call happened with empty instrs), we compute dim by embedding a single "nop".
    if not instrs:
        if _safetorch_cache["dim"] is None:
            # compute a small embedding to determine size
            dummy = ["nop"]
            ids = conv.convert_to_ids(dummy)
            padded, lengths = norm.normalize_functions([ids])
            seq = padded[0]
            length0 = int(lengths[0])
            tensor = torch.LongTensor(seq).to(device)
            with torch.no_grad():
                emb = net(tensor, [length0]).squeeze(0).cpu()
            dim = int(emb.shape[0])
            _safetorch_cache["dim"] = dim
        else:
            dim = _safetorch_cache["dim"]
        return [0.0] * dim

    # Convert instructions -> ids -> normalized padded sequence
    ids = conv.convert_to_ids(instrs)
    padded, lengths = norm.normalize_functions([ids])
    seq = padded[0]
    length0 = int(lengths[0])

    # Run SAFE encoder
    tensor = torch.LongTensor(seq).to(device)
    with torch.no_grad():
        emb = net(tensor, [length0]).squeeze(0).cpu()

    # cache embedding dimensionality
    if _safetorch_cache["dim"] is None:
        _safetorch_cache["dim"] = int(emb.shape[0])

    # return plain Python list of floats (safe to store as node attribute later)
    return emb.numpy().tolist()

def ams2vec_inference(assembly_code, path_python_executable, path_script_asm2vec):
    
    # Call the script with the assembly code as an argument
    result = subprocess.run(
        [path_python_executable, path_script_asm2vec, assembly_code],
        capture_output=True,
        text=True
    )
    
    # Check if there is any error output
    if result.stderr:
        print("Error:", result.stderr)
        return None
    
    # Extract the output as a string
    output = result.stdout.strip()
    
    try:
        # Attempt to parse the output as a list of floats using ast.literal_eval
        embedding = ast.literal_eval(output)
        return embedding
    except (SyntaxError, ValueError) as e:
        print(f"Error: Failed to parse embedding output.\n{type(e).__name__}: {e}")
        return None

def extract_assembly_code_from_node(angr_node):
    '''
    Extract the assembly code from an Angr CFG node and return a string of assembly code.
    Parameters:
        angr_node (angr.analyses.cfg.CFGNode): The CFG node.
    Returns:
        assembly_code (str): A string of assembly code.
    '''
    # If there is no block at all, bail out early
    if angr_node.block is None:
        return ""
    try:
        assembly_code = ""
        for instr in angr_node.block.capstone.insns:
            mnemonic = instr.mnemonic
            op_str = instr.op_str
            instruct = mnemonic + " " + op_str
            assembly_code += instruct + "\n"
    except KeyError:
        # No bytes mapped for this block’s address — skip it
        return ""
    return assembly_code  # bb1, bb2, bb3, bb4, ...


def get_node_embedding(node, path_python_executable, path_script_embedding_model):
    # Extract the assembly code from the angr node
    assembly_code = extract_assembly_code_from_node(node) # assembly_code = [bb1, bb2, ...]
    # Get the embedding for the assembly code using the embedding model
    embedding = safetorch_inference(assembly_code, path_python_executable, path_script_embedding_model)
    return embedding


def get_ACFG(cfg, project, path_python_executable, path_script_embedding_model):
    """Function to extract an ACFG from a CFG of a function
    Args:
        :param cfg:                         CFG of a function
        :param project:                     Angr project
        :param path_python_executable:      Path to the Python executable for Asm2Vec
        :param path_script_embedding_model: Path to the embedding script for model inference
    Output:
        :return:            ACFG of the function
    """
    
    # Create an empty ACFG
    acfg = nx.DiGraph()

    # Add non-duplicated nodes
    visited_addresses = set()
    for node in cfg.graph.nodes():
        # Address of the node
        addr = hex(node.addr)
        # Check if the address has been visited
        if addr not in visited_addresses:
            # Get the node embedding
            features = get_node_embedding(node, path_python_executable, path_script_embedding_model)
            # Add the address to the set of visited addresses
            visited_addresses.add(addr)
            # Add the new node in the ACFG with additional features
            acfg.add_node(
                # node address
                node_for_adding=addr,
                # node features
                embedding=features,
            )

    # Add edges between existing nodes
    for src, dst, data in cfg.graph.edges(data=True):
        # Retrieve the nodes addresses 
        src_addr = hex(src.addr)
        dst_addr = hex(dst.addr)

        # Ensure both source address and destination address exist in the new graph
        if (src_addr in visited_addresses) and (dst_addr in visited_addresses):
            # Add the edge in the ACFG with additional features
            acfg.add_edge(
                # edge source and destination 
                u_of_edge=src_addr, 
                v_of_edge=dst_addr, 
            )
     
    print(f"Final acfg (in get_ACFG): {acfg}")
    return acfg


def get_Geometric_Data_from_CFG(cfg, project, label=None, path_python_executable=None, path_script_embedding_model=None, ref=None):
    """Function to extract a PyTorch Geometric Data object from a CFG of a function
    Args:
        :param cfg:                                        CFG of a function
        :param project:                                    Angr project
        :param label (optional):                           Label for the function
        :param path_python_executable (optional):          Path to the Python executable
        :param path_script_embedding_model (optional):     Path to the embedding model script
        :param ref (optional):                             Reference information for the function
    Output:
        :return:                                           PyTorch Geometric Data object
    """

    # Get the ACFG from the CFG
    acfg = get_ACFG(cfg=cfg, project=project, 
                    path_python_executable=path_python_executable, 
                    path_script_embedding_model=path_script_embedding_model
                    )
    # Extract node features
    node_features = []  
    # Iterate through nodes to get features
    for node_id, attributes in acfg.nodes(data=True):
        # iterate through the attributes and add each key and value to the list
        values = []
        for key, value in attributes.items():
            # acfg node features
            values.append(value)

        node_features.append(values) 

    # Create a mapping from addresses to integers
    address_to_index = {address: idx for idx, address in enumerate(acfg.nodes)}
    # Edge indices
    edge_indices = [] 
    # Iterate through edges to get index and features
    for src, dst, edge in acfg.edges(data=True):
        # Extract edge feature 
        source_index = address_to_index[src]
        destination_index = address_to_index[dst]
        # Append the source and target node indices to the edge indices
        edge_indices.append([source_index, destination_index])

    # Convert to PyTorch tensors
    print(f"\nConvert to PyTorch tensors:")
    # Flatten the nested list structure and filter out any None values
    flat_node_features = [emb for sublist in node_features for emb in sublist]
    # Convert the list to a PyTorch tensor
    x = torch.tensor(flat_node_features, dtype=torch.float32)
    print(f"x.shape: {x.shape}")
    edge_index = torch.tensor(edge_indices, dtype=torch.long).t().contiguous()
    print(f"edge_index.shape: {edge_index.shape}")

    if label is not None:
        labels = [label] 
        y = torch.tensor(labels, dtype=torch.long)
        # Create a PyTorch Geometric Data object
        data = Data(x=x, edge_index=edge_index, y=y, ref=ref)
    else:
        # Create a PyTorch Geometric Data object
        data = Data(x=x, edge_index=edge_index, ref=ref)

    # Check if the data object is valid
    data.validate(raise_on_error=True)
    print(f"Data object: {data}")
    return data



def get_Geometric_Datas(project, functions_addresses, path_python_executable, path_script_embedding_model, dictionary_labeled=True):
    """Function to extract a list of PyTorch Geometric Data objects from a list of functions
    Args:
        :param project:                 Angr project
        :param functions_addresses:     A dictionary of the form {name:(addres, label)} of the functions
    Output:
        :return:                        List of PyTorch Geometric Data objects with the CFG information and extracted features
    """    
    tot_count0 = 0
    tot_count1 = 0
    # list of ACFGs extracted from the binary
    geometric_datas_list = []
    i = 0
    # Loop through each function in the project 
    for name, value in functions_addresses.items(): # functions_addresses = {name:(address, label)}
        # Check for the label 
        if dictionary_labeled:
            address, label = value
        else:
            address = value

        print(f"\n-------------------------ITERATION: {i} --- Name: {name} --- Address: {hex(address)} ------------------------------------------") 
        i+=1
        # Find the starting state for the CFG
        start_state = project.factory.blank_state(addr=address, state_add_options=angr.options.ZERO_FILL_UNCONSTRAINED_REGISTERS) # project.factory.blank_state(addr=address)

        # Get the CFG for the specified function
        cfg = project.analyses.CFGEmulated(
            starts=[address], 
            initial_state=start_state, 
            context_sensitivity_level=CONTEXT_SENSITIVITY_LEVEL, 
            normalize=NORMALIZE, 
            call_depth=CALLDEPTH, 
            state_add_options=angr.options.refs, 
            keep_state=KEEP_STATE
        )  
                
        # Check for the label
        if dictionary_labeled:
            data_geom = get_Geometric_Data_from_CFG(cfg=cfg, project=project, label=label, 
                                                    path_python_executable=path_python_executable, 
                                                    path_script_embedding_model=path_script_embedding_model,
                                                    ref={'name': name, 'address': hex(address)})
            
            # Count the number of geometric datas with label 0 and 1
            if label == 0:
                tot_count0 += 1
            elif label == 1:
                tot_count1 += 1

        else:
            data_geom = get_Geometric_Data_from_CFG(cfg=cfg, project=project, label=None,
                                                    path_python_executable=path_python_executable, 
                                                    path_script_embedding_model=path_script_embedding_model,
                                                    ref={'name': name, 'address': hex(address)})
    
        # Append the Geometric Data to the list
        geometric_datas_list.append(data_geom)
        
    print(f"\n\n--------------------------------------------------------------------------------------------------")
    print(f"Total number of geometric datas (cfg with more than 0 nodes / edges): {len(geometric_datas_list)}")
    print(f"with label 0: {tot_count0}")
    print(f"with label 1: {tot_count1}")
    return geometric_datas_list