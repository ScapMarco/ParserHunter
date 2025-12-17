import json
import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.metrics import recall_score, accuracy_score, precision_score, f1_score, roc_auc_score


def plot_metric_scores_transpose_results(df):
    """
    Plots a boxplot for each metric with scores (Recall, Precision, F1, AUC_ROC, Accuracy),
    using different colors for the test cases and a specified order for Validation_Parser.

    Parameters:
    df (pd.DataFrame): DataFrame containing the test scores and parameters.

    Returns:
    None: Displays the boxplot.
    """

    # Specify the order for Validation_Parser
    parser_order = [
        "PicoHTTPParser",
        "CSimpleJSONParser",
        "Benoitc_HTTP",
        "CParserXML",
        "cJSON_Parser",
        "YACC_Calculator",
        "ELF_Parser",
        "Network_Packet_Analyzer",
        "Packcc",
        "PCAP_Parser"
    ]

    # Ensure the Validation_Parser column is treated as a categorical variable with the specified order
    df["Validation_Parser"] = pd.Categorical(df["Validation_Parser"], categories=parser_order, ordered=True)

    # Reshape the dataframe from wide to long format
    long_df = df.melt(
        id_vars=["Validation_Parser"],
        value_vars=["recall", "precision", "f1_score", "roc_auc", "accuracy"],
        var_name="metric",
        value_name="score"
    )

    # Create the boxplot
    plt.figure(figsize=(15, 8))
    plt.rcParams["mathtext.fontset"]
    fontsize = 24
    plt.rcParams.update({'font.size': fontsize, 'font.family': 'STIXGeneral', 'mathtext.fontset': 'stix'})

    sns.boxplot(
        data=long_df,
        x="metric",
        y="score",
        hue="Validation_Parser",
        hue_order=parser_order,  # Ensure the correct order of categories
        palette="Set2",
        linewidth=2.5  # Make boxplot lines thicker
    )

    # Plot Settings
    plt.xlabel("Metrics", fontsize=fontsize)
    plt.ylabel("Scores", fontsize=fontsize)
    plt.xticks(fontsize=fontsize / 2, rotation=0)
    plt.yticks(fontsize=fontsize / 2)
    plt.legend(
        title="Validation Parser",
        loc="lower right",  # Legend inside the plot
        fontsize=fontsize / 3,
        title_fontsize=fontsize / 3
    )
    plt.tight_layout()
    plt.grid()

    # Show plot
    plt.show()


def load_best_config_from_json(model_dir):
    """
    Loads the best hyperparameter configuration from a JSON file.

    Args:
        model_dir (str): Path to the model directory.

    Returns:
        dict: Hyperparameter configuration.
    """
    json_path = os.path.join(model_dir, "best_params.json")

    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"Best config JSON not found at: {json_path}")

    with open(json_path, "r") as f:
        config = json.load(f)

    return config


# Define a function to compute the metrics
def compute_metrics(group):
    y_true = group['true_label']
    y_pred = group['prediction']
    y_prob = group['parser_probability']
    metrics = {
        'recall': recall_score(y_true, y_pred),
        'accuracy': accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred),
        'f1_score': f1_score(y_true, y_pred),
        'roc_auc': roc_auc_score(y_true, y_prob)
    }
    return pd.Series(metrics)


def get_best_config(csv_path, metric, model, use_pretrained_config=False, model_dir=None):
    """
    Either finds the best hyperparameter configuration or loads it from JSON.

    Args:
        csv_path (str): Path to the CSV file.
        metric (str): Metric to evaluate.
        model (str): Model name.
        use_pretrained_config (bool): If True, load config from JSON.
        model_dir (str): Required if use_pretrained_config is True.

    Returns:
        dict: Best metric values per Validation_Parser + mean/std.
    """
    df = pd.read_csv(csv_path)

    # Define hyperparameter columns
    if model in [
        "GCN", "GraphSAGE_noCRoss_sisampler_f1score", "GraphSAGE_all1",
        "GCN_all1", "Safetorch_RGCN_NOCrossweights_and_sampler",
        "TEST_GraphSAGE_NOCrossweight_and_sampler"
    ]:
        hyperparams = ["hidden_dim", "dropout", "learning_rate", "epochs", "batch_size", "weight_decay"]

    elif model in [
        "GAT", "GAT_siCRoss_sisampler_f1score",
        "GAT_all1", "TEST_GAT_no_weight_Cross_Entropy_safetorch"
    ]:
        hyperparams = ["hidden_dim", "dropout", "learning_rate", "epochs",
                       "batch_size", "weight_decay", "num_heads"]

    # Ensure numeric types
    for col in hyperparams:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # --------------------------------------------------
    # CASE 1: Load pretrained configuration from JSON
    # --------------------------------------------------
    if use_pretrained_config:
        if model_dir is None:
            raise ValueError("model_dir must be provided when use_pretrained_config=True")

        best_config_dict = load_best_config_from_json(model_dir)

        print("Loaded best configuration from JSON:")
        print(best_config_dict)

    # --------------------------------------------------
    # CASE 2: Search best configuration from CSV
    # --------------------------------------------------
    else:
        grouped = df.groupby(hyperparams)[metric].mean().reset_index()
        best_config = grouped.loc[grouped[metric].idxmax(), hyperparams]
        best_config_dict = best_config.to_dict()

        print(f"Best configuration for {metric}:")
        print(best_config_dict)

    # --------------------------------------------------
    # Filter dataframe using selected configuration
    # --------------------------------------------------
    # Keep only hyperparameters that exist in the CSV
    filtered_config = {
        k: v for k, v in best_config_dict.items()
        if k in hyperparams
    }

    missing = set(hyperparams) - set(filtered_config.keys())
    if missing:
        raise ValueError(
            f"JSON config is missing required hyperparameters: {missing}"
        )

    ############################
    # Filter dataframe
    best_df = df[df[hyperparams].eq(filtered_config).all(axis=1)]

    # -------------------------------
    # Recall (selection metric)
    # -------------------------------
    recall_per_parser = dict(
        zip(best_df["Validation_Parser"], best_df["recall"])
    )

    recall_mean = best_df["recall"].mean()
    recall_std = best_df["recall"].std()

    # -------------------------------
    # ROC AUC (reported metric)
    # -------------------------------
    roc_auc_per_parser = dict(
        zip(best_df["Validation_Parser"], best_df["roc_auc"])
    )

    roc_auc_mean = best_df["roc_auc"].mean()
    roc_auc_std = best_df["roc_auc"].std()

    # -------------------------------
    # Printing (clear and unambiguous)
    # -------------------------------
    print("\nRecall per Validation Parser (best Recall configuration):")
    for k, v in recall_per_parser.items():
        print(f"  {k}: {v}")

    print(f"\nRecall summary:")
    print(f"  mean: {recall_mean}")
    print(f"  std : {recall_std}")

    print("\nROC AUC per Validation Parser (same configuration):")
    for k, v in roc_auc_per_parser.items():
        print(f"  {k}: {v}")

    print(f"\nROC AUC summary:")
    print(f"  mean: {roc_auc_mean}")
    print(f"  std : {roc_auc_std}")

    # -------------------------------
    # Return structured results
    # -------------------------------
    return {
        "recall_per_parser": recall_per_parser,
        "recall_mean": recall_mean,
        "recall_std": recall_std,
        "roc_auc_per_parser": roc_auc_per_parser,
        "roc_auc_mean": roc_auc_mean,
        "roc_auc_std": roc_auc_std,
    }


def main(model, metric, embedding_model, use_pretrained_config=False):

    # Load the CSV data file
    df = pd.read_csv(f"./Results/{embedding_model}/{model}/analyzed_validation_results.csv")
    # Group by the hyperparameters and dataset_len, then compute the metrics
    if model in ["GCN", "GraphSAGE_noCRoss_sisampler_f1score", "TEST_RGCN_noCRoss_sisampler_recall", "GraphSAGE_all1", "GCN_all1", "Safetorch_RGCN_NOCrossweights_and_sampler", "TEST_GraphSAGE_NOCrossweight_and_sampler"]:
        results = df.groupby(['hidden_dim', 'dropout', 'learning_rate', 'epochs', 'batch_size', 'weight_decay', 'dataset_len']).apply(compute_metrics).reset_index()
    elif model in ["GAT",  "GAT_siCRoss_sisampler_f1score", "GAT_all1", "TEST_GAT_no_weight_Cross_Entropy_safetorch"]:
        results = df.groupby(['hidden_dim', 'dropout', 'learning_rate', 'epochs', 'batch_size', 'weight_decay', 'num_heads', 'dataset_len']).apply(compute_metrics).reset_index()

    results.sort_values('dataset_len', ascending=False)

    # Mapping dictionary for dataset_len values
    mapping = {
        760: "PicoHTTPParser",              # Train on the rest: 653 + 421 + 362 + 2293 + 252 + 679 + 382 + 1802 + 294 = 7138
        653: "CSimpleJSONParser",           # Train on the rest: 760 + 421 + 362 + 2293 + 252 + 679 + 382 + 1802 + 294 = 7245
        421: "Benoitc_HTTP",                # Train on the rest: 760 + 653 + 362 + 2293 + 252 + 679 + 382 + 1802 + 294 = 7477
        362: "CParserXML",                  # Train on the rest: 760 + 653 + 421 + 2293 + 252 + 679 + 382 + 1802 + 294 = 7536
        2293: "cJSON_Parser",               # Train on the rest: 760 + 653 + 421 + 362 + 252 + 679 + 382 + 1802 + 294 = 5605
        252: "YACC_Calculator",             # Train on the rest: 760 + 653 + 421 + 362 + 2293 + 679 + 382 + 1802 + 294 = 7646
        679: "ELF_Parser",                  # Train on the rest: 760 + 653 + 421 + 362 + 2293 + 252 + 382 + 1802 + 294 = 7219
        382: "Network_Packet_Analyzer",     # Train on the rest: 760 + 653 + 421 + 362 + 2293 + 252 + 679 + 1802 + 294 = 7516
        1802: "Packcc",                     # Train on the rest: 760 + 653 + 421 + 362 + 2293 + 252 + 679 + 382 + 294 = 6096
        294: "PCAP_Parser",                 # Train on the rest: 760 + 653 + 421 + 362 + 2293 + 252 + 679 + 382 + 1802 = 7604
    }

    # Replace values in the 'dataset_len' column
    results['dataset_len'] = results['dataset_len'].replace(mapping)
    # Rename the column
    results.rename(columns={'dataset_len': 'Validation_Parser'}, inplace=True)
    # Save the dataframe to a CSV file
    results.to_csv(f"./Results/{embedding_model}/{model}/validation.csv", index=False)

    # Plot the metric scores
    #plot_metric_scores_transpose_results(results)

    # Get the best configuration for the selected metric
    print(f"\n")
    
    model_dir = f"./Results/{embedding_model}/{model}"

    best_recall_values = get_best_config(
        csv_path=f"{model_dir}/validation.csv",
        metric=metric,
        model=model,
        use_pretrained_config=use_pretrained_config,
        model_dir=model_dir
    )
    # for key, value in best_recall_values.items():
    #     print(f"{key}: {value}")


if __name__ == "__main__":
    model = "GraphSAGE_noCRoss_sisampler_f1score" # Model used
    metric = "recall"                           # Metric to evaluate
    embedding_model = "Safetorch"               # Embedding model used

    # Set to True to load best_params.json
    use_pretrained_config = False

    main(
        model=model,
        metric=metric,
        embedding_model=embedding_model,
        use_pretrained_config=use_pretrained_config
    )