import angr
import torch
import os
import pickle
import random
import numpy as np

# Utility functions
import from_CFG_to_DataGeometric 

# use conda env test-3.10.0-env


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


def create_and_save_geometric_datas_list(path_binary, path_dictionary, path_python_executable, path_script_asm2vec, path_output_file):

    # set seed for reproducibility
    torch.manual_seed(42)
    random.seed(42)
    np.random.seed(42)

    # Create an Angr project for the binary executable
    project = angr.Project(thing=path_binary, load_options={"auto_load_libs": False})
    #
    # get the dictionary of functions to analyze  {'name': address}
    functions_to_analyze = load_and_convert_pkl(path_dictionary, label=True)
    #
    # Create a list of DataGeometric objects from a Angr project and a dictionary of functions
    geometric_datas_list = from_CFG_to_DataGeometric.get_Geometric_Datas(project=project, 
                                                                        functions_addresses=functions_to_analyze, 
                                                                        path_python_executable=path_python_executable,
                                                                        path_script_asm2vec=path_script_asm2vec,
                                                                        dictionary_labeled=True) 
    #
    try:
        # Save the list using torch.save
        torch.save(geometric_datas_list, path_output_file)
        print(f"\nGeometric datas list saved to {path_output_file}\n")
    except Exception as e:
        print(f"\nError saving geometric datas list: {e}\n")


def automatize_create_and_save_geometric_datas_list(path_bash_script, path_labeled_dictionaries, path_out_files, path_python_executable, path_script_asm2vec):
    '''
    Automatize the process of creating and saving geometric datas list for each executable in a bash script file.
    The function reads the bash script file, extracts the executable file names, 
    creates the full path to the executables (binary_path), the full path to the labeled dictionaries (labeled_dictionary_path) 
    and the full path to the output files.
    Then, it calls the function to create and save the geometric datas list for each executable.

    Parameters:
    path_bash_script (str): The path to the bash script file.
    path_labeled_dictionaries (str): The path to the directory containing the labeled dictionaries.
    path_out_files (str): The path to the directory where to save the output files.
    create3 (bool): If True, use the function to create and save geometric datas list3. If False, use the function to create and save geometric datas list.
    '''

    script_dir = os.path.dirname(os.path.abspath(path_bash_script))
    dictionary_dir = os.path.abspath(path_labeled_dictionaries)
    out_files_dir = os.path.abspath(path_out_files)
    executable_count = 0
    
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
                    # Create the full path to the output file
                    path_output_file = os.path.join(out_files_dir, executable_file + '.pt')

                    print()
                    print(f"AUTOMATIZE CREATE AND SAVE GEOMETRIC DATAS LIST --------------------------------")
                    print(f"{executable_count}) executable file name: {executable_file}")
                    print(f"    {executable_count}) executable path: {path_binary}")
                    print(f"    {executable_count}) labeled dictionary path: {path_dictionary}")
                    print(f"    {executable_count}) output file path: {path_output_file}")
                    print()

                    # Call the function to create and save geometric data
                    create_and_save_geometric_datas_list(path_binary=path_binary, 
                                                        path_dictionary=path_dictionary, 
                                                        path_python_executable=path_python_executable,
                                                        path_script_asm2vec=path_script_asm2vec,
                                                        path_output_file=path_output_file)


    print()
    print(f"END AUTOMATIZE CREATE AND SAVE GEOMETRIC DATAS LIST --------------------------------")
    print(f"    Total executables: {executable_count}")


    
########################################################################################################################################################################################################################

def main(path_bash_scripts):
    for path_bash_script in path_bash_scripts:
        automatize_create_and_save_geometric_datas_list(
            path_bash_script=path_bash_script, 
            path_labeled_dictionaries="./Dictionaries_Labeled_Datas",
            path_out_files="./Saved_Geometric_Datas",
            path_python_executable = "/home/fabio.pinelli/anaconda3/envs/asm2vec/bin/python", # change to your python executable
            # /home/marcos/anaconda3/envs/asm2vec/bin/python
            # /home/fabio.pinelli/anaconda3/envs/asm2vec/bin/python
            path_script_asm2vec = "./Asm2Vec/asm2vec_inference.py"
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