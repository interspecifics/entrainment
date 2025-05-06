import socket
import threading
import queue
import time
import numpy as np
from datetime import datetime
import json
import os
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from collections import deque
import torch
import torch.nn as nn
from pythonosc import udp_client
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import pandas as pd
from scipy import signal
from ml_engine import MLEngine, EntrainmentScore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ecg_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ECGServer')

@dataclass
class DeviceConfig:
    """Configuration for each ECG device"""
    device_id: int
    ip: str
    port: int
    sampling_rate: int = 500
    buffer_size: int = 1000
    sync_interval: float = 1.0
    clock_offset: float = 0.0
    jitter: float = 0.0
    last_sync: float = 0.0

class JitterBuffer:
    """Handles jitter and synchronization for each device"""
    def __init__(self, buffer_size: int = 1000):
        self.buffer = deque(maxlen=buffer_size)
        self.last_timestamp = 0
        self.clock_offset = 0
        self.jitter = 0
        self.lock = threading.Lock()
        self.sync_history = deque(maxlen=100)  # Store sync history
        self.clock_drift = 0
        self.last_sync_time = 0
    
    def add_sample(self, sample: float, timestamp: float):
        with self.lock:
            adjusted_time = timestamp + self.clock_offset
            self.buffer.append((adjusted_time, sample))
            self._update_jitter(timestamp)
    
    def get_samples(self, start_time: float, end_time: float) -> List[float]:
        with self.lock:
            return [s for t, s in self.buffer if start_time <= t <= end_time]
    
    def _update_jitter(self, timestamp: float):
        if self.last_timestamp:
            delay = timestamp - self.last_timestamp
            self.jitter = 0.9 * self.jitter + 0.1 * abs(delay - (1/500))  # Assuming 500Hz
        self.last_timestamp = timestamp
    
    def update_clock_offset(self, offset: float, server_time: float):
        with self.lock:
            if self.last_sync_time:
                # Calculate clock drift
                time_diff = server_time - self.last_sync_time
                self.clock_drift = (offset - self.clock_offset) / time_diff
            self.clock_offset = offset
            self.last_sync_time = server_time
            self.sync_history.append((server_time, offset))

class MLPredictor(nn.Module):
    """Neural network for ECG signal prediction"""
    def __init__(self, input_size: int = 10, hidden_size: int = 32):
        super(MLPredictor, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)
    
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        return self.fc(lstm_out[:, -1, :])

class ECGServer:
    def __init__(self, host: str = '0.0.0.0', port: int = 8000):
        self.host = host
        self.port = port
        self.devices: Dict[int, DeviceConfig] = {}
        self.jitter_buffers: Dict[int, JitterBuffer] = {}
        self.sample_queues: Dict[int, queue.Queue] = {}
        self.running = False
        self.master_time = time.time()
        self.sync_interval = 1.0  # Sync every second
        
        # Initialize ML model
        self.model = MLPredictor()
        self.model.load_state_dict(torch.load('ecg_model.pth')) if os.path.exists('ecg_model.pth') else None
        self.model.eval()
        
        # Initialize ML engine
        self.ml_engine = MLEngine()
        
        # Initialize visualization
        self.setup_visualization()
        
        # Initialize OSC clients for Max/MSP and TouchDesigner
        self.osc_clients = {
            'max': udp_client.SimpleUDPClient('127.0.0.1', 8001),
            'touchdesigner': udp_client.SimpleUDPClient('127.0.0.1', 8002)
        }
    
    def setup_visualization(self):
        """Final design: legends close to plots, entrainment circular plot in middle row right, ML/Entrainment status in bottom left."""
        import matplotlib as mpl
        plt.rcParams.update({'font.size': 12})
        self.fig = plt.figure(figsize=(52, 12))  # Further increased width for all plots
        gs = self.fig.add_gridspec(3, 3, hspace=0.38, wspace=0.32)

        # Top row
        self.ax_ecg = self.fig.add_subplot(gs[0, 0])
        self.ax_ecg.set_title('ECG Signals', fontsize=14, fontweight='bold')
        self.ax_ecg.set_ylabel('Amplitude')
        self.ax_ecg.grid(True, linestyle='--', alpha=0.5)

        self.ax_hr = self.fig.add_subplot(gs[0, 1])
        self.ax_hr.set_title('Heart Rate', fontsize=14, fontweight='bold')
        self.ax_hr.set_ylabel('BPM')
        self.ax_hr.grid(True, linestyle='--', alpha=0.5)

        self.ax_pred = self.fig.add_subplot(gs[0, 2])
        self.ax_pred.set_title('ML Predictions vs Actual', fontsize=14, fontweight='bold')
        self.ax_pred.set_xlabel('Sample Index')
        self.ax_pred.set_ylabel('Amplitude')
        self.ax_pred.grid(True, linestyle='--', alpha=0.5)

        # Middle row
        self.ax_offset = self.fig.add_subplot(gs[1, 0])
        self.ax_offset.set_title('Clock Offsets', fontsize=12)
        self.ax_offset.set_ylabel('Offset (s)')
        self.ax_offset.grid(True, linestyle='--', alpha=0.5)

        self.ax_jitter = self.fig.add_subplot(gs[1, 1])
        self.ax_jitter.set_title('Jitter', fontsize=12)
        self.ax_jitter.set_ylabel('Jitter (s)')
        self.ax_jitter.grid(True, linestyle='--', alpha=0.5)

        self.ax_circular = self.fig.add_subplot(gs[1, 2], polar=True)
        self.ax_circular.set_title('Entrainment Circular Plot', fontsize=14, fontweight='bold', pad=20)
        self.ax_circular.set_yticklabels([])
        self.ax_circular.set_xticklabels([])
        self.ax_circular.set_ylim(0, 1)
        self.ax_circular.grid(True, linestyle='--', alpha=0.5)

        # Bottom row
        self.ax_status = self.fig.add_subplot(gs[2, 0])
        self.ax_status.set_title('ML/Entrainment Status', fontsize=12, color='black')
        self.ax_status.axis('on')
        self.ax_status.set_xticks([])
        self.ax_status.set_yticks([])
        for spine in self.ax_status.spines.values():
            spine.set_edgecolor('black')
            spine.set_linewidth(2)
        # Optionally, leave gs[2,1] and gs[2,2] empty for now
        self.ax_empty1 = self.fig.add_subplot(gs[2, 1])
        self.ax_empty1.axis('off')
        self.ax_empty2 = self.fig.add_subplot(gs[2, 2])
        self.ax_empty2.axis('off')

        # Color palette
        colors = ['r', 'g', 'b', 'y', 'm']
        self.device_colors = colors
        self.lines = {}
        self.hr_lines = {}
        self.offset_lines = {}
        self.jitter_lines = {}
        self.prediction_lines = {}
        self.actual_lines = {}
        self.circ_points = {}

        for i in range(5):
            self.lines[i], = self.ax_ecg.plot([], [], color=colors[i], label=f'Device {i+1}')
            self.hr_lines[i], = self.ax_hr.plot([], [], color=colors[i], label=f'HR {i+1}')
            self.offset_lines[i], = self.ax_offset.plot([], [], color=colors[i], label=f'Offset {i+1}')
            self.jitter_lines[i], = self.ax_jitter.plot([], [], color=colors[i], label=f'Jitter {i+1}')
            self.prediction_lines[i], = self.ax_pred.plot([], [], color=colors[i], linestyle='--', label=f'Pred {i+1}')
            self.actual_lines[i], = self.ax_pred.plot([], [], color=colors[i], alpha=0.5, label=f'Actual {i+1}')
            self.circ_points[i] = self.ax_circular.plot([], [], 'o', color=colors[i], markersize=14, label=f'Device {i+1}')[0]

        # Place legends close to their boxes
        self.ax_ecg.legend(loc='upper right', fontsize=9, borderaxespad=0.5)
        self.ax_hr.legend(loc='upper right', fontsize=9, borderaxespad=0.5)
        self.ax_pred.legend(loc='upper right', fontsize=9, ncol=2, borderaxespad=0.5)
        self.ax_offset.legend(loc='upper right', fontsize=9, borderaxespad=0.5)
        self.ax_jitter.legend(loc='upper right', fontsize=9, borderaxespad=0.5)
        self.ax_circular.legend(loc='upper right', fontsize=9, borderaxespad=0.5)

        # Data storage
        self.ecg_data = {i: deque(maxlen=1000) for i in range(5)}
        self.hr_data = {i: deque(maxlen=100) for i in range(5)}
        self.times = {i: deque(maxlen=1000) for i in range(5)}
        self.offset_data = {i: deque(maxlen=100) for i in range(5)}
        self.jitter_data = {i: deque(maxlen=100) for i in range(5)}
        self.prediction_data = {i: deque(maxlen=1000) for i in range(5)}
        self.actual_data = {i: deque(maxlen=1000) for i in range(5)}
        self.ml_status = {
            'model_loaded': False,
            'prediction_confidence': {},
            'sync_detection': {},
            'last_update': time.time()
        }
        # Status/entrainment text
        self.status_text = self.ax_status.text(0.01, 0.99, '', ha='left', va='top', fontsize=12, family='monospace', color='black')

        # Use tight_layout to maximize space usage
        self.fig.tight_layout(rect=[0, 0, 1, 1], pad=1.0)
    
    def start(self):
        """Start the server"""
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))
        
        # Start processing threads
        self.processing_thread = threading.Thread(target=self._process_samples)
        self.processing_thread.start()
        
        # Start sync thread
        self.sync_thread = threading.Thread(target=self._sync_devices)
        self.sync_thread.start()
        
        # Start visualization
        self.ani = FuncAnimation(self.fig, self._update_plot, interval=50)
        plt.show()
        
        logger.info(f"Server started on {self.host}:{self.port}")
        
        try:
            while self.running:
                data, addr = self.socket.recvfrom(1024)
                self._handle_packet(data, addr)
        except KeyboardInterrupt:
            self.stop()
    
    def _sync_devices(self):
        """Synchronize all devices with master clock"""
        while self.running:
            current_time = time.time()
            for device_id, device in self.devices.items():
                try:
                    # Send sync message to device
                    sync_msg = {
                        'type': 'sync',
                        'server_time': current_time,
                        'device_id': device_id
                    }
                    self.socket.sendto(
                        json.dumps(sync_msg).encode(),
                        (device.ip, device.port)
                    )
                    
                    # Update device timing info
                    device.last_sync = current_time
                    device.clock_offset = self.jitter_buffers[device_id].clock_offset
                    device.jitter = self.jitter_buffers[device_id].jitter
                    
                    # Update visualization data
                    self.offset_data[device_id].append(device.clock_offset)
                    self.jitter_data[device_id].append(device.jitter)
                    
                except Exception as e:
                    logger.error(f"Error syncing device {device_id}: {e}")
            
            time.sleep(self.sync_interval)
    
    def _handle_packet(self, data: bytes, addr: tuple):
        """Handle incoming UDP packets"""
        try:
            packet = json.loads(data.decode())
            
            if packet.get('type') == 'sync_response':
                # Handle sync response
                device_id = packet['device_id']
                device_time = packet['device_time']
                server_time = packet['server_time']
                
                # Calculate clock offset
                current_time = time.time()
                round_trip_time = current_time - server_time
                clock_offset = (device_time + round_trip_time/2) - current_time
                
                if device_id in self.jitter_buffers:
                    self.jitter_buffers[device_id].update_clock_offset(clock_offset, current_time)
            
            else:
                # Handle regular data packet
                device_id = packet['device_id']
                timestamp = packet['timestamp']
                sample = packet['sample']
                
                if device_id not in self.devices:
                    self._register_device(device_id, addr[0], addr[1])
                
                self.sample_queues[device_id].put((timestamp, sample))
            
        except Exception as e:
            logger.error(f"Error handling packet: {e}")
    
    def _register_device(self, device_id: int, ip: str, port: int):
        """Register a new device"""
        self.devices[device_id] = DeviceConfig(device_id, ip, port)
        self.jitter_buffers[device_id] = JitterBuffer()
        self.sample_queues[device_id] = queue.Queue()
        logger.info(f"Registered device {device_id} at {ip}:{port}")
    
    def _process_samples(self):
        """Process samples from all devices"""
        while self.running:
            for device_id, queue in self.sample_queues.items():
                try:
                    while not queue.empty():
                        timestamp, sample = queue.get_nowait()
                        self._process_device_sample(device_id, timestamp, sample)
                except queue.Empty:
                    continue
            time.sleep(0.001)
    
    def _process_device_sample(self, device_id: int, timestamp: float, sample: float):
        """Process a single sample from a device"""
        # Add to jitter buffer
        self.jitter_buffers[device_id].add_sample(sample, timestamp)
        
        # Get recent samples for prediction
        recent_samples = self.jitter_buffers[device_id].get_samples(
            timestamp - 0.1, timestamp
        )
        
        if len(recent_samples) >= 10:
            # Prepare input for ML model
            input_data = np.array(recent_samples[-10:])
            
            # Make prediction using ML engine
            prediction = self.ml_engine.predict_signal(input_data)
            
            # Update visualization data
            self.ecg_data[device_id].append(sample)
            self.times[device_id].append(timestamp)
            self.prediction_data[device_id].append(prediction[0])
            self.actual_data[device_id].append(sample)
            
            # Update ML status
            self.ml_status['prediction_confidence'][device_id] = 1.0 - np.abs(prediction[0] - sample) / 1000.0
            
            # Calculate heart rate
            if len(self.ecg_data[device_id]) > 1:
                peaks = self._find_peaks(list(self.ecg_data[device_id]))
                if len(peaks) >= 2:
                    intervals = np.diff(peaks)
                    hr = 60 / (np.mean(intervals) / 500)  # Assuming 500Hz sampling
                    self.hr_data[device_id].append(hr)
            
            # Analyze entrainment if we have multiple devices
            if len(self.devices) > 1:
                signals = {
                    dev_id: np.array(list(self.ecg_data[dev_id]))
                    for dev_id in self.devices
                    if len(self.ecg_data[dev_id]) > 0
                }
                if len(signals) > 1:
                    entrainment_results = self.ml_engine.analyze_entrainment(signals)
                    self._update_entrainment_visualization(entrainment_results)
                    
                    # Update sync detection status
                    for (id1, id2), score in entrainment_results.items():
                        self.ml_status['sync_detection'][id1] = score.overall_score
                        self.ml_status['sync_detection'][id2] = score.overall_score
            
            # Update ML status
            self.ml_status['last_update'] = time.time()
            self._update_ml_status()
            
            # Send to Max/MSP and TouchDesigner
            self._send_to_clients(device_id, sample, prediction)
    
    def _find_peaks(self, signal: List[float], threshold: float = 0.5) -> List[int]:
        """Simple peak detection"""
        peaks = []
        for i in range(1, len(signal)-1):
            if signal[i] > threshold and signal[i] > signal[i-1] and signal[i] > signal[i+1]:
                peaks.append(i)
        return peaks
    
    def _send_to_clients(self, device_id: int, sample: float, prediction: float):
        """Send data to Max/MSP and TouchDesigner"""
        for client_name, client in self.osc_clients.items():
            try:
                client.send_message(f"/ecg/{device_id}/raw", sample)
                client.send_message(f"/ecg/{device_id}/prediction", prediction)
            except Exception as e:
                logger.error(f"Error sending to {client_name}: {e}")
    
    def _update_entrainment_visualization(self, entrainment_results):
        """Update the entrainment and ML status panel, and the circular plot."""
        import numpy as np
        text = "Entrainment Analysis:\n"
        phases = []
        radii = []
        device_ids = list(self.devices.keys())
        # Compute phase for each device (using Hilbert transform if enough data)
        for i, dev_id in enumerate(device_ids):
            signal = np.array(self.ecg_data[dev_id])
            if len(signal) > 20:
                analytic = np.angle(np.fft.hilbert(signal)) if hasattr(np.fft, 'hilbert') else np.angle(np.abs(signal))
                phase = analytic[-1]
                # Find entrainment score (use mean of overall_score for this device)
                entr_scores = [score.overall_score for (id1, id2), score in entrainment_results.items() if dev_id in (id1, id2)]
                entrainment = np.mean(entr_scores) if entr_scores else 0
                r = 1 - entrainment  # closer to center = more entrained
                phases.append(phase)
                radii.append(r)
                self.circ_points[dev_id].set_data([phase], [r])
            else:
                self.circ_points[dev_id].set_data([], [])
        # Optionally, plot the absolute center
        self.ax_circular.plot([0], [0], 'ko', markersize=10, label='Perfect Entrainment')
        # Update text panel as before
        for (id1, id2), score in entrainment_results.items():
            text += f"Devices {id1}-{id2}: PhaseSync={score.phase_sync:.2f}  Amp={score.amplitude_coupling:.2f}  Temp={score.temporal_alignment:.2f}  Score={score.overall_score:.2f}\n"
        text += "\nML Engine Status:\n"
        text += f"Models Loaded: {'Yes' if self.ml_engine.predictor is not None else 'No'}\n"
        for device_id in self.devices:
            if device_id in self.ml_status['prediction_confidence']:
                conf = self.ml_status['prediction_confidence'][device_id]
                text += f"Device {device_id}: PredConf={conf:.1%}"
                if device_id in self.ml_status['sync_detection']:
                    sync = self.ml_status['sync_detection'][device_id]
                    text += f"  Sync={sync:.1%}"
                text += "\n"
        elapsed = time.time() - self.ml_status['last_update']
        text += f"Last Update: {elapsed:.1f}s ago"
        self.status_text.set_text(text)
    
    def _update_ml_status(self):
        """Update ML engine status information"""
        status_text = "ML Engine Status:\n\n"
        
        # Model loading status
        status_text += f"Models Loaded: {'Yes' if self.ml_engine.predictor is not None else 'No'}\n"
        
        # Device-specific status
        for device_id in self.devices:
            if device_id in self.ml_status['prediction_confidence']:
                conf = self.ml_status['prediction_confidence'][device_id]
                status_text += f"\nDevice {device_id}:\n"
                status_text += f"  Prediction Confidence: {conf:.2%}\n"
                if device_id in self.ml_status['sync_detection']:
                    sync = self.ml_status['sync_detection'][device_id]
                    status_text += f"  Sync Detection: {sync:.2%}\n"
        
        # Last update time
        elapsed = time.time() - self.ml_status['last_update']
        status_text += f"\nLast Update: {elapsed:.1f}s ago"
        
        self.status_text.set_text(status_text)
    
    def _update_plot(self, frame):
        """Update the visualization"""
        for device_id in self.devices:
            if len(self.ecg_data[device_id]) > 0:
                self.lines[device_id].set_data(
                    list(range(len(self.ecg_data[device_id]))),
                    list(self.ecg_data[device_id])
                )
                if len(self.hr_data[device_id]) > 0:
                    self.hr_lines[device_id].set_data(
                        list(range(len(self.hr_data[device_id]))),
                        list(self.hr_data[device_id])
                    )
                if len(self.offset_data[device_id]) > 0:
                    self.offset_lines[device_id].set_data(
                        list(range(len(self.offset_data[device_id]))),
                        list(self.offset_data[device_id])
                    )
                if len(self.jitter_data[device_id]) > 0:
                    self.jitter_lines[device_id].set_data(
                        list(range(len(self.jitter_data[device_id]))),
                        list(self.jitter_data[device_id])
                    )
                if len(self.prediction_data[device_id]) > 0:
                    self.prediction_lines[device_id].set_data(
                        list(range(len(self.prediction_data[device_id]))),
                        list(self.prediction_data[device_id])
                    )
                    self.actual_lines[device_id].set_data(
                        list(range(len(self.actual_data[device_id]))),
                        list(self.actual_data[device_id])
                    )
        # Only show x-labels on bottom row
        plt.setp(self.ax_ecg.get_xticklabels(), visible=False)
        plt.setp(self.ax_hr.get_xticklabels(), visible=False)
        plt.setp(self.ax_offset.get_xticklabels(), visible=False)
        plt.setp(self.ax_jitter.get_xticklabels(), visible=False)
        # Autoscale
        for ax in [self.ax_ecg, self.ax_hr, self.ax_pred, self.ax_offset, self.ax_jitter]:
            ax.relim()
            ax.autoscale_view()
        return (list(self.lines.values()) +
                list(self.hr_lines.values()) +
                list(self.offset_lines.values()) +
                list(self.jitter_lines.values()) +
                list(self.prediction_lines.values()) +
                list(self.actual_lines.values()) +
                [self.status_text])

    def stop(self):
        """Cleanly stop the server and all resources"""
        self.running = False
        try:
            if hasattr(self, 'socket'):
                self.socket.close()
        except Exception:
            pass
        try:
            if hasattr(self, 'processing_thread') and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=1)
        except Exception:
            pass
        try:
            if hasattr(self, 'sync_thread') and self.sync_thread.is_alive():
                self.sync_thread.join(timeout=1)
        except Exception:
            pass
        try:
            plt.close(self.fig)
        except Exception:
            pass
        print('Server stopped cleanly.')

if __name__ == "__main__":
    server = ECGServer()
    server.start() 