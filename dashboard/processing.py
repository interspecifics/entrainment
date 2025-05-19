# processing.py
"""
Real-time Heart Rate Variability Entrainment Analysis
Processing module - handles signal processing and calculations

Modified to analyze 6 subjects organized in 3 pairs
"""
import numpy as np
import scipy.signal as signal
import time
import collections
from typing import List, Dict, Deque, Tuple
import config  # Import centralized configuration

# ============ Improved Pan-Tompkins QRS Detection Algorithm ============
class PanTompkinsQRS:
    """Improved Pan-Tompkins QRS detection algorithm"""
    
    def __init__(self, sample_rate=config.SAMPLE_RATE, window_size=config.QRS_WINDOW_SIZE):
        self.sample_rate = sample_rate
        self.window_size = window_size
        
        # Filter coefficients (use normalized frequencies from config)
        norm_freqs = config.get_normalized_filter_frequencies(config.QRS_FILTER_LOW, config.QRS_FILTER_HIGH)
        self.b_bp, self.a_bp = signal.butter(3, norm_freqs, btype='bandpass')
        
        # Buffer for incoming ECG data
        self.ecg_buffer = collections.deque(maxlen=self.window_size*2)
        self.filtered_buffer = collections.deque(maxlen=self.window_size*2)
        
        # Results
        self.r_peaks_indices = []  # Global indices
        self.r_peaks_values = []   # Corresponding amplitudes
        self.last_r_peak_idx = 0   # Last detected peak index
        self.rr_intervals = []     # RR intervals in seconds
        
        # Adaptive thresholds
        self.threshold = 0.0       # Detection threshold
        self.noise_level = 0.0     # Noise level estimate
        self.signal_level = 0.0    # Signal level estimate
        
        # Buffer index counter
        self.buffer_idx_counter = 0
        
        # Initialize with empty buffer
        for i in range(self.window_size):
            self.ecg_buffer.append(0)
            self.filtered_buffer.append(0)
    
    def update(self, new_sample):
        """Add new ECG sample and update QRS detection"""
        # Add new sample to buffer
        self.ecg_buffer.append(new_sample)
        self.buffer_idx_counter += 1
        
        # Only process if we have enough data
        if len(self.ecg_buffer) >= self.window_size:
            # Get the current window for processing
            ecg_window = np.array(list(self.ecg_buffer)[-self.window_size:])
            
            # Apply bandpass filter
            ecg_filtered = signal.filtfilt(self.b_bp, self.a_bp, ecg_window)
            
            # Add filtered sample to buffer
            self.filtered_buffer.append(ecg_filtered[-1])
            
            # Derivative (five-point derivative for better noise reduction)
            ecg_derivative = np.zeros_like(ecg_filtered)
            for i in range(2, len(ecg_filtered)-2):
                ecg_derivative[i] = (2*ecg_filtered[i+2] + ecg_filtered[i+1] - ecg_filtered[i-1] - 2*ecg_filtered[i-2]) / 8.0
            
            # Squaring
            ecg_squared = ecg_derivative ** 2
            
            # Moving window integration (using sample rate adjusted value)
            integration_window = config.ms_to_samples(config.QRS_INTEGRATION_WINDOW_MS)
            ecg_integrated = np.convolve(ecg_squared, np.ones(integration_window)/integration_window, mode='same')
            
            # Find potential peaks in integrated signal
            # Use height parameter to avoid detecting noise
            min_height = config.QRS_MIN_PEAK_PROMINENCE * np.max(ecg_integrated) if np.max(ecg_integrated) > 0 else config.QRS_MIN_PEAK_PROMINENCE
            peaks, _ = signal.find_peaks(ecg_integrated, height=min_height, 
                                        distance=config.ms_to_samples(config.QRS_MIN_PEAK_DISTANCE_MS))
            
            # Process detected peaks
            for peak_idx in peaks:
                # Get actual value from raw ECG at this position
                peak_value = ecg_window[peak_idx]
                
                # Calculate absolute global buffer index
                global_idx = self.buffer_idx_counter - self.window_size + peak_idx
                
                # Only accept if sufficiently far from the last detected peak
                min_samples_between_peaks = config.ms_to_samples(config.QRS_MIN_PEAK_DISTANCE_MS)
                
                if len(self.r_peaks_indices) == 0 or (global_idx - self.last_r_peak_idx) > min_samples_between_peaks:
                    # Update adaptive threshold
                    if self.signal_level == 0:  # First peak
                        self.signal_level = peak_value
                        self.threshold = 0.5 * peak_value
                    else:
                        # If peak is above threshold, it's a QRS complex
                        if peak_value > self.threshold:
                            # Add to results
                            self.r_peaks_indices.append(global_idx)
                            self.r_peaks_values.append(peak_value)
                            self.last_r_peak_idx = global_idx
                            
                            # Calculate RR interval if we have at least 2 peaks
                            if len(self.r_peaks_indices) > 1:
                                rr_interval = (self.r_peaks_indices[-1] - self.r_peaks_indices[-2]) / self.sample_rate
                                self.rr_intervals.append(rr_interval)
                            
                            # Update signal level (weighted average)
                            self.signal_level = 0.125 * peak_value + 0.875 * self.signal_level
                        else:
                            # Update noise level
                            self.noise_level = 0.125 * peak_value + 0.875 * self.noise_level
                        
                        # Update threshold based on signal and noise levels
                        self.threshold = self.noise_level + 0.25 * (self.signal_level - self.noise_level)
            
            return ecg_filtered[-1]
        
        return 0
    
    def get_latest_rr_intervals(self, n=20):
        """Get the n most recent RR intervals"""
        return self.rr_intervals[-n:] if len(self.rr_intervals) >= n else self.rr_intervals.copy()
    
    def get_hrv(self, window_size=20):
        """Calculate heart rate variability using SDNN method"""
        rr_intervals = self.get_latest_rr_intervals(window_size)
        if len(rr_intervals) >= 3:
            return np.std(rr_intervals)
        return 0


# ============ HRV Entrainment Analysis ============
class HRVEntrainmentAnalyzer:
    """Analyzes entrainment between two HRV signals"""
    
    def __init__(self, window_size=config.HRV_ANALYSIS_WINDOW, max_lag=config.MAX_CROSS_CORR_LAG, 
                 hrv_history_duration=config.HRV_HISTORY_DURATION,
                 corr_history_size=config.CORR_HISTORY_SIZE):
        self.window_size = window_size
        self.max_lag = max_lag
        self.hrv_history_duration = hrv_history_duration
        self.corr_history_size = corr_history_size
        
        # HRV data storage - buffer size based on configured history duration
        self.hrv_data = {}
        
        # Cross-correlation results
        self.lags = np.arange(-max_lag, max_lag + 1)
        self.cross_corr = np.zeros_like(self.lags, dtype=float)
        
        # Storage for correlation history over time
        self.corr_history = collections.deque(maxlen=self.corr_history_size)
        self.corr_timestamps = collections.deque(maxlen=self.corr_history_size)
        
        # Time tracking
        self.last_analysis_time = time.time()
        self.analysis_interval = 0.5  # Perform analysis every 0.5 seconds
        
    def register_channel(self, channel_name):
        """Register a new channel to track"""
        if channel_name not in self.hrv_data:
            # Calculate buffer size based on history duration and expected update rate
            # Assuming HRV is updated around 1-2 Hz, we need buffer for hrv_history_duration seconds
            buffer_size = self.hrv_history_duration * 2  # 2 samples per second × duration
            
            self.hrv_data[channel_name] = {
                'values': collections.deque(maxlen=buffer_size),
                'times': collections.deque(maxlen=buffer_size)
            }
    
    def update_hrv(self, channel_name, hrv_value):
        """Update HRV value for a channel"""
        self.register_channel(channel_name)
        
        current_time = time.time()
        self.hrv_data[channel_name]['values'].append(hrv_value)
        self.hrv_data[channel_name]['times'].append(current_time)
        
        # Check if it's time to perform analysis
        if current_time - self.last_analysis_time >= self.analysis_interval:
            self.analyze_entrainment()
            self.last_analysis_time = current_time
    
    def analyze_entrainment(self):
        """Analyze entrainment between the first two channels"""
        if len(self.hrv_data) < 2:
            return  # Need at least two channels
        
        # Get the first two channels
        channels = list(self.hrv_data.keys())
        if len(channels) < 2:
            return
            
        ch1, ch2 = channels[0], channels[1]
        
        # Get data
        hrv1_values = list(self.hrv_data[ch1]['values'])
        hrv2_values = list(self.hrv_data[ch2]['values'])
        
        # Need enough data for analysis
        if len(hrv1_values) < self.window_size or len(hrv2_values) < self.window_size:
            return
        
        # Get the most recent window of data
        hrv1 = np.array(hrv1_values[-self.window_size:])
        hrv2 = np.array(hrv2_values[-self.window_size:])
        
        # Remove mean (DC component)
        hrv1 = hrv1 - np.mean(hrv1)
        hrv2 = hrv2 - np.mean(hrv2)
        
        # Calculate cross-correlation
        cross_corr = signal.correlate(hrv1, hrv2, mode='full')
        
        # Normalize
        if np.max(np.abs(cross_corr)) > 0:
            cross_corr = cross_corr / np.max(np.abs(cross_corr))
        
        # Store result (truncate to max_lag)
        middle = len(cross_corr) // 2
        start = max(0, middle - self.max_lag)
        end = min(len(cross_corr), middle + self.max_lag + 1)
        
        if end > start:
            result = cross_corr[start:end]
            result_lags = np.arange(start - middle, end - middle)
            
            # Ensure lags and cross_corr are the same length
            min_len = min(len(result), len(self.lags))
            self.cross_corr = result[:min_len]
            self.lags = result_lags[:min_len]
            
            # Store in history
            self.corr_history.append(self.cross_corr.copy())
            self.corr_timestamps.append(time.time())
    
    def get_entrainment_results(self):
        """Get the latest entrainment analysis results"""
        return self.lags, self.cross_corr
    
    def get_correlation_history(self):
        """Get the history of correlation patterns over time"""
        return list(self.corr_timestamps), list(self.corr_history)
    
    def get_hrv_data(self):
        """Get all HRV data for visualization"""
        return self.hrv_data


# ============ Additional Helper Classes for Spectrogram-style Visualization ============
class EntrainmentHistoryManager:
    """Helper class to manage the correlation history data for visualization"""
    
    def __init__(self, max_history=config.CORR_HISTORY_SIZE, max_lag=config.MAX_CROSS_CORR_LAG):
        self.max_history = max_history
        self.max_lag = max_lag
        self.correlation_history = []
        self.timestamps = []
        
    def update(self, lags, cross_corr, timestamp=None):
        """Add a new correlation pattern to the history"""
        if timestamp is None:
            timestamp = time.time()
            
        # Add new correlation pattern to history
        self.correlation_history.append(cross_corr)
        self.timestamps.append(timestamp)
        
        # Limit history size
        if len(self.correlation_history) > self.max_history:
            self.correlation_history.pop(0)
            self.timestamps.pop(0)
            
    def get_correlation_matrix(self):
        """Get the correlation history as a 2D matrix for visualization"""
        if not self.correlation_history:
            return np.array([]), np.array([])
            
        # Create 2D matrix where each row is a correlation pattern
        correlation_matrix = np.array(self.correlation_history)
        time_values = np.array(self.timestamps)
        
        return time_values, correlation_matrix
