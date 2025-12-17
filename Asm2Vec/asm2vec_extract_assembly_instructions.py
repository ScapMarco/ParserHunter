import re
import angr
import os
import sys
from gensim.models.asm2vec import Asm2Vec, Function, Instruction
import pickle


# Use conda env asm2vec (python 3.8.19)

# Constants
CALLDEPTH = 2                  # Analyzes the current function and its direct calls up to two levels deep.
CONTEXT_SENSITIVITY_LEVEL = 2  # Considers different calling contexts for functions for precise behavior analysis.
NORMALIZE = True               # Simplifies the CFG structure by removing unnecessary nodes and edges.
KEEP_STATE = True              # Preserves all input states during analysis for debugging and exploration.


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

def cfg_to_list_of_assembly_functions(cfg):
    assembly_codes = []
    for node in cfg.graph.nodes():
        # Extract the assembly code from the node
        assembly_code = extract_assembly_code_from_node(node)
        assembly_codes.append(assembly_code)

    return assembly_codes # [bb1, bb2, ...]

def extract_assembly_code(binary_path, path_labeled_dictionary, label=False):

    # [function1, function2, ...] = [[bb1, bb2, ...], [bb1, bb2, ...], ...]
    fuctions_assembly_code = [] 

    # Create an Angr project for the binary executable
    project = angr.Project(thing=binary_path, load_options={"auto_load_libs": False})
    
    # get the labeled dictionary of functions to analyze  ( {'name': (address, label)} )
    functions_to_analyze = load_and_convert_pkl(path_labeled_dictionary, label=label)
    i = 1
    for name, value in functions_to_analyze.items():
        print(f"({i}) Extracting assembly from function: {name} -------------------------------------------")
        i+=1

        # Check for the Label
        if label == False:
            address = value
        else:
            address, y = value

        try:
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
        except Exception as e:
            print(f"Skipping this Function (for angr error): {e}")
            continue

        print(f"cfg.graph: {cfg.graph}")

        # Extract the assembly code of each basic block from the function CFG
        function_assembly_code = cfg_to_list_of_assembly_functions(cfg)
        print(f"    Total basic blocks (len(function_assembly_code)): {len(function_assembly_code)}")
        fuctions_assembly_code.append(function_assembly_code)


    # Flatten the list of lists into a single list
    #       from [function1, function2, ...] = [[bb1, bb2, ...], [bb1, bb2, ...], ...]
    #       to   [bb1, bb2, bb3, bb4, ...]
    flattened_fuctions_assembly_code = [item for sublist in fuctions_assembly_code for item in sublist]

    print(f"Extracted all functions from executable {binary_path} ------------------------------")
    print(f"    Total functions: {len(fuctions_assembly_code)}")
    print(f"    Total basic blocks: {len(flattened_fuctions_assembly_code)}")
    print()
    return flattened_fuctions_assembly_code # [bb1, bb2, bb3, bb4, ...]



def get_assembly_codes_list_from_bash_scripts(paths_bash_scripts, path_labeled_dictionaries):
    """
    Extracts assembly codes from executables specified in a list of bash script files.

    Args:
    - paths_bash_scripts (list): List of paths to bash script files.
    - path_labeled_dictionaries (str): Path to the folder containing labeled dictionaries.

    Returns:
    - assembly_codes_list (list): List of assembly codes extracted from the executables.
    """
    
    assembly_codes_list = []
    tot_executables = 0 

    # Iterate over each bash script file
    for bash_script_path in paths_bash_scripts:
        script_dir = os.path.dirname(os.path.abspath(bash_script_path))
        dictionary_dir = os.path.abspath(path_labeled_dictionaries)
        
        # Read the bash script file
        with open(bash_script_path, 'r') as file:
            for line in file:
                if line.startswith('gcc') or line.startswith('clang'):
                    tokens = line.split()
                    # Find the index of the '-o' option
                    output_index = tokens.index('-o') + 1 if '-o' in tokens else -1
                    if output_index != -1 and output_index < len(tokens):
                        # Extract the executable file name
                        executable_file = tokens[output_index]
                        # Create the full path to the executable
                        binary_path = os.path.join(script_dir, 'Executables', executable_file)
                        # Create the dictionary file name
                        dictionary_file = executable_file + '.pkl'
                        # Create the full path to the labeled dictionary
                        labeled_dictionary_path = os.path.join(dictionary_dir, dictionary_file)
                        # Get assembly codes list from executable
                        print(f"binary_path: {binary_path}")
                        
                        assembly_codes = extract_assembly_code(binary_path, labeled_dictionary_path, label=True)
                        assembly_codes_list.extend(assembly_codes)
                        tot_executables += 1
    print()
    print(f"Extracted all basic blocks from all executables -------------------------------------------")
    print(f"    Total executables analyzed: {tot_executables}")
    print(f"    Total basic blocks extracted: {len(assembly_codes_list)}")
    return assembly_codes_list



def get_assembly_codes_list_from_executables(paths_executables, path_labeled_dictionaries):
    """
    Extracts assembly codes from executables specified in a list of bash script files.
    """
    
    assembly_codes_list = []
    tot_executables = 0 

    for binary_path, dictionary_path  in zip(paths_executables, path_labeled_dictionaries):

        # Get assembly codes list from executable
        print(f"binary_path: {binary_path}")
        print(f"dictionary_path: {dictionary_path}")
        
        assembly_codes = extract_assembly_code(binary_path, dictionary_path, label=False)
        assembly_codes_list.extend(assembly_codes)
        tot_executables += 1

    print()
    print(f"Extracted all basic blocks from all executables -------------------------------------------")
    print(f"    Total executables analyzed: {tot_executables}")
    print(f"    Total basic blocks extracted: {len(assembly_codes_list)}")
    return assembly_codes_list




def save_list(list_assembly, file_path):
    # Open the file in write mode and write each string from the list to the file
    with open(file_path, "w") as file:
        for string in list_assembly:
            file.write(string + "\n")
    print(f"List of Basic blocks saved in {file_path}\n")


def read_list(file_path):
    print(f"Reading list from file: {file_path} -----------------------------------------------")
    # Initialize an empty list to store the assembly code instructions
    assembly_codes = []

    # Open the file in read mode and read all lines into the list
    with open(file_path, "r") as file:
        current_basic_block = ""  # Initialize a string to store the instructions of the current basic block
        for line in file:
            line = line.strip()  # Remove leading and trailing whitespace
            if line:  # If the line is not empty
                if len(line.split()) == 1:  # If the line contains a single instruction
                    line += " "  # Add a space after the instruction
                current_basic_block += line + "\n"  # Add the line to the current basic block with a newline character
            else:  # If an empty line is encountered, it signifies the end of the current basic block
                assembly_codes.append(current_basic_block.rstrip("\n"))  # Append the current basic block to the list of assembly codes
                current_basic_block = ""  # Reset the string for the next basic block

    # If there's any remaining basic block after reading all lines, append its instructions to the assembly codes list
    if current_basic_block:
        assembly_codes.append(current_basic_block.rstrip("\n"))
    
    print(f"End Reading list! Readed {len(assembly_codes)} basic blocks -----------------------------------------------")
    return assembly_codes

def main(paths_bash_scripts, path_labeled_dictionaries, paths_executables, path_dictionaries):

    # get the assembly codes list from the bash scripts
    assembly_codes_from_bash = get_assembly_codes_list_from_bash_scripts(paths_bash_scripts, path_labeled_dictionaries) 
    # Total executables analyzed: 

    # get the assembly codes list from the executables
    assembly_codes_from_executables = get_assembly_codes_list_from_executables(paths_executables, path_dictionaries) 
    # Total executables analyzed: 14 with a total of 10767 basic blocks

    # assembly_codes is a list where each element is a string of assembly code representing a basic block
    # assembly_codes = [bb1, bb2, bb3, bb4, ...]
    assembly_codes = assembly_codes_from_bash + assembly_codes_from_executables
    print()
    print(f"Final len(assembly_codes): {len(assembly_codes)}") # len(assembly_codes): 696448
    print(f"assembly_codes[0]: \n{assembly_codes[0]}") # [bb1, bb2, bb3, bb4, ...]
    print() 

    # Save the list of assembly codes to a text file
    save_list(list_assembly=assembly_codes, file_path = "./Asm2Vec/assembly_codes.txt")

    # Read the list of assembly codes from a text file
    assembly_codes = read_list(file_path="./Asm2Vec/assembly_codes.txt")
    print(f"len(assembly_codes): {len(assembly_codes)}") # len(assembly_codes): 696448
    print(f"assembly_codes[0]: \n{assembly_codes[0]}") # [bb1, bb2, bb3, bb4, ...]  =  [..., INT\npop ebx\nret \n', 'call eax\n']
    print()



if __name__ == "__main__":
    # list of paths to bash script files (to retrieve the names of the executables to analyze)
    paths_bash_scripts = [ 
        "./Binaries/Packcc/compile_script.sh",
        "./Binaries/elf-parser/compile_script.sh",
        "./Binaries/Yacc_Calculator_tutorial/compile_script.sh",
        "./Binaries/CParserXML/compile_script.sh",  
        "./Binaries/picohttpparser/compile_script.sh",  
        "./Binaries/CSimpleJSONParser/compile_script.sh",
        "./Binaries/cJSON/compile_script.sh",
        "./Binaries/Benoitc_HTTP_Parser/compile_script.sh",
        "./Binaries/network-packet-analyzer/compile_script.sh",
        "./Binaries/pcap_parser/compile_script.sh",
    ]
    # Path to the folder containing all list of labeled functions to analyze
    path_labeled_dictionaries = "./Dictionaries_Labeled_Datas"

    # list of paths to executables
    paths_executables = [
        "./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/bin/echo",
        "./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/bin/grep",
        "./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/bin/fgrep",
        "./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/bin/egrep",
        "./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/bin/netstat",
        "./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/bin/ping",
        "./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/bin/ping6",
        "./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/bin/zcat",
        "./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/sbin/ifconfig",
        "./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/sbin/vconfig",
        "./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/usr/bin/awk",
        "./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/usr/bin/curl",
        "./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/usr/bin/hexdump",
        "./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/usr/bin/mii_mgr",
    ]

    # Single Paths to the list of functions to analyze
    path_dictionaries = [
        "./Asm2Vec/Dictionaries_list_of_functions/echo.pkl",
        "./Asm2Vec/Dictionaries_list_of_functions/grep.pkl",
        "./Asm2Vec/Dictionaries_list_of_functions/fgrep.pkl", 
        "./Asm2Vec/Dictionaries_list_of_functions/egrep.pkl", 
        "./Asm2Vec/Dictionaries_list_of_functions/netstat.pkl", 
        "./Asm2Vec/Dictionaries_list_of_functions/ping.pkl", 
        "./Asm2Vec/Dictionaries_list_of_functions/ping6.pkl", 
        "./Asm2Vec/Dictionaries_list_of_functions/zcat.pkl", 
        "./Asm2Vec/Dictionaries_list_of_functions/ifconfig.pkl", 
        "./Asm2Vec/Dictionaries_list_of_functions/vconfig.pkl", 
        "./Asm2Vec/Dictionaries_list_of_functions/awk.pkl", 
        "./Asm2Vec/Dictionaries_list_of_functions/curl.pkl", 
        "./Asm2Vec/Dictionaries_list_of_functions/hexdump.pkl", 
        "./Asm2Vec/Dictionaries_list_of_functions/mii_mgr.pkl", 
    ]

    main(paths_bash_scripts, path_labeled_dictionaries, paths_executables, path_dictionaries)