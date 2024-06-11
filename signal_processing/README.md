## signal_processing

python code to process the ECG signal for exploratory data analysis, peak detection, Heart Rate Variability and entrainment analysis.

- [data](signal_processing/data): raw data that was recorded using the custom ESP32 devices.
- [hrv_analysis.ipynb](signal_processing/hrv_analysis.ipynb): jupyter notebook for Heart Rate Variability (HRV) analysis.
- [ml_models](signal_processing/ml_models): trained k means models used to charachterize stages of entrainment coherence.
- [peak_detection.ipynb](signal_processing/peak_detection.ipynb): jupyter notebook for testing different approaches to heart beat (peak) detection in the ECG data. this resulted in the real time heart beat detection algorithm programmed to run on the microcontrollers in real time.
- [plot_serial_data.py](signal_processing/plot_serial_data.py): Python script for plotting serial data from ECG recordings.
- [sync_EDA.ipynb](signal_processing/sync_EDA.ipynb): jupyter notebook for analyzing entrainment coherence in ECG recordings.
 --- 
![image](https://github.com/interspecifics/entrainment/assets/12953522/557d8259-2782-46e6-9148-c97ef8ba5a2b)
