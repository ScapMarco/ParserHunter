import pickle
import angr
import r2pipe
from multiprocessing import Process, Queue

# Use the conda environment test-3.9-env

# Constants
CALLDEPTH = 2                  # Analyzes the current function and its direct calls up to two levels deep.
CONTEXT_SENSITIVITY_LEVEL = 2  # Considers different calling contexts for functions for precise behavior analysis.
NORMALIZE = True               # Simplifies the CFG structure by removing unnecessary nodes and edges.
KEEP_STATE = True              # Preserves all input states during analysis for debugging and exploration.
MIN_NODES_EDGES = 1            # Minimum number of nodes and edges to consider 
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

def save_labeled_data(labeled_dict, filename):
    with open(filename, 'wb') as file:
        pickle.dump(labeled_dict, file)
    print(f"    Labeled data saved to {filename}")

def load_and_convert_pkl(file_path):
    try:
        with open(file_path, 'rb') as file:
            data = pickle.load(file)

            # Check if the loaded data is a dictionary
            if not isinstance(data, dict):
                raise ValueError("The loaded data is not a dictionary.")
            
            return data            
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"Error: {e}")

def main(bin_name, binary_path, file_path):
    # Get the list of functions
    load_opts = {"auto_load_libs": False}
    functions_to_analyze = identify_functions_with_r2(
        project_path=binary_path,
        load_options=load_opts
    )
    # save the functions_to_analyze dictionary data
    save_labeled_data(functions_to_analyze, filename=file_path) 

    # READ THE DATA
    dictionary = load_and_convert_pkl(file_path)
    if dictionary is not None:
        print("Dictionary successfully loaded:")
    print()
    print(f"Total functions to analyze: {len(dictionary)}")

if __name__ == "__main__":
    # binary name
    bin_name = f"csv_test"
    # binary path
    binary_path = f"./Binaries/libcsv/{bin_name}"
    # file path
    file_path = f"./Case_Studies/Dictionaries_list_of_functions/{bin_name}.pkl"
    main(bin_name, binary_path, file_path)

# Executables for training Asm2Vec
# ./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/bin/echo
# ./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/bin/grep
# ./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/bin/fgrep
# ./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/bin/egrep
# ./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/bin/netstat
# ./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/bin/ping
# ./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/bin/ping6
# ./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/bin/zcat
# ./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/sbin/ifconfig
# ./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/sbin/vconfig
# ./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/usr/bin/awk
# ./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/usr/bin/curl
# ./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/usr/bin/hexdump
# ./Binaries/Test_Extraction_Firmware/_miwifi_r1cm_firmware_36bfd_2.22.21.bin.extracted/squashfs-root/usr/bin/mii_mgr