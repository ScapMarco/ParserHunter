# ParserHunter

This repository contains the data and scripts used for the training and validation of the experiments described in the paper *ParserHunter: Identify Parsing Functions in Binary Code*.

---


## Requirements

This project requires three Conda environments for different functionalities. Below are the setup instructions:


1. **Function Extraction Environment** (`test-3.9-env`):
   - **Python Version**: `3.9.15`
   - **Key Packages**: `angr`, `r2pipe`, `timeout-decorator`
   - **Setup**:
     ```bash
     conda create -n test-3.9-env python=3.9.15
     conda activate test-3.9-env
     conda install angr r2pipe timeout-decorator
     ```

2. **Geometric Data Creation and GNN Model Inference Environment** (`test-3.10.0-env`):
   - **Python Version**: `3.10.0`
   - **Key Packages**: `torch`, `torch-geometric`, `pandas`, `matplotlib`, `flask`
   - **Setup**:
     ```bash
     conda create -n test-3.10.0-env python=3.10.0
     conda activate test-3.10.0-env
     conda install pytorch -c pytorch
     conda install torch-geometric pandas matplotlib flask
     ```

3. **Asm2Vec Model Inference Environment** (`asm2vec`):
   - **Python Version**: `3.8.19`
   - **Key Packages**: `gensim`, `asm2vec`, `numpy`, `scipy`
   - **Setup**:
     ```bash
     conda create -n asm2vec python=3.8.19
     conda activate asm2vec
     conda install gensim numpy scipy
     ```


## Training and Validation Overview

### Replicating the Asm2Vec Training Process:
1. **Prepare Function List**  
   Extract a list of functions from the binary executable files and save it in `Asm2Vec/Dictionaries_list_of_functions` as `.pt` files.  
   - Use: `Binaries/extract_list_functions.py`

2. **Extract Assembly Instructions**  
   Extract all assembly instructions from the basic blocks of the Control Flow Graphs (CFGs) and save them as a single file (`Asm2Vec/assembly_codes.txt`).  
   - Use: `Asm2Vec/asm2Vec_extract_assembly_instructions.py`

3. **Train Asm2Vec Model**  
   Clean the assembly instructions and train the Asm2Vec model, saving it in `Asm2Vec/asm2vec_model`.  
   - Use: `Asm2Vec/asm2Vec_training.py`

4. **Infer Vectors**  
   Use the trained Asm2Vec model to infer vector embeddings for the assembly instructions of functions.  
   - Use: `Asm2Vec/asm2vec_inference.py`  
   - Input: Function assembly instructions  

---

### Replicating the GNN Training and Validation Process using the an embedding moldel (Asm2Vec or SafeTorch):
1. **Data Preparation**  
   Extract and manually label function data, saving the labeled datasets in `Dictionaries_Labeled_Datas/`.  
   - Use: `Binaries/manual_labelling.py`

2. **Create Geometric Data**  
   From the list of labeled data creates PyTorch Geometric data objects and save them in `Saved_Geometric_Datas/`.  
   - Steps:  
     a. Extract CFGs for each function.  
     b. Enrich CFG nodes with features using the trained Asm2Vec or SAFETorch embedding model.  
     c. Convert to PyTorch Geometric Data objects.  
     d. Save as `.pt` files.  
   - Use: `asm2vec_experiments/create_geometric_datas.py` for the Asm2Vec embedding model or `safetorch_experiments/create_geometric_datas.py` for the SafeTorch embedding model.

3. **Train GNN Model**  
   Train a GNN model using a grid search to find the best hyperparameters. Save the following results:  
     - Best model: `Results/embedding_model_name/model_name/best_model.pth`  
     - Best hyperparameters: `Results/embedding_model_name/model_name/best_params.json`  
     - Grid search results: `Results/embedding_model_name/model_name/result_gridsearch.csv`  
   - Use: `asm2vec_experiments/gnn_training_and_test.py` for the Asm2Vec embedding model or `safetorch_experiments/gnn_training_and_test.py` for the SafeTorch embedding model.
---


## How to Replicate Plots and Tables
The following scripts and notebooks can be used to replicate the plots and tables presented in the paper:

- **Table 2:** Distribution of functions per parser library and other training data statistics.
  - Run: `Plots/analyze_training_data.py`

- **Table 4 and Table 8:** Performance comparison of GCN and GAT across different metrics and embedding models.
  - Run: `Plots/analyze_validation_data.py`  and `Plots/analyze_grid_search_best_model.py` to produce the csv table `validation.csv` inside each model folder, then filter out by the best parameters (found inside the file `best_params.json`). 

- **Table 5:** Recall of 3 PIE-based baselines.
  - Run `Plots/static_code_exploration.ipynb`
  
- **Table 6 and Table 7:** Recall of SAFE embeddings using KNN and performance comparison of XGBoost and a Neural Network Classifier.
  - Run `Plots/safetorch_data_exploration.ipynb`

- **Figure 6:** Reverse cumulative distribution of the prediction consistency across all compilation settings
  - Run: `Plots/robustness.ipynb`  

- **Figure 7 and 8:** Recall results for different optimization levels for x86-32 and 64 architectures
  - Run: `Plots/compilers_recall_validation_results.ipynb`  

- **Table 9:** Mean Recall results for different LLM and input code representations 
  - Run: `Plots/analyzed_llm_classifications.ipynb`  


## Project Structure

### Directories:
- **Binaries/**: Executable and tools for function extraction. 
- **Asm2Vec/**: Asm2Vec training and inference files.  
- **Asm2Vec/Dictionaries_list_of_functions/**: Function lists extracted from binaries.  
- **safetorch/**: SafeTorch model files. 
- **safetorch/outputs**: SafeTorch model outputs for baselines (comparison with SAFE paper)..
- **code_counting_features/**: Code and saved results for manual code feature experiments (comparison with PIE paper).
- **asm2vec_experiments/**: Create geometric data and GNN training using Asm2Vec embeddings.  
- **safetorch_experiments/**: Create geometric data and GNN training using SafeTorch embeddings.
- **Case_Studies/**: Geometric data, function lists for case studies and tools for create case studies geometric data.
- **Dictionaries_Labeled_Datas/**: Labeled function lists.  
- **GNNs_Models/**: GNN model definitions.  
- **Plots/**: Analysis and Plot generation scripts.  
- **Results/**: Results from GNN training and test. 
- **Saved_Geometric_Datas/**: Saved PyTorch Geometric data objects used for training and test the GNN models.

### Key Python Files:
- `create_geometric_datas.py`: Create PyTorch Geometric data from labeled datasets.  
- `from_CFG_to_DataGeometric.py`: Support script for data creation.  
- `gnn_training_and_test.py`: Train/validate GNN model.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.