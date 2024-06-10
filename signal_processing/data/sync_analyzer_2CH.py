"""
----------------------------
+-HeartBeat_SynC_Quantizer-+
----------------------------
-emmanuel@interspecifics.cc-
may02.2024
+--------------------------+
A. 
    Analize recorded ECG sessions
    Train a model based on delta-features
    Use the model to classify the segments
    Visualize analized segments 
B. 
    Uses delta-feature model
    Real time classification of window-time events


sync_analyzer.py:
    uses 4 channels record 
    estimates time differences in pulses between choosen signal and the others
    creates dts.csv and dts_features.csv with the output of this differences

sync_analyzer_2CH.py:
    uses 2 channel record
"""



import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

CH_NS=['PULSE','RAW', 'AVG']


def read_csv_data(filepath):
    """
    Reads a CSV file and expects 12 columns corresponding to 4 groups of 3 columns each.
    Args:
    filepath (str): The path to the CSV file.

    Returns:
    DataFrame: A pandas DataFrame containing the loaded data.
    """
    return pd.read_csv(filepath)



def plot_data(data, start_index, end_index, value_index):
    """
    Plots selected data from a specified range and column index for each group.

    Args:
    data (DataFrame): The data to plot, expected to have 12 columns.
    start_index (int): The starting index of the range of data points to plot.
    end_index (int): The ending index of the range of data points to plot.
    value_index (int): The index of the value to plot in each group (0, 1, or 2).
    """
    if value_index < 0 or value_index > 2:
        raise ValueError("value_index must be 0, 1, or 2")

    fig, axs = plt.subplots(4, 1, figsize=(10, 8))

    for i in range(4):
        col_index = i * 3 + value_index
        axs[i].plot(data.iloc[start_index:end_index, col_index])
        axs[i].set_title(f'CHANNEL{i+1}: {CH_NS[value_index]}')
        axs[i].set_xlabel('Index')
        axs[i].set_ylabel('Value')

    plt.tight_layout()
    plt.show()



def estimate_time_differences(data, sample_frequency, window_size = 100, base_signal_index=0):
    """
    For each window of 100 samples, estimate the time difference between the pulse in the signal from the first group and the pulses in the samples of the other groups in the windows.
    Add a new column for each group with the value of the corresponding time difference for all the 100 positions of the time window.
    Save the resulting differences in 'dts.csv'.

    Args:
    data (DataFrame): The data to process, expected to have 12 columns.
    sample_frequency (int): The number of samples per second.
    window_size (int): The number of samples per window.
    base_signal_index (int): The index of the signal used as reference (0, 1, 2, or 3).
    """
    # Calculate the time interval between samples in seconds
    time_interval_seconds = 1 / sample_frequency
    # Number of windows
    num_windows = data.shape[0] // window_size

    # Prepare DataFrame to store time differences
    time_diffs = pd.DataFrame(index=np.arange(num_windows * window_size))
    time_diffs_features = pd.DataFrame(index=np.arange(num_windows))
    deltas = [[] for _ in range(4)]
    deltas_features = [[] for _ in range(4)]

    #select the base signal
    base_signal = data.iloc[:, base_signal_index]
    signals = [[] for _ in range(4)]
    for i in range(4):
        signals[i] = data.iloc[:, i * 3]

    # Process each window, group by group
    for w in range(num_windows):
        base_window = base_signal[w*window_size:(w+1)*window_size]
        base_pulses = np.where(base_window > 0)[0]
        for i in range(4):
            window = signals[i][w*window_size:(w+1)*window_size]
            # Find index of pulses in the window
            pulses = np.where(window > 0)[0]
            # Calculate time differences for pulses in the window
            if len(pulses) > 0 and len(base_pulses) > 0:
                pulse_diff_time = (base_pulses[0] - pulses[0]) * time_interval_seconds
            else:
                pulse_diff_time = -1  # No pulse in this window
            # Fill the window with the time difference
            deltas[i].extend([pulse_diff_time]*window_size)
            deltas_features[i].append(pulse_diff_time)
    for i in range(4):
        time_diffs[f'Group{i+1}_Delta'] = deltas[i]
        time_diffs_features[f'Group{i+1}_Delta'] = deltas_features[i]
    # Save the DataFrame to CSV
    time_diffs.to_csv('dts.csv', index=False)
    time_diffs_features.to_csv('dts_features.csv', index=False)
    return time_diffs



def plot_data(data, dts, start_index, end_index, value_index, ilist=[0,1,2,3]):
    """
    Plots selected data from a specified range and column index for each group, and plots the time differences.

    Args:
    data (DataFrame): The data to plot, expected to have 12 columns.
    dts (DataFrame): The data object containing time differences to plot.
    start_index (int): The starting index of the range of data points to plot.
    end_index (int): The ending index of the range of data points to plot.
    value_index (int): The index of the value to plot in each group (0, 1, or 2).
    ilist(list): list of indexes, for operating over a data subset
    """
    lil = len(ilist)
    #
    if value_index < 0 or value_index > 2:
        raise ValueError("value_index must be 0, 1, or 2")
    fig, axs = plt.subplots(lil+1, 1, figsize=(16, 10))  # Changed to 5 subplots to accommodate the dts plot
    for i in range(lil):
        i_i = ilist[i]
        col_index = i_i * 3 + value_index
        axs[i].plot(data.iloc[start_index:end_index, col_index])
        axs[i].set_title(f'CHANNEL{i_i+1}: {CH_NS[value_index]}')
        axs[i].set_xlabel('Index')
        axs[i].set_ylabel('Value')
    # Plotting the time differences data
    axs[lil].plot(dts.iloc[start_index:end_index, ilist])
    axs[lil].set_title('Time Between Pulses')
    axs[lil].set_xlabel('Index')
    axs[lil].set_ylabel('Time Difference (s)')
    plt.tight_layout()
    plt.show()



# //*-*-
# //*-*-
#dat0 = read_csv_data('D:/SK/PY/entrainment/T3/T3_4CH.csv')
dat0 = read_csv_data('D:/SK/PY/entrainment/T10/T102CH.csv')

#plot_data(dat0, 0, 3000, 0)
dts = estimate_time_differences(dat0, 100, 100, 0)
plot_data(dat0, dts,  0, 30000, 0)




import pandas as pd
from sklearn.cluster import KMeans

def train_kmeans_model(file_path):
    """
    Reads a CSV file and trains a KMeans clustering model with 6 clusters.

    Args:
    file_path (str): The path to the CSV file containing the data.

    Returns:
    KMeans: The trained KMeans model.
    """
    # Read the CSV file
    data = pd.read_csv(file_path)
    
    # Check if data has the expected 4 features
    if data.shape[1] != 4:
        raise ValueError("The input CSV file must have exactly 4 columns representing features.")
    
    # Initialize and train the KMeans model
    kmeans = KMeans(n_clusters=6, random_state=0)
    kmeans.fit(data)
    
    return kmeans



    def classify_and_save_clusters(file_path, model):
        """
        Classifies the instances in the CSV file using the provided KMeans model and saves the data with an additional
        column for the cluster number to a new file called 'clustered.csv'.

        Args:
        file_path (str): The path to the CSV file containing the data.
        model (KMeans): The trained KMeans model.
        """
        # Read the data from the file
        data = pd.read_csv(file_path)
        
        # Check if data has the expected 4 features
        if data.shape[1] != 4:
            raise ValueError("The input CSV file must have exactly 4 columns representing features.")
        
        # Predict the clusters for each instance in the data
        clusters = model.predict(data)
        
        # Add the cluster labels to the data
        data['Cluster'] = clusters
        
        # Save the new DataFrame with cluster labels to a new CSV file
        data.to_csv('clustered.csv', index=False)
        
        print("Data with cluster labels has been saved to 'clustered.csv'.")

    # Example usage:
    # kmeans_model = train_kmeans_model('path_to_your_data.csv')
    # classify_and_save_clusters('path_to_your_data.csv', kmeans_model)


