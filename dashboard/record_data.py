# record_data.py
"""
Real-time Heart Rate Variability Entrainment Analysis
Data Recording Module - handles saving ECG, filtered data, and HRV to files

Designed to work with the OSCHandler from network.py
Modified to record only beat detected, raw ECG, timestamp, and HRV
"""
import os
import time
import logging
from datetime import datetime
import config  # Import centralized configuration

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ECGDataRecorder:
    """Records ECG data to files with simplified format (beat, raw ECG, timestamp, HRV)"""
    
    def __init__(self, base_path=config.BASE_PATH, base_folder_name=config.BASE_FOLDER_NAME, 
                 buffer_size=config.RECORDING_BUFFER_SIZE, channels=None):
        """Initialize the data recorder
        
        Args:
            base_path: Base directory for recordings
            base_folder_name: Base name for recording folders
            buffer_size: Number of samples to buffer before writing to file
            channels: List of channel names to record (e.g., ["/c1", "/c2", ...])
        """
        self.base_path = base_path
        self.base_folder_name = base_folder_name
        self.buffer_size = buffer_size
        self.channels = channels or []
        
        # Initialize data structures
        self.recording_enabled = False
        self.recording_buffers = {}
        self.file_handles = {}
        self.sample_counters = {}
        self.folder_path = None
        self.start_time = None
        
        # Status
        logger.info(f"ECGDataRecorder initialized (idle)")
        
    def _get_next_folder_name(self):
        """Create a new uniquely named folder for this recording session"""
        # Create a timestamp-based folder name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{self.base_folder_name}{timestamp}"
        folder_path = os.path.join(self.base_path, folder_name)
        
        # Create the directory if it doesn't exist
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            logger.info(f"Created recording directory: {folder_path}")
        
        return folder_path
    
    def start_recording(self, channels=None):
        """Start or resume recording data
        
        Args:
            channels: Optional list of channels to record (overwrites existing list)
        """
        if channels is not None:
            self.channels = channels
        
        if not self.recording_enabled:
            self.recording_enabled = True
            self.start_time = time.time()
            
            # Create a new folder for this recording session
            self.folder_path = self._get_next_folder_name()
            
            # Initialize buffers and files for each channel
            for channel in self.channels:
                # Extract channel number from address (e.g., "/c1" -> "1")
                channel_num = channel[2:]
                
                # Initialize recording buffer
                self.recording_buffers[channel] = []
                
                # Initialize sample counter
                self.sample_counters[channel] = 0
                
                # Create and open file for writing
                file_path = os.path.join(self.folder_path, f"ECG_c{channel_num}.txt")
                self.file_handles[channel] = open(file_path, 'w+')
                
                # Write header with only the specified columns
                # Beat, Raw ECG, Timestamp, HRV
                self.file_handles[channel].write("Beat\tRaw_ECG\tTimestamp\tHRV\n")
                logger.info(f"Opened recording file for {channel}: {file_path}")
            
            # Create an info file with recording details
            self._write_info_file()
            
            logger.info(f"Recording started with {len(self.channels)} channels")
            return True
        
        return False
    
    def _write_info_file(self):
        """Write recording information to a metadata file"""
        info_path = os.path.join(self.folder_path, "recording_info.txt")
        
        with open(info_path, 'w') as f:
            f.write(f"Recording started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Channels: {', '.join(self.channels)}\n")
            f.write(f"Buffer size: {self.buffer_size}\n")
            f.write(f"Format: Tab-separated values (TSV)\n\n")
            f.write("Columns:\n")
            f.write("1. Beat - Boolean indicating beat detection (1=detected, 0=not detected)\n")
            f.write("2. Raw_ECG - Raw integer ECG values from the sensor\n")
            f.write("3. Timestamp - Unix epoch time in seconds\n")
            f.write("4. HRV - Heart Rate Variability calculated using SDNN method\n")
            
            # Add more relevant information here as needed
            f.write("\nNotes:\n")
            f.write("- Beat values are boolean (1=detected, 0=not detected)\n")
            f.write("- Raw ECG values are integers direct from the sensor\n")
            f.write("- Timestamps are in Unix epoch time (seconds since Jan 1, 1970)\n")
            f.write("- HRV values are calculated using SDNN method\n")
        
        logger.info(f"Recording information saved to {info_path}")
    
    def stop_recording(self):
        """Stop recording data and close files"""
        if self.recording_enabled:
            self.recording_enabled = False
            
            # Flush all buffers
            self._flush_all_buffers()
            
            # Close all files
            for channel, file_handle in self.file_handles.items():
                if file_handle and not file_handle.closed:
                    file_handle.close()
                    logger.info(f"Closed recording file for {channel}")
            
            # Clear file handles
            self.file_handles = {}
            
            # Update info file with end time
            if self.folder_path:
                info_path = os.path.join(self.folder_path, "recording_info.txt")
                if os.path.exists(info_path):
                    with open(info_path, 'a') as f:
                        duration = time.time() - self.start_time if self.start_time else 0
                        f.write(f"\nRecording ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"Duration: {duration:.2f} seconds\n")
                        
                        # Add sample counts per channel
                        f.write("\nSample counts:\n")
                        for channel, count in self.sample_counters.items():
                            f.write(f"- {channel}: {count} samples\n")
            
            logger.info(f"Recording stopped after {sum(self.sample_counters.values())} total samples")
            return True
        
        return False
    
    def _flush_all_buffers(self):
        """Flush all recording buffers to disk"""
        for channel, buffer in self.recording_buffers.items():
            if buffer and channel in self.file_handles:
                file_handle = self.file_handles[channel]
                if file_handle and not file_handle.closed:
                    file_handle.writelines(buffer)
                    logger.debug(f"Flushed {len(buffer)} samples for {channel}")
            
            # Clear buffer
            self.recording_buffers[channel] = []
    
    def is_recording(self):
        """Check if recording is currently active"""
        return self.recording_enabled
    
    def get_recording_status(self):
        """Get the current recording status"""
        if not self.recording_enabled:
            return "Inactive"
        
        # Calculate total samples and time
        total_samples = sum(self.sample_counters.values())
        duration = time.time() - self.start_time if self.start_time else 0
        
        return {
            "status": "Active",
            "duration": duration,
            "total_samples": total_samples,
            "folder": self.folder_path,
            "channels": {channel: count for channel, count in self.sample_counters.items()}
        }
    
    # ===== Methods for connecting to OSCHandler =====
    
    def on_data(self, channel, ecg_value, filtered_value, hrv_value, timestamp, original_args):
        """Callback for receiving data from OSCHandler
        
        This method is called by OSCHandler when new data is available.
        
        Modified to handle the new format where sensors send:
        - beat detected (boolean) 
        - raw ECG data (integer)
        """
        if self.recording_enabled and channel in self.channels:
            try:
                # Format timestamp as integer
                timestamp_int = int(timestamp)
                
                # Extract beat detection status from original_args
                # The first value is now a boolean for beat detection
                beat_detected = 1 if original_args[0] else 0
                
                # The second value is the raw ECG value (integer)
                raw_ecg = int(original_args[1]) if len(original_args) > 1 else int(ecg_value)
                
                # Format line with only the columns we want in the specific order:
                # Beat, Raw_ECG, Timestamp, HRV
                line = f"{beat_detected}\t{raw_ecg}\t{timestamp_int}\t{hrv_value:.6f}\n"
                
                # Add to buffer
                self.recording_buffers[channel].append(line)
                self.sample_counters[channel] += 1
                
                # Flush buffer if it's full
                if len(self.recording_buffers[channel]) >= self.buffer_size:
                    if channel in self.file_handles:
                        self.file_handles[channel].writelines(self.recording_buffers[channel])
                        self.recording_buffers[channel] = []
                        
                        # Log progress occasionally
                        if self.sample_counters[channel] % 1000 == 0:
                            logger.info(f"Recorded {self.sample_counters[channel]} samples for {channel}")
                
            except Exception as e:
                logger.error(f"Error recording data for {channel}: {e}")
    
    def on_shutdown(self):
        """Callback for OSCHandler shutdown
        
        This method is called by OSCHandler when it's shutting down.
        """
        if self.recording_enabled:
            logger.info("OSCHandler is shutting down, stopping recording...")
            self.stop_recording()
    
    def connect_to_osc_handler(self, osc_handler):
        """Connect this recorder to an OSCHandler instance
        
        Args:
            osc_handler: Instance of OSCHandler from network.py
        """
        if hasattr(osc_handler, 'add_data_listener'):
            osc_handler.add_data_listener(self)
            
            # Automatically set channels based on OSC handler if none specified
            if not self.channels and hasattr(osc_handler, 'osc_addresses'):
                self.channels = osc_handler.osc_addresses
                logger.info(f"Configured channels from OSCHandler: {self.channels}")
            
            return True
        
        logger.error("Failed to connect: The provided object is not a valid OSCHandler")
        return False
    
    def disconnect_from_osc_handler(self, osc_handler):
        """Disconnect this recorder from an OSCHandler instance
        
        Args:
            osc_handler: Instance of OSCHandler from network.py
        """
        if hasattr(osc_handler, 'remove_data_listener'):
            osc_handler.remove_data_listener(self)
            return True
        
        return False
