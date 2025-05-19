# network.py
"""
Real-time Heart Rate Variability Entrainment Analysis
Network module - handles OSC and other communications related tasks

Modified to analyze 6 subjects organized in 3 pairs and support external data recorders
Modified to handle new sensor format sending beat detected and raw ECG directly
"""
import time
import collections
import threading
from pythonosc import dispatcher, osc_server
import numpy as np
import config  # Import centralized configuration

# Import processing classes after config import
from processing import PanTompkinsQRS, HRVEntrainmentAnalyzer

# ============ OSC Server for Real-time Data Reception ============
class OSCHandler:
    """Handles OSC messages and processes ECG data"""
    
    def __init__(self, ip=config.OSC_IP_ADDRESS, port=config.OSC_PORT, 
                 sample_rate=config.SAMPLE_RATE, 
                 osc_addresses=None, subject_pairs=None):
        self.ip = ip
        self.port = port
        self.sample_rate = sample_rate
        
        # Default OSC addresses if none provided
        self.osc_addresses = osc_addresses or config.OSC_ADDRESSES
        
        # Subject pairs for entrainment analysis
        self.subject_pairs = subject_pairs or config.SUBJECT_PAIRS
        
        # QRS detectors for each channel
        self.qrs_detectors = {}
        
        # HRV entrainment analyzer for each pair with configured history duration
        self.entrainment_analyzers = {}
        for pair_idx, (ch1, ch2) in enumerate(self.subject_pairs):
            self.entrainment_analyzers[pair_idx] = HRVEntrainmentAnalyzer(
                hrv_history_duration=config.HRV_HISTORY_DURATION
            )
        
        # Raw ECG data storage (for visualization)
        self.raw_data = {}
        self.raw_buffer_size = config.RAW_ECG_BUFFER_SIZE
        
        # External data listeners
        self.data_listeners = []
        
        # Set up OSC dispatcher
        self.dispatcher = dispatcher.Dispatcher()
        self.setup_dispatcher()
        
        # Initialize OSC server
        self.server = osc_server.ThreadingOSCUDPServer((self.ip, self.port), self.dispatcher)
        self.server_thread = None
        
        # Update rate tracking for debugging
        self.update_times = collections.deque(maxlen=100)
        self.last_update_time = time.time()
    
    def add_data_listener(self, listener):
        """Add an external data listener that will receive all processed data"""
        if listener not in self.data_listeners:
            self.data_listeners.append(listener)
            print(f"Added data listener: {listener}")
    
    def remove_data_listener(self, listener):
        """Remove a previously added data listener"""
        if listener in self.data_listeners:
            self.data_listeners.remove(listener)
            print(f"Removed data listener: {listener}")
    
    def setup_dispatcher(self):
        """Set up the OSC message dispatcher"""
        # Register handlers for each OSC address we're expecting
        for address in self.osc_addresses:
            self.dispatcher.map(address, self.ecg_handler)
            
            # Initialize raw data buffer
            self.raw_data[address] = collections.deque(maxlen=self.raw_buffer_size)
            
            # Initialize QRS detector
            self.qrs_detectors[address] = PanTompkinsQRS(sample_rate=self.sample_rate)
            
        # Register channels with entrainment analyzers
        for pair_idx, (ch1, ch2) in enumerate(self.subject_pairs):
            analyzer = self.entrainment_analyzers[pair_idx]
            analyzer.register_channel(ch1)
            analyzer.register_channel(ch2)
    
    def ecg_handler(self, address, *args):
        """Handle incoming ECG data from OSC
        
        Modified to handle new format where sensor sends:
        - args[0]: beat detected (boolean)
        - args[1]: raw ECG data (integer)
        """
        if args:
            try:
                # Extract data from the new format
                # First value is beat detected (boolean)
                beat_detected = bool(args[0]) if len(args) > 0 else False
                
                # Second value is raw ECG value (integer)
                ecg_value = int(args[1]) if len(args) > 1 else 0
                
                # Store raw data for visualization
                self.raw_data[address].append(ecg_value)
                
                # Process with QRS detector
                # Note: We still use our own QRS detector for HRV calculation,
                # but we use the sensor-detected beats for recording
                filtered_sample = self.qrs_detectors[address].update(ecg_value)
                
                # Calculate HRV
                hrv = self.qrs_detectors[address].get_hrv()
                
                # Update entrainment analyzers for each pair that includes this channel
                for pair_idx, (ch1, ch2) in enumerate(self.subject_pairs):
                    if address in (ch1, ch2):
                        self.entrainment_analyzers[pair_idx].update_hrv(address, hrv)
                
                # Track update rate for debugging
                current_time = time.time()
                self.update_times.append(current_time - self.last_update_time)
                self.last_update_time = current_time
                
                # Notify external data listeners
                for listener in self.data_listeners:
                    if hasattr(listener, 'on_data'):
                        listener.on_data(address, ecg_value, filtered_sample, hrv, int(current_time), args)
                
            except (ValueError, TypeError) as e:
                if config.DEBUG_MODE:
                    print(f"Error processing OSC data at {address}: {e}")
    
    def start(self):
        """Start the OSC server in a separate thread"""
        print(f"Starting OSC server on {self.ip}:{self.port}")
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
    
    def stop(self):
        """Stop the OSC server"""
        # Notify listeners we're shutting down
        for listener in self.data_listeners:
            if hasattr(listener, 'on_shutdown'):
                listener.on_shutdown()
                
        # Clear listeners
        self.data_listeners.clear()
        
        # Shut down server
        if self.server:
            self.server.shutdown()
            if self.server_thread:
                self.server_thread.join(timeout=1.0)
    
    def get_update_rate(self):
        """Get the current update rate in Hz for debugging"""
        if len(self.update_times) > 1:
            return 1.0 / np.mean(self.update_times)
        return 0

    def get_entrainment_analyzer(self, pair_idx=0):
        """Get the entrainment analyzer for a specific pair"""
        return self.entrainment_analyzers.get(pair_idx)
    
    def get_subject_pair(self, pair_idx=0):
        """Get the subject pair channels for a specific pair index"""
        if 0 <= pair_idx < len(self.subject_pairs):
            return self.subject_pairs[pair_idx]
        return None
