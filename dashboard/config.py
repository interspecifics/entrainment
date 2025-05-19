# config.py
"""
Centralized configuration for HRV Entrainment Analysis System
All modules should import parameters from here
"""
import os
import numpy as np

# ----- Network Settings -----
OSC_IP_ADDRESS = '0.0.0.0'  # Accept connections from any IP
OSC_PORT = 8001            # OSC server port
OSC_ADDRESSES = ["/c1", "/c2", "/c3", "/c4", "/c5", "/c6"]  # OSC channel addresses

# ----- Sampling and Analysis Settings -----
SAMPLE_RATE = 500          # ECG sampling rate in Hz

# ----- Derived Time-Based Parameters -----
# These are calculated based on SAMPLE_RATE to maintain consistent time values
def ms_to_samples(ms):
    """Convert milliseconds to samples"""
    return int((ms / 1000.0) * SAMPLE_RATE)

def seconds_to_samples(seconds):
    """Convert seconds to samples"""
    return int(seconds * SAMPLE_RATE)

# ----- Processing Parameters -----
# QRS detection parameters
QRS_WINDOW_SIZE = seconds_to_samples(2.5)  # Window size for QRS detection (2.5 seconds)
QRS_FILTER_LOW = 5.0        # Bandpass filter low cutoff (Hz)
QRS_FILTER_HIGH = 20.0      # Bandpass filter high cutoff (Hz)
QRS_INTEGRATION_WINDOW_MS = 150  # Integration window in milliseconds
QRS_MIN_PEAK_DISTANCE_MS = 200   # Minimum distance between peaks in milliseconds
QRS_MIN_PEAK_PROMINENCE = 0.1    # Minimum peak prominence

# HRV analysis parameters
HRV_ANALYSIS_WINDOW_SECONDS = 1.8  # Window size for entrainment analysis (seconds)
HRV_ANALYSIS_WINDOW = seconds_to_samples(HRV_ANALYSIS_WINDOW_SECONDS)
MAX_CROSS_CORR_LAG = 30      # Maximum lag for cross-correlation analysis
HRV_HISTORY_DURATION = 2000  # Maximum history to store for HRV data (seconds)
CORR_HISTORY_SIZE = 100      # Number of correlation patterns to store for visualization

# ----- Buffer Sizes -----
RAW_ECG_BUFFER_SIZE = seconds_to_samples(50)  # 50 seconds of ECG data
RECORDING_BUFFER_SIZE = 100  # Number of samples to buffer before writing to file

# ----- Visualization Settings -----
HRV_DISPLAY_RANGE = 30       # Time range to display in HRV plot (seconds)
ECG_DISPLAY_SECONDS = 10     # Number of seconds to display in ECG plot
WINDOW_SIZE = 1800           # Window width in pixels
WINDOW_HEIGHT = 900          # Window height in pixels

# ----- Visual Settings -----
ECG_C1_COLOR = (255, 50, 50)   # Red
ECG_C2_COLOR = (50, 200, 50)   # Green
ECG_C3_COLOR = (0, 128, 255)  # Blue
ECG_C4_COLOR = (200, 200, 50)  # Yellow
ECG_C5_COLOR = (200, 50, 200)  # Purple
ECG_C6_COLOR = (50, 200, 200)  # Cyan
RR_INTERVAL_COLOR = (50, 200, 50)  # Green
CROSS_CORR_COLOR = (200, 200, 50)  # Yellow
R_PEAK_COLOR = (255, 0, 0)     # Red

# ----- Recording Settings -----
BASE_PATH = "data"               # Base directory for recordings
BASE_FOLDER_NAME = "ECG_HRV_Recording_"  # Base name for recording folders

# ----- Subject Pairs for Entrainment Analysis -----
SUBJECT_PAIRS = [
    ("/c1", "/c2"),  # Pair 1
    ("/c3", "/c4"),  # Pair 2
    ("/c5", "/c6"),  # Pair 3
]

# ----- Debug Settings -----
DEBUG_MODE = True            # Enable debug messages

# ----- Helper Functions -----
def get_normalized_filter_frequencies(low_freq, high_freq):
    """
    Convert filter frequencies to normalized values required by scipy.signal
    
    Args:
        low_freq: Low cutoff frequency in Hz
        high_freq: High cutoff frequency in Hz
        
    Returns:
        Tuple of normalized frequencies for scipy.signal butter filter
    """
    return [low_freq/(SAMPLE_RATE/2), high_freq/(SAMPLE_RATE/2)]

def parameter_summary():
    """Return a string summarizing the current configuration"""
    summary = "===== HRV Entrainment Analysis Configuration =====\n"
    summary += f"Sample rate: {SAMPLE_RATE} Hz\n"
    summary += f"QRS window size: {QRS_WINDOW_SIZE} samples ({QRS_WINDOW_SIZE/SAMPLE_RATE:.2f} seconds)\n"
    summary += f"HRV analysis window: {HRV_ANALYSIS_WINDOW} samples ({HRV_ANALYSIS_WINDOW/SAMPLE_RATE:.2f} seconds)\n"
    summary += f"Raw ECG buffer: {RAW_ECG_BUFFER_SIZE} samples ({RAW_ECG_BUFFER_SIZE/SAMPLE_RATE:.2f} seconds)\n"
    summary += f"QRS integration window: {ms_to_samples(QRS_INTEGRATION_WINDOW_MS)} samples ({QRS_INTEGRATION_WINDOW_MS} ms)\n"
    summary += f"Minimum peak distance: {ms_to_samples(QRS_MIN_PEAK_DISTANCE_MS)} samples ({QRS_MIN_PEAK_DISTANCE_MS} ms)\n"
    return summary
