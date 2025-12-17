import os
import json
import torch
import random
import numpy as np
import pandas as pd
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import make_scorer, recall_score, f1_score, roc_auc_score
from torch.utils.data import ConcatDataset

# Models 
import GNNs_Models.GNNs_Models_Classifiers as GNNs_Models_Classifiers


# use conda env test-3.10.0-env


def set_case_studies_node_features_to_one(case_studies):
    """
    Replace every Data.x in `case_studies` with a column of ones shaped [num_nodes, 1].
    Operates in-place. Works even if .x is None or missing.
    """
    # Normalize to list
    if not isinstance(case_studies, (list, tuple)):
        case_studies = [case_studies]

    for d in case_studies:
        # Infer number of nodes robustly
        n_nodes = getattr(d, "num_nodes", None)
        if n_nodes is None or n_nodes == 0:
            if hasattr(d, "x") and d.x is not None:
                n_nodes = int(d.x.size(0))
            elif hasattr(d, "edge_index") and d.edge_index is not None:
                try:
                    n_nodes = int(d.edge_index.max().item()) + 1
                except Exception:
                    n_nodes = None

        if n_nodes is None or n_nodes == 0:
            raise ValueError(f"Cannot determine number of nodes for graph from file {getattr(d, 'filename', '?')}")

        # Create tensor of ones [n_nodes, 1]
        device = d.x.device if hasattr(d, "x") and d.x is not None else "cpu"
        d.x = torch.ones((n_nodes, 1), dtype=torch.float32, device=device)


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
            
    #set_case_studies_node_features_to_one(case_studies=datas_list)
    #set_case_studies_node_features_to_zero(case_studies=datas_list)
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



def GNN_training_and_test(path_train_data, path_to_save_results):
    # reproducibility & thread settings
    torch.manual_seed(42)
    random.seed(42)
    np.random.seed(42)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

    # Load datasets
    datasets = [load_dataset_from_folder(folder) for folder in path_train_data]
    
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
              

    param_grid = {
        'input_dim': [100], # or 1 for all features equal to 1
        'hidden_dim': [16, 32],
        #'num_heads': [2, 4], # Comment out for GCN and GraphSAGE
        'output_dim': [2],
        'dropout': [0, 0.1],
        'learning_rate': [0.1, 0.01],
        'epochs': [10, 25],
        'batch_size': [32, 64],
        'weight_decay': [0.0, 0.01],
        'num_relations': [1]
    }

    model = 'GCN'  

    grid_search = GridSearchCV(
        estimator=GNNs_Models_Classifiers.MyGNNClassifier(verbose=True, model_name=model),
        param_grid=param_grid,
        scoring=make_scorer(recall_score),   # Scoring method: recall_score, f1_score, roc_auc_score, accuracy_score
        refit=True,
        cv=custom_cv,
        verbose=3,
        n_jobs=200   # number of parallel jobs
    )
    # fit grid search
    try:
        print("Starting GridSearchCV.fit(...) — this may take a while.")
        grid_search.fit(train_val_data, y_array)
    except Exception as e:
        print("ERROR during grid_search.fit():", e)
        raise
    # Take best model and params
    best_model = grid_search.best_estimator_
    best_params = grid_search.best_params_

    save_model(best_model=best_model, best_params=best_params, path=path_to_save_results)
    save_grid_search_results(grid_search=grid_search, path_train_data=path_train_data, path=path_to_save_results)

    print("Grid search finished. Best params:", best_params)
    return grid_search, best_model, best_params

###############################################################################################################################################

def main(path_train_data, path_to_save_results):
    # Train and test the GNN model
    GNN_training_and_test(path_train_data, path_to_save_results)

if __name__ == "__main__":
    # Paths to the training data folders
    path_train_data = [
        "./Saved_Geometric_Datas/Safetorch/Picohttpparser", 
        "./Saved_Geometric_Datas/Safetorch/CSimpleJSONParser", 
        "./Saved_Geometric_Datas/Safetorch/Benoitc_HTTP", 
        "./Saved_Geometric_Datas/Safetorch/CParserXML", 
        "./Saved_Geometric_Datas/Safetorch/cJSON", 
        "./Saved_Geometric_Datas/Safetorch/YACC_Calculator",
        "./Saved_Geometric_Datas/Safetorch/ELF_Parser",
        "./Saved_Geometric_Datas/Safetorch/Network_Packet_Analyzer",
        "./Saved_Geometric_Datas/Safetorch/Packcc",
        "./Saved_Geometric_Datas/Safetorch/PCAP_Parser",
    ]
    # Path to save the results
    path_to_save_results = "./Results/"
    # main function
    main(path_train_data, path_to_save_results)

    # first activate: conda activate test-3.10.0-env
    # run with: python -m safetorch_experiments.gnn_training_and_test_with_safetorch_embeddings > output.txt 2>&1