import os
import torch

def load_dataset_from_folder(folder_path):
    datas_list = []
    # Load data from the folder
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            geometric_data = torch.load(file_path)
            datas_list.extend(geometric_data)
    return datas_list

def statistics_training_data(path_train_data):
    # Load all datasets and keep track of their lengths
    datasets = [load_dataset_from_folder(folder) for folder in path_train_data]

    print(f"Total binaries len(datasets): {len(datasets)}")
    overall_ones = 0
    overall_zeros = 0

    for i, dataset in enumerate(datasets):
        dataset_name = os.path.basename(path_train_data[i])
        num_ones = 0
        num_zeros = 0

        for data in dataset:
            num_ones += data.y.sum().item()
            num_zeros += (1 - data.y).sum().item()

        overall_ones += num_ones
        overall_zeros += num_zeros

        total_labels = num_ones + num_zeros
        print(f"Statistics for dataset '{dataset_name}':")
        print(f"    Number of 1 labels: {num_ones}")
        print(f"    Number of 0 labels: {num_zeros}")
        print(f"    Total labels: {total_labels}")

    print("\nOverall statistics:")
    print(f"    Total number of 1 labels: {overall_ones}")
    print(f"    Total number of 0 labels: {overall_zeros}")
    print(f"    Total labels: {overall_ones + overall_zeros}")


def main():
    # Define the embedding model used
    embedding_model = "Safetorch"
    # Path to the training data folders
    path_train_data = [
        f"./Saved_Geometric_Datas/{embedding_model}/Picohttpparser", 
        f"./Saved_Geometric_Datas/{embedding_model}/CSimpleJSONParser", 
        f"./Saved_Geometric_Datas/{embedding_model}/Benoitc_HTTP", 
        f"./Saved_Geometric_Datas/{embedding_model}/CParserXML", 
        f"./Saved_Geometric_Datas/{embedding_model}/cJSON", 
        f"./Saved_Geometric_Datas/{embedding_model}/YACC_Calculator",
        f"./Saved_Geometric_Datas/{embedding_model}/ELF_Parser",
        f"./Saved_Geometric_Datas/{embedding_model}/Network_Packet_Analyzer",
        f"./Saved_Geometric_Datas/{embedding_model}/Packcc",
        f"./Saved_Geometric_Datas/{embedding_model}/PCAP_Parser"
    ]

    # Statistics for the training data
    statistics_training_data(path_train_data)


if __name__ == '__main__':
    main()