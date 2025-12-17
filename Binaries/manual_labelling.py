import os
import pickle
import angr
import r2pipe
from multiprocessing import Process, Queue

# Use conda env 3.9.15

# Constants
CALLDEPTH = 2                  # Analyzes the current function and its direct calls up to two levels deep.
CONTEXT_SENSITIVITY_LEVEL = 2  # Considers different calling contexts for functions for precise behavior analysis.
NORMALIZE = True               # Simplifies the CFG structure by removing unnecessary nodes and edges.
KEEP_STATE = True              # Preserves all input states during analysis for debugging and exploration.
MIN_NODES_EDGES = 3            # Minimum number of nodes and edges to consider 
TIMEOUT_DURATION = 60          # Timeout duration in seconds


def _cfg_worker(address, project_kwargs, out_q):
    try:
        proj = angr.Project(**project_kwargs)
        cfg = proj.analyses.CFGEmulated(
            starts=[address],
            initial_state=proj.factory.blank_state(addr=address),
            context_sensitivity_level=CONTEXT_SENSITIVITY_LEVEL,
            normalize=NORMALIZE,
            call_depth=CALLDEPTH,
            state_add_options=angr.options.refs,
            keep_state=KEEP_STATE,
            max_steps=100000
        )
        nodes = len(cfg.graph.nodes())
        edges = len(cfg.graph.edges())
        out_q.put((True, (nodes, edges)))
    except Exception as e:
        out_q.put((False, str(e)))

def filter_graphs(address, project_path, load_options):
    out_q = Queue()
    # Pass only what the worker needs: path and load_options
    p = Process(
        target=_cfg_worker,
        args=(address, {"thing": project_path, "load_options": load_options}, out_q)
    )
    p.start()
    p.join(TIMEOUT_DURATION)
    if p.is_alive():
        p.terminate()
        p.join()
        print(f"    CFG build process timed out at {hex(address)}")
        return False

    success, payload = out_q.get()
    if not success:
        print(f"    CFG error at {hex(address)}: {payload}")
        return False

    nodes, edges = payload
    if nodes <= MIN_NODES_EDGES or edges <= MIN_NODES_EDGES:
        return False

    print(f"    CFG OK for {hex(address)} (nodes={nodes}, edges={edges})")
    return True

def identify_functions_with_r2(project_path, load_options):
    """Identify functions in the binary using fast Radare2 and skip slow CFG builds."""
    print("Analyzing binary with RADARE2…")
    r2 = r2pipe.open(project_path)
    r2.cmd('e bin.libs=false')
    r2.cmd('e bin.cache=true')              # or r2.cmd('e bin.relocs.apply=true')
    r2.cmd('aa')                            # full auto-analysis (xrefs, vars, calls, etc.)
    r2.cmd('s .text')
    functions = r2.cmdj('aflj')

    results = {}
    for i, func in enumerate(functions):
        name = func['name']
        addr = func['offset']
        # skip libs/imports
        if func.get('is_lib') or name.startswith('sym.imp.'):
            continue

        # call filter_graphs
        if filter_graphs(
            address=addr,
            project_path=project_path,
            load_options=load_options
        ):
            print(f"{len(results)}: {name} @ {hex(addr)}")
            results[name] = addr

    return results

def label_data(input_dict):
    total = len(input_dict)
    labeled_dict = {} 
    for i, (name, memory_address) in enumerate(input_dict.items()):
        memory_address = hex(memory_address)
        label = input(f"{memory_address} -- {name} -- {i}/{total} -- Enter label (1 or 0 or ?): ")
        while label not in ['0', '1', '?']:
            print("Invalid input. Please enter either 1, 0 or ?.")
            label = input(f"{memory_address} -- {name} -- {i}/{total} -- Enter label (1 or 0 or ?): ")
        labeled_dict[name] = (memory_address, label)
    return labeled_dict

def save_labeled_data(labeled_dict, filename):
    with open(filename, 'wb') as file:
        pickle.dump(labeled_dict, file)
    print(f"    Labeled data saved to {filename}")

def apply_labels_to_other_executables(selected_executable, labeled_data, input_path, output_path):
    # Get all executables in the input path
    executables = [f for f in os.listdir(input_path) if os.path.isfile(os.path.join(input_path, f))]

    for exe in executables:
        if exe == os.path.basename(selected_executable):
            continue  # Skip the selected executable

        binary_path = os.path.join(input_path, exe)

        # Identify functions for the current executable
        load_opts = {"auto_load_libs": False}
        functions_to_analyze = identify_functions_with_r2(
            project_path=binary_path,
            load_options=load_opts
        )

        # Create a new labeled dictionary for the current executable
        new_labeled_dict = {}
        for name, address in functions_to_analyze.items():
            if name in labeled_data:
                new_labeled_dict[name] = (hex(address), labeled_data[name][1]) # Use the same label

        # Save the new labeled data to a separate file
        output_filename = os.path.join(output_path, f"{os.path.basename(binary_path)}.pkl")
        save_labeled_data(new_labeled_dict, filename=output_filename)


def main(input_path, output_path):
    # Get the list of executables in the specified path
    executables = [f for f in os.listdir(input_path) if os.path.isfile(os.path.join(input_path, f))]

    if not executables:
        print("No executables found in the specified folder.")
        return

    print("Available executables:")
    for i, exe in enumerate(executables):
        print(f"{i}: {exe}")

    # Ask the user to select an executable
    selected_index = int(input("Select an executable by entering its index: "))
    selected_executable = os.path.join(input_path, executables[selected_index])

    # Get the list of functions
    load_opts = {"auto_load_libs": False}
    functions_to_analyze = identify_functions_with_r2(
        project_path=selected_executable,
        load_options=load_opts
    )


    # Add labels to the functions
    functions_to_analyze = label_data(input_dict=functions_to_analyze) # dict {name: (address, label)}

    # Save the functions_to_analyze dictionary data
    output_filename = os.path.join(output_path, f"{os.path.basename(selected_executable)}.pkl")
    save_labeled_data(functions_to_analyze, filename=output_filename)

    # Apply the same labels to all other executables
    apply_labels_to_other_executables(selected_executable, functions_to_analyze, input_path, output_path)

if __name__ == "__main__":
    # Specify the path to the folder containing executables
    input_path = "./Binaries/Packcc/Executables/"
    output_path = "./Dictionaries_Labeled_Datas/"
    main(input_path, output_path)



# Paths to Binaries (10 bin)
# ./Binaries/CParserXML/Executables/                OK  21
# ./Binaries/picohttpparser/Executables             OK  32
# ./Binaries/CSimpleJSONParser/Executables          OK  38
# ./Binaries/cJSON/Executables                      OK  99
# ./Binaries/Benoitc_HTTP_Parser/Executables        OK  16
# ./Binaries/Yacc_Calculator_tutorial/Executables   OK  28
# ./Binaries/network-packet-analyzer/Executables    OK  14
# ./Binaries/elf-parser/Executables                 OK  26  
# ./Binaries/pcap_parser/Executables                OK  14
# ./Binaries/Packcc/Executables                     OK  105
