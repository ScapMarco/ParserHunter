import pandas as pd
import matplotlib.pyplot as plt

def create_dataframe_from_csv(file_path):
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
        print(f"DataFrame path: {file_path}")
        
        # Convert string representations of lists to actual lists
        for column in df.columns:
            if df[column].dtype == 'object':
                df[column] = df[column].apply(lambda x: eval(x) if isinstance(x, str) and x.startswith('{') else x)
        
        # Columns to exclude
        exclude_columns = ["mean_fit_time", "std_fit_time", "mean_score_time", "std_score_time",
                           "param_batch_size", "param_dropout", "param_epochs", "param_hidden_dim", 
                           "param_learning_rate", "param_input_dim", "param_output_dim", 
                           "param_weight_decay", "params", 
                           #"param_num_heads" # comment out num_heads for GCN
                           ]
                           
        
        # Drop the specified columns
        df = df.drop(columns=exclude_columns)
        
        return df
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return None



def plotting_scores(df):
    # Specific columns to plot
    test_score_columns = [
        "Picohttpparser_test_score",
        "CSimpleJSONParser_test_score",
        "Benoitc_HTTP_test_score",
        "CParserXML_test_score",
        "cJSON_test_score",
        "YACC_Calculator_test_score",
        "ELF_Parser_test_score",
        "Network_Packet_Analyzer_test_score",
        "Packcc_test_score",
        "PCAP_Parser_test_score"
    ]
    
    # Extract scores for the specified test score columns
    scores = df[test_score_columns].iloc[0]  # Assuming single row for the best model

    # Creating the plot
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(scores.index, scores.values, color="skyblue")
    ax.set_xlabel("Test Score Metrics")
    ax.set_ylabel("Score Value")
    ax.set_title("Test Metric Scores for Different Binaries")
    plt.xticks(rotation=45, ha="right")

    # Adding the score values on top of each bar
    for bar, value in zip(bars, scores.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f'{value:.2f}', ha='center', va='bottom')

    plt.tight_layout()
    plt.grid()
    plt.show()


def main(file_path):
    # Read the CSV data file
    df = create_dataframe_from_csv(file_path)

    # Display the DataFrame information
    print("\nDataFrame Info:")
    print(df.info())

    # Take the best model
    best_model = df[df["rank_test_score"] == 1]
    print("\nBest Model:")
    # Round the values to 4 decimal places
    best_model = best_model.round(4)
    # Display the best model
    print(best_model)

    # Plot the scores for the best model
    plotting_scores(best_model)

if __name__ == '__main__':
    # Define the embedding model used
    embedding_model = "Safetorch"
    # Path to the CSV file
    file_path = f"./Results/{embedding_model}/Safetorch_RGCN_NOCrossweights_and_sampler/result_gridsearch.csv"
    main(file_path)