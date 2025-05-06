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
    last_message: float = 0.0
    message_count: int = 0
    error_count: int = 0
    signal_quality: float = 0.0
    is_connected: bool = False

class JitterBuffer:
    """Handles jitter and synchronization for each device"""
    def __init__(self, buffer_size: int = 1000):
        self.buffer = deque(maxlen=buffer_size)
        self.last_timestamp = 0
        self.clock_offset = 0
        self.jitter = 0
        self.lock = threading.Lock()
        self.sync_history = deque(maxlen=100)
        self.clock_drift = 0
        self.last_sync_time = 0
        self.message_gaps = deque(maxlen=100)
        self.last_message_time = 0
    
    def add_sample(self, sample: float, timestamp: float, signal_quality: float):
        with self.lock:
            adjusted_time = timestamp + self.clock_offset
            self.buffer.append((adjusted_time, sample, signal_quality))
            self._update_jitter(timestamp)
            self._update_message_gaps(timestamp)
    
    def get_samples(self, start_time: float, end_time: float) -> List[Tuple[float, float, float]]:
        with self.lock:
            return [(t, s, q) for t, s, q in self.buffer if start_time <= t <= end_time]
    
    def _update_jitter(self, timestamp: float):
        if self.last_timestamp:
            delay = timestamp - self.last_timestamp
            self.jitter = 0.9 * self.jitter + 0.1 * abs(delay - (1/500))
        self.last_timestamp = timestamp
    
    def _update_message_gaps(self, timestamp: float):
        if self.last_message_time:
            gap = timestamp - self.last_message_time
            self.message_gaps.append(gap)
        self.last_message_time = timestamp
    
    def get_message_gap_stats(self) -> Tuple[float, float]:
        if not self.message_gaps:
            return 0.0, 0.0
        return np.mean(self.message_gaps), np.std(self.message_gaps)

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
        self.sync_interval = 1.0
        self.max_message_gap = 0.1  # 100ms
        self.reconnect_timeout = 5.0  # 5 seconds
        
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

        # New device status box
        self.ax_device_status = self.fig.add_subplot(gs[2, 1])
        self.ax_device_status.set_title('Device Status', fontsize=12, color='black')
        self.ax_device_status.axis('on')
        self.ax_device_status.set_xticks([])
        self.ax_device_status.set_yticks([])
        for spine in self.ax_device_status.spines.values():
            spine.set_edgecolor('black')
            spine.set_linewidth(2)
        
        # Device status text
        self.device_status_text = self.ax_device_status.text(
            0.01, 0.99, '', 
            ha='left', va='top', 
            fontsize=10, 
            family='monospace',
            color='black',
            transform=self.ax_device_status.transAxes
        )

        # Leave the last cell empty for future use
        self.ax_empty = self.fig.add_subplot(gs[2, 2])
        self.ax_empty.axis('off')

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
    
    def _handle_packet(self, data: bytes, addr: tuple):
        """Handle incoming UDP packets with improved error handling"""
        try:
            packet = json.loads(data.decode())
            
            # Verify required fields
            required_fields = ['device_id', 'timestamp', 'raw_value', 'filtered_value', 
                             'signal_quality', 'is_beat', 'rr_interval', 'time_offset']
            
            if not all(field in packet for field in required_fields):
                logger.error(f"Missing required fields in packet from {addr}")
                return
            
            device_id = packet['device_id']
            
            # Handle device registration or reconnection
            if device_id not in self.devices:
                self._register_device(device_id, addr[0], addr[1])
            elif not self.devices[device_id].is_connected:
                self._handle_reconnection(device_id, addr[0], addr[1])
            
            # Update device status
            device = self.devices[device_id]
            device.last_message = time.time()
            device.message_count += 1
            device.signal_quality = packet['signal_quality']
            
            # Check for message gaps
            if device.last_message and (time.time() - device.last_message) > self.max_message_gap:
                logger.warning(f"Message gap detected for device {device_id}")
                device.error_count += 1
            
            # Add sample to processing queue
            self.sample_queues[device_id].put((
                packet['timestamp'],
                packet['raw_value'],
                packet['filtered_value'],
                packet['signal_quality'],
                packet['is_beat'],
                packet['rr_interval'],
                packet['time_offset']
            ))
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {addr}: {e}")
        except Exception as e:
            logger.error(f"Error handling packet from {addr}: {e}")
    
    def _handle_reconnection(self, device_id: int, ip: str, port: int):
        """Handle device reconnection"""
        device = self.devices[device_id]
        if device.ip != ip or device.port != port:
            logger.info(f"Device {device_id} reconnected from {ip}:{port}")
            device.ip = ip
            device.port = port
        device.is_connected = True
        device.error_count = 0
    
    def _process_samples(self):
        """Process samples from all devices"""
        while self.running:
            for device_id, queue in self.sample_queues.items():
                try:
                    while not queue.empty():
                        timestamp, raw_value, filtered_value, signal_quality, is_beat, rr_interval, time_offset = queue.get_nowait()
                        self._process_device_sample(device_id, timestamp, raw_value, filtered_value, signal_quality, is_beat, rr_interval, time_offset)
                except queue.Empty:
                    continue
            time.sleep(0.001)
    
    def _process_device_sample(self, device_id: int, timestamp: float, raw_value: float, 
                             filtered_value: float, signal_quality: float, is_beat: bool, 
                             rr_interval: float, time_offset: float):
        """Process a single sample from a device with improved error handling"""
        try:
            # Add to jitter buffer
            self.jitter_buffers[device_id].add_sample(filtered_value, timestamp, signal_quality)
            
            # Get recent samples for prediction
            recent_samples = self.jitter_buffers[device_id].get_samples(
                timestamp - 0.1, timestamp
            )
            
            if len(recent_samples) >= 10:
                # Prepare input for ML model
                input_data = np.array([s[1] for s in recent_samples[-10:]])
                
                # Make prediction using ML engine
                prediction = self.ml_engine.predict_signal(input_data)
                
                # Update visualization data
                self.ecg_data[device_id].append(filtered_value)
                self.times[device_id].append(timestamp)
                self.prediction_data[device_id].append(prediction[0])
                self.actual_data[device_id].append(filtered_value)
                
                # Update ML status
                self.ml_status['prediction_confidence'][device_id] = 1.0 - np.abs(prediction[0] - filtered_value) / 1000.0
                
                # Calculate heart rate if beat detected
                if is_beat:
                    hr = 60 / (rr_interval / 1000)  # Convert ms to seconds
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
                
                # Send to Max/MSP and TouchDesigner
                self._send_to_clients(device_id, filtered_value, prediction[0], is_beat, rr_interval)
                
        except Exception as e:
            logger.error(f"Error processing sample from device {device_id}: {e}")
            self.devices[device_id].error_count += 1
    
    def _send_to_clients(self, device_id: int, value: float, prediction: float, 
                        is_beat: bool, rr_interval: float):
        """Send data to Max/MSP and TouchDesigner with improved error handling"""
        for client_name, client in self.osc_clients.items():
            try:
                client.send_message(f"/ecg/{device_id}/raw", value)
                client.send_message(f"/ecg/{device_id}/prediction", prediction)
                if is_beat:
                    client.send_message(f"/ecg/{device_id}/beat", 1)
                    client.send_message(f"/ecg/{device_id}/rr", rr_interval)
            except Exception as e:
                logger.error(f"Error sending to {client_name}: {e}")
    
    def _sync_devices(self):
        """Synchronize all devices with master clock"""
        while self.running:
            current_time = time.time()
            for device_id, device in self.devices.items():
                try:
                    # Check for device timeout
                    if device.is_connected and (current_time - device.last_message) > self.reconnect_timeout:
                        logger.warning(f"Device {device_id} timeout")
                        device.is_connected = False
                        device.error_count += 1
                        continue
                    
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
                    device.error_count += 1
            
            time.sleep(self.sync_interval)
    
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
        """Update ML engine status information with device health"""
        status_text = "ML Engine Status:\n\n"
        
        # Model loading status
        status_text += f"Models Loaded: {'Yes' if self.ml_engine.predictor is not None else 'No'}\n"
        
        # Device-specific status
        for device_id in self.devices:
            device = self.devices[device_id]
            status_text += f"\nDevice {device_id}:\n"
            status_text += f"  Connected: {'Yes' if device.is_connected else 'No'}\n"
            status_text += f"  Signal Quality: {device.signal_quality:.2%}\n"
            status_text += f"  Error Count: {device.error_count}\n"
            status_text += f"  Message Count: {device.message_count}\n"
            
            if device_id in self.ml_status['prediction_confidence']:
                conf = self.ml_status['prediction_confidence'][device_id]
                status_text += f"  Prediction Confidence: {conf:.2%}\n"
            
            if device_id in self.ml_status['sync_detection']:
                sync = self.ml_status['sync_detection'][device_id]
                status_text += f"  Sync Detection: {sync:.2%}\n"
        
        # Last update time
        elapsed = time.time() - self.ml_status['last_update']
        status_text += f"\nLast Update: {elapsed:.1f}s ago"
        
        self.status_text.set_text(status_text)
    
    def _update_device_status(self):
        """Update the device status display"""
        status_text = "Device Status:\n\n"
        
        for device_id, device in self.devices.items():
            # Get connection status with color
            connection_status = "🟢 Connected" if device.is_connected else "🔴 Disconnected"
            
            # Get signal quality with color
            if device.signal_quality > 0.8:
                quality_color = "🟢"
            elif device.signal_quality > 0.5:
                quality_color = "🟡"
            else:
                quality_color = "🔴"
            
            # Format device info
            status_text += f"Device {device_id}:\n"
            status_text += f"  Status: {connection_status}\n"
            status_text += f"  Signal: {quality_color} {device.signal_quality:.1%}\n"
            status_text += f"  IP: {device.ip}:{device.port}\n"
            status_text += f"  Messages: {device.message_count}\n"
            status_text += f"  Errors: {device.error_count}\n"
            
            # Add message gap info if available
            if device_id in self.jitter_buffers:
                mean_gap, std_gap = self.jitter_buffers[device_id].get_message_gap_stats()
                status_text += f"  Avg Gap: {mean_gap*1000:.1f}ms ±{std_gap*1000:.1f}ms\n"
            
            status_text += "\n"
        
        self.device_status_text.set_text(status_text)

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
        
        # Update device status
        self._update_device_status()
        
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
                [self.status_text, self.device_status_text])

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