# main.py
"""
Real-time Heart Rate Variability Entrainment Analysis
with Improved Pan-Tompkins QRS Detection Algorithm
Main module - integrates processing, networking, and visualization

Modified to analyze 6 subjects organized in 3 pairs
Added data recording functionality via record_data.py
Modified to handle new sensor format sending beat detected and raw ECG directly
"""
# main.py - begin with config import
import config  # Import centralized configuration first
from network import OSCHandler
from graphs import EntrainmentVisualizerQt
from record_data import ECGDataRecorder
import time
import pyqtgraph as pg
import argparse
import logging
import sys
from PyQt5 import QtCore, QtWidgets, QtGui

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set PyQtGraph preferences
pg.setConfigOption('background', 'k')  # Black background
pg.setConfigOption('foreground', 'w')  # White foreground
pg.setConfigOptions(antialias=True)    # Enable antialiasing for prettier plots

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='HRV Entrainment Analysis System')
    parser.add_argument('--record', action='store_true', 
                        help='Enable data recording at startup')
    parser.add_argument('--visualize', action='store_true', default=True,
                        help='Enable visualization (default: True)')
    parser.add_argument('--ip', type=str, default=config.OSC_IP_ADDRESS,
                        help=f'OSC server IP address (default: {config.OSC_IP_ADDRESS})')
    parser.add_argument('--port', type=int, default=config.OSC_PORT,
                        help=f'OSC server port (default: {config.OSC_PORT})')
    parser.add_argument('--sample-rate', type=int, default=config.SAMPLE_RATE,
                        help=f'ECG sample rate in Hz (default: {config.SAMPLE_RATE})')
    
    return parser.parse_args()

def update_config_from_args(args):
    """Update configuration based on command line arguments"""
    if args.sample_rate != config.SAMPLE_RATE:
        # Update the sample rate in the config module
        config.SAMPLE_RATE = args.sample_rate
        
        # Recalculate all derived parameters that depend on sample rate
        config.QRS_WINDOW_SIZE = config.seconds_to_samples(2.5)
        config.HRV_ANALYSIS_WINDOW = config.seconds_to_samples(config.HRV_ANALYSIS_WINDOW_SECONDS)
        config.RAW_ECG_BUFFER_SIZE = config.seconds_to_samples(50)
        
        logger.info(f"Sample rate updated to {args.sample_rate} Hz")
        logger.info(f"Recalculated parameters: {config.parameter_summary()}")

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Update configuration if sample rate was changed
    if args.sample_rate != config.SAMPLE_RATE:
        update_config_from_args(args)
    
    # Print configuration for confirmation
    print("====== HRV Entrainment Analysis Configuration ======")
    print(f"Network: {args.ip}:{args.port}")
    print(f"Channels: {config.OSC_ADDRESSES}")
    print(f"Subject Pairs: {config.SUBJECT_PAIRS}")
    print(f"Sample rate: {config.SAMPLE_RATE} Hz")
    print(f"Display range: {config.HRV_DISPLAY_RANGE}s, History: {config.HRV_HISTORY_DURATION}s")
    print(f"Debug mode: {'Enabled' if config.DEBUG_MODE else 'Disabled'}")
    print(f"Recording: {'Enabled' if args.record else 'Disabled'}")
    print(f"Recording format: Beat detected (bool), Raw ECG (int), Timestamp, HRV")  # Updated format info
    print(f"Visualization: {'Enabled' if args.visualize else 'Disabled'}")
    print(f"Added feature: Entrainment Evolution Over Time")
    print("==================================================")
    
    # Create OSC handler with the updated configuration
    osc_handler = OSCHandler(ip=args.ip, port=args.port, 
                             sample_rate=config.SAMPLE_RATE,
                             subject_pairs=config.SUBJECT_PAIRS)
    
    # Create data recorder
    data_recorder = ECGDataRecorder(channels=config.OSC_ADDRESSES)
    data_recorder.connect_to_osc_handler(osc_handler)
    
    # Start recording if enabled via command line
    if args.record:
        data_recorder.start_recording()
    
    # Start OSC handler
    osc_handler.start()
    
    try:
        # Set up visualization if enabled
        if args.visualize:
            # Create and configure visualizer
            visualizer = EntrainmentVisualizerQt(osc_handler, subject_pairs=config.SUBJECT_PAIRS)
            
            # Add recording controls to the visualizer
            visualizer.add_recording_controls(data_recorder)
            
            print(f"Listening for OSC messages on {args.ip}:{args.port}")
            print("Press Ctrl+C to exit.")
            print("User controls:")
            print("  +/- : Increase/decrease HRV time range")
            print("  1-3 : Select subject pair (1-3) for detailed view")
            print("  R   : Toggle recording on/off")
            print("Recording Controls:")
            print("  R key         : Toggle recording on/off")
            print("  Record button : Visible at the bottom of the window")
            print("  Status        : Displayed at the top of correlation plot")
            print("Expected OSC message format:")
            print("  First value: Beat detected (boolean)")
            print("  Second value: Raw ECG value (integer)")
            
            # Start visualization
            visualizer.start()
        else:
            # If visualization is disabled, just keep the main thread alive
            print("Running in headless mode (no visualization)")
            print(f"Listening for OSC messages on {args.ip}:{args.port}")
            print("Expected OSC message format:")
            print("  First value: Beat detected (boolean)")
            print("  Second value: Raw ECG value (integer)")
            print("Press Ctrl+C to exit")
            
            # Keep program running until Ctrl+C
            while True:
                time.sleep(1)
                
                # Print recording status every 10 seconds
                if data_recorder.is_recording() and int(time.time()) % 10 == 0:
                    status = data_recorder.get_recording_status()
                    if isinstance(status, dict):
                        print(f"Recording time: {status['duration']:.1f}s, Total samples: {status['total_samples']}")
                    else:
                        print("Recording active")
        
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        # Ensure recording is stopped
        if data_recorder.is_recording():
            data_recorder.stop_recording()
        
        # Disconnect data recorder from OSC handler
        data_recorder.disconnect_from_osc_handler(osc_handler)
        
        # Stop OSC handler
        osc_handler.stop()

if __name__ == "__main__":
    main()
