import os
import json
import torch
import random
import numpy as np
import pandas as pd
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import make_scorer, recall_score, f1_score
from torch.utils.data import ConcatDataset

# Models 
import GNNs_Models.GNNs_Models_Classifiers as GNNs_Models_Classifiers

# use conda env test-3.10.0-env

def load_dataset_from_folder(folder_path):
    datas_list = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            geometric_datas = torch.load(file_path)  # list of Data objects
            # Tag each graph with its source file
            for data in geometric_datas:
                data.filename = filename  # or file_path if you want full path
            datas_list.extend(geometric_datas)
    return datas_list


# New Version with all data 1 node features (shape [num_nodes, 1])
def load_dataset_from_folder_2(folder_path, set_node_feat_one: bool = False):
    """
    Load torch-geometric Data objects saved as files in folder_path.
    If set_node_feat_one is True, set every data.x to ones with shape [num_nodes, 1],
    regardless of original feature dimension.
    Returns a list of Data objects (each Data will have .filename set).
    """
    datas_list = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if not os.path.isfile(file_path):
            continue

        geometric_datas = torch.load(file_path)  # could be a Data or list[Data]

        # Normalize to iterable of Data objects
        if isinstance(geometric_datas, (list, tuple)):
            iterable = geometric_datas
        else:
            iterable = [geometric_datas]

        for data in iterable:
            # tag source filename
            data.filename = filename

            if set_node_feat_one:
                if not hasattr(data, "x") or data.x is None:
                    raise ValueError(f"Expected data.x to exist for file '{filename}', but it does not.")

                # Get number of nodes
                num_nodes = data.x.size(0)

                # Replace with [num_nodes, 1] ones tensor (float)
                data.x = torch.ones((num_nodes, 1), dtype=torch.float, device=data.x.device)

        datas_list.extend(iterable)

    return datas_list


def save_grid_search_results(grid_search, path_train_data, path):
    # convert grid_search.cv_results_ to a pandas DataFrame
    data_results = pd.DataFrame(grid_search.cv_results_) 
    # Extract dataset names from path_train_data
    dataset_names = [path.split('/')[-1] for path in path_train_data]
    # Rename the columns "split_i" to their corresponding dataset names
    for i in range(len(dataset_names)):
        new_name = f'{dataset_names[i]}_test_score'
        data_results = data_results.rename(columns={f'split{i}_test_score': new_name})

    # string name of the saved file
    filename = f"{path}result_gridsearch.csv"
    print(f"Saving the grid search results to {filename}")
    # Save the grid search pandas DataFrame to a CSV file
    data_results.to_csv(filename, index=False)

def save_model(best_model, best_params, path):
    # Save the best model for future usage
    model_save_path = f"{path}best_model.pth"  # Define the path to save the model
    torch.save(best_model.state_dict(), model_save_path)  # Save the model's state_dict
    print(f"Best model saved to {model_save_path}")
    # Save the json file with the best parameters
    json_save_path = f"{path}best_params.json"  # Define the path to save the json file
    with open(json_save_path, 'w') as f:
        json.dump(best_params, f)
    print(f"Best parameters saved to {json_save_path}")

def set_case_studies_node_features_to_one(case_studies):
    """
    Replace every Data.x in `case_studies` with a column of ones shaped [num_nodes, 1].
    - case_studies: list of torch_geometric.data.Data (or a single Data).
    - estimator_or_model: either your fitted estimator (has .model) or the torch.nn.Module itself.
    - dtype/device: optional overrides for the created tensors.
    The function operates in-place and returns None.
    """
    # Normalize to list
    if not isinstance(case_studies, (list, tuple)):
        case_studies = [case_studies]

    for d in case_studies:
        # infer number of nodes robustly
        n_nodes = getattr(d, "num_nodes", None)
        if n_nodes is None:
            if hasattr(d, "x") and d.x is not None:
                n_nodes = int(d.x.size(0))
            elif hasattr(d, "edge_index") and d.edge_index is not None:
                try:
                    n_nodes = int(d.edge_index.max().item()) + 1
                except Exception:
                    n_nodes = None

        # Replace x with ones of shape [n_nodes, 1]
        d.x = torch.ones((n_nodes, 1), dtype=torch.float, device=d.x.device)


def GNN_training_and_test(path_train_data, path_case_studies, path_to_save_results):
    # reproducibility & thread settings
    torch.manual_seed(42)
    random.seed(42)
    np.random.seed(42)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

    # Load all datasets and keep track of their lengths
    datasets = [load_dataset_from_folder(folder) for folder in path_train_data]
    #datasets = [load_dataset_from_folder_2(folder, set_node_feat_one=True) for folder in path_train_data]
    for i in range(len(datasets)):
        print(f"    Functions in the {i} binary len(datasets[{i}]) ({path_train_data[i]}): {len(datasets[i])}")

    # count labels robustly
    total_ones = 0
    total_zeros = 0
    for dataset in datasets:
        for data in dataset:
            y = data.y
            if isinstance(y, torch.Tensor):
                y_flat = y.view(-1)
                total_ones += int((y_flat == 1).sum().item())
                total_zeros += int((y_flat == 0).sum().item())
            else:
                if int(y) == 1:
                    total_ones += 1
                else:
                    total_zeros += 1
    print(f"Total number of 1 labels: {total_ones}")
    print(f"Total number of 0 labels: {total_zeros}")

    # Concat all datasets
    train_val_data = ConcatDataset(datasets)
    # build y array for sklearn: one scalar label per graph in same order
    y_array = np.array([int(train_val_data[i].y.view(-1).item()) for i in range(len(train_val_data))], dtype=int)
    # custom CV (must yield indices into concatenated dataset)
    custom_cv = GNNs_Models_Classifiers.MultiDatasetPredefinedSplit(datasets)

    # sanity-check CV mapping (print a few splits)
    splits = list(custom_cv.split(train_val_data))
    print(f"Custom CV produced {len(splits)} splits (expected {len(datasets)}). Example split sizes (train/test):")
    for k, (tr, te) in enumerate(splits[:3]):
        print(f"  split {k}: train {len(tr)} test {len(te)}; sample idxs -> train[:5]={np.array(tr)[:5]} test[:5]={np.array(te)[:5]}")

    # param grid for grid search
    param_grid = {
        'input_dim': [20], # or 1 for all features equal to 1
        'hidden_dim': [16, 32],
        #'num_heads': [2, 4],  # Comment out for GCN and GraphSAGE
        'output_dim': [2],
        'dropout': [0, 0.1],
        'learning_rate': [0.1, 0.01],
        'epochs': [10, 25],
        'batch_size': [32, 64],
        'weight_decay': [0.0, 0.01],
    }

    model = 'GraphSAGE'

    grid_search = GridSearchCV(
        estimator=GNNs_Models_Classifiers.MyGNNClassifier(verbose=True, model_name=model),
        param_grid=param_grid,
        scoring=make_scorer(f1_score),   # score for f1_score or recall_score
        refit=True,
        cv=custom_cv,
        verbose=3,
        n_jobs=200   # number of parallel jobs
    )

    # Train and Validate the model
    try:
        print("Starting GridSearchCV.fit(...) — this may take a while.")
        grid_search.fit(train_val_data, y_array)
    except Exception as e:
        print("ERROR during grid_search.fit():", e)
        raise

    # Get the best estimator (model) and best parameters
    best_model = grid_search.best_estimator_
    best_params = grid_search.best_params_

    # Save the best model and parameters
    save_model(best_model=best_model, best_params=best_params, path=path_to_save_results)
    # Save the grid search results to a CSV file and rename the columns
    save_grid_search_results(grid_search=grid_search, path_train_data=path_train_data, path=path_to_save_results) 
    
    print("Grid search finished. Best params:", best_params)
    return grid_search, best_model, best_params


def main(path_train_data, path_case_studies, path_to_save_results):
    # Train and test the GNN model
    GNN_training_and_test(path_train_data, path_case_studies, path_to_save_results)


if __name__ == "__main__":
    # Paths to the training data folders
    path_train_data = [
        "./Saved_Geometric_Datas/Asm2Vec/Picohttpparser", 
        "./Saved_Geometric_Datas/Asm2Vec/CSimpleJSONParser", 
        "./Saved_Geometric_Datas/Asm2Vec/Benoitc_HTTP", 
        "./Saved_Geometric_Datas/Asm2Vec/CParserXML", 
        "./Saved_Geometric_Datas/Asm2Vec/cJSON", 
        "./Saved_Geometric_Datas/Asm2Vec/YACC_Calculator",
        "./Saved_Geometric_Datas/Asm2Vec/ELF_Parser",
        "./Saved_Geometric_Datas/Asm2Vec/Network_Packet_Analyzer",
        "./Saved_Geometric_Datas/Asm2Vec/Packcc",
        "./Saved_Geometric_Datas/Asm2Vec/PCAP_Parser",
    ]
    # Paths to the case studies
    path_case_studies = [
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_sparse.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_mutool.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_muraster.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_busybox.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_cp.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_cat.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_miio_notify.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_traceroute.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_aes_crypt.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_chr.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_crontab.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_find.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_head.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_tail.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_smemcap.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_strings.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_xargs.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_jsmn.pt",
        "./Case_Studies/Saved_Geometric_Datas/case_studies_geometric_datas_libcsv.pt",
    ]
    # Path to save the results
    path_to_save_results = "./Results/"
    # main function
    main(path_train_data, path_case_studies, path_to_save_results)


    # first activate: conda activate test-3.10.0-env
    # run with: python -m asm2vec_experiments.GNN_training_and_test > output.txt 2>&1



####################################################################################################################################

    # No cross Weighted, Si sampler, Optimized by Recall, usa "analyze_validation_data.py" to find the best parameters (not using the json file)
    # Safetorch (Mean)
    #   Graph SAGE: 0.90    -> No tutti 1 o 0
    #   RGCN: 0.90          -> No tutti 1 o 0
    #   GCN: 0.90           -> Tutti 1 o 0
    #   GAT: 0.85           -> Tutti 1 o 0 su 4 binari / 10
    # Asm2Vec (Mean)
    #   Graph SAGE: 0.80    -> No tutti 1 o 0
    #   RGCN: 0.74          -> No Tutti 1 o 0
    #   GCN: 0.79           -> No Tutti 1 o 0
    #   GAT: 0.83           -> Tutti 1 o 0 su 1 binari / 10



    # No cross Weighted, Si sampler, Optimized by Recall, usa  the json file to find the best parameters
    # Safetorch (Mean)
    #   Graph SAGE: 0.90  -> No tutti 1 o 0
    #   RGCN: 0.90        -> No tutti 1 o 0
    #   GCN: 0.90         -> Tutti 1 o 0 
    #   GAT: 0.85         -> Tutti 1 o 0 su 4 binari / 10
    # Asm2Vec (Mean)
    #   Graph SAGE: 0.80 -> Non tutti 1 o 0 
    #   RGCN: 0.74      -> No Tutti 1 o 0
    #   GCN: 0.76       -> Tutti 1 o 0
    #   GAT:  0.83      -> Tutti 1 o 0 su 2 binari / 10

####################################################################################################################################

    # Si cross Weighted, Si sampler, Optimized by Recall, usa "analyze_validation_data.py" to find the best parameters (not using the json file)
    # Safetorch (Mean)
    #   Graph SAGE:
    #   RGCN: 
    #   GCN: 
    #   GAT: 
    # Asm2Vec (Mean)
    #   Graph SAGE:
    #   RGCN:
    #   GCN:
    #   GAT:



    # Si cross Weighted, Si sampler, Optimized by Recall, usa  the json file to find the best parameters
    # Safetorch (Mean)
    #   Graph SAGE: 
    #   RGCN: 
    #   GCN 
    #   GAT
    # Asm2Vec (Mean)
    #   Graph SAGE:
    #   RGCN:
    #   GCN:
    #   GAT:

####################################################################################################################################


    # No cross Weighted, Si sampler, Optimized by f1-Score, usa "analyze_validation_data.py" to find the best parameters (not using the json file)
    # Safetorch (Mean)
    #   Graph SAGE: 
    #   RGCN:
    #   GCN 
    #   GAT
    # Asm2Vec (Mean)
    #   Graph SAGE:
    #   RGCN:
    #   GCN:
    #   GAT:



    # No cross Weighted, Si sampler, Optimized by f1-Score, usa  the json file to find the best parameters
    # Safetorch (Mean)
    #   Graph SAGE:
    #   RGCN: 
    #   GCN 
    #   GAT
    # Asm2Vec (Mean)
    #   Graph SAGE:
    #   RGCN:
    #   GCN:
    #   GAT:


####################################################################################################################################


    # Si cross Weighted, Si sampler, Optimized by f1-Score, usa "analyze_validation_data.py" to find the best parameters (not using the json file)
    # Safetorch (Mean)
    #   Graph SAGE: 
    #   RGCN:
    #   GCN 
    #   GAT
    # Asm2Vec (Mean)
    #   Graph SAGE:
    #   RGCN:
    #   GCN:
    #   GAT:



    # Si cross Weighted, Si sampler, Optimized by f1-Score, usa  the json file to find the best parameters
    # Safetorch (Mean)
    #   Graph SAGE:
    #   RGCN: 
    #   GCN 
    #   GAT
    # Asm2Vec (Mean)
    #   Graph SAGE:
    #   RGCN:
    #   GCN:
    #   GAT:


####################################################################################################################################


