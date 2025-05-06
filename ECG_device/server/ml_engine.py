import torch
import torch.nn as nn
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from scipy import signal
from scipy.stats import pearsonr
import torch.nn.functional as F

@dataclass
class EntrainmentScore:
    """Structure for entrainment analysis results"""
    phase_sync: float  # Phase synchronization score
    amplitude_coupling: float  # Amplitude coupling score
    temporal_alignment: float  # Temporal alignment score
    overall_score: float  # Combined entrainment score

class PredictiveCompletion(nn.Module):
    """LSTM-based model for ECG signal prediction and completion"""
    def __init__(self, input_size: int = 10, hidden_size: int = 64, num_layers: int = 2):
        super(PredictiveCompletion, self).__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
    
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        return self.fc(lstm_out[:, -1, :])

class SynchronyDetector(nn.Module):
    """Neural network for detecting synchrony between multiple ECG signals"""
    def __init__(self, input_size: int = 20, hidden_size: int = 64):
        super(SynchronyDetector, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU()
        )
        self.sync_head = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x1, x2):
        # Encode both signals
        h1 = self.encoder(x1)
        h2 = self.encoder(x2)
        
        # Compute synchrony score
        combined = torch.abs(h1 - h2)
        return self.sync_head(combined)

class EntrainmentAnalyzer:
    """Analyzes entrainment between multiple ECG signals"""
    def __init__(self, window_size: int = 1000, sampling_rate: int = 500):
        self.window_size = window_size
        self.sampling_rate = sampling_rate
    
    def compute_phase_sync(self, signal1: np.ndarray, signal2: np.ndarray) -> float:
        """Compute phase synchronization between two signals"""
        # Compute analytic signals using Hilbert transform
        analytic1 = signal.hilbert(signal1)
        analytic2 = signal.hilbert(signal2)
        
        # Extract phases
        phase1 = np.angle(analytic1)
        phase2 = np.angle(analytic2)
        
        # Compute phase difference
        phase_diff = np.mod(phase1 - phase2, 2*np.pi)
        
        # Compute phase locking value
        plv = np.abs(np.mean(np.exp(1j * phase_diff)))
        return float(plv)
    
    def compute_amplitude_coupling(self, signal1: np.ndarray, signal2: np.ndarray) -> float:
        """Compute amplitude coupling between two signals"""
        # Compute signal envelopes
        env1 = np.abs(signal.hilbert(signal1))
        env2 = np.abs(signal.hilbert(signal2))
        
        # Compute correlation between envelopes
        correlation, _ = pearsonr(env1, env2)
        return float(correlation)
    
    def compute_temporal_alignment(self, signal1: np.ndarray, signal2: np.ndarray) -> float:
        """Compute temporal alignment between two signals"""
        # Find peaks in both signals
        peaks1, _ = signal.find_peaks(signal1, distance=self.sampling_rate//2)
        peaks2, _ = signal.find_peaks(signal2, distance=self.sampling_rate//2)
        
        if len(peaks1) < 2 or len(peaks2) < 2:
            return 0.0
        
        # Compute inter-peak intervals
        intervals1 = np.diff(peaks1)
        intervals2 = np.diff(peaks2)
        
        # Compute correlation between intervals
        correlation, _ = pearsonr(intervals1, intervals2)
        return float(correlation)
    
    def analyze_entrainment(self, signals: Dict[int, np.ndarray]) -> Dict[Tuple[int, int], EntrainmentScore]:
        """Analyze entrainment between all pairs of signals"""
        results = {}
        device_ids = list(signals.keys())
        
        for i in range(len(device_ids)):
            for j in range(i+1, len(device_ids)):
                id1, id2 = device_ids[i], device_ids[j]
                signal1, signal2 = signals[id1], signals[id2]
                
                # Compute individual metrics
                phase_sync = self.compute_phase_sync(signal1, signal2)
                amp_coupling = self.compute_amplitude_coupling(signal1, signal2)
                temp_align = self.compute_temporal_alignment(signal1, signal2)
                
                # Compute overall score (weighted average)
                overall_score = (
                    0.4 * phase_sync +
                    0.3 * amp_coupling +
                    0.3 * temp_align
                )
                
                results[(id1, id2)] = EntrainmentScore(
                    phase_sync=phase_sync,
                    amplitude_coupling=amp_coupling,
                    temporal_alignment=temp_align,
                    overall_score=overall_score
                )
        
        return results

class MLEngine:
    """Main ML engine coordinating all models and analyses"""
    def __init__(self, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        self.device = device
        self.predictor = PredictiveCompletion().to(device)
        self.sync_detector = SynchronyDetector().to(device)
        self.entrainment_analyzer = EntrainmentAnalyzer()
        
        # Load pre-trained models if available
        self._load_models()
    
    def _load_models(self):
        """Load pre-trained models"""
        try:
            self.predictor.load_state_dict(torch.load('models/predictor.pth'))
            self.sync_detector.load_state_dict(torch.load('models/sync_detector.pth'))
        except:
            print("No pre-trained models found. Using initialized models.")
    
    def predict_signal(self, signal: np.ndarray) -> np.ndarray:
        """Predict and complete ECG signal"""
        self.predictor.eval()
        with torch.no_grad():
            # Prepare input
            x = torch.FloatTensor(signal).unsqueeze(0).to(self.device)
            # Make prediction
            prediction = self.predictor(x)
            return prediction.cpu().numpy()
    
    def detect_synchrony(self, signal1: np.ndarray, signal2: np.ndarray) -> float:
        """Detect synchrony between two signals"""
        self.sync_detector.eval()
        with torch.no_grad():
            # Prepare inputs
            x1 = torch.FloatTensor(signal1).unsqueeze(0).to(self.device)
            x2 = torch.FloatTensor(signal2).unsqueeze(0).to(self.device)
            # Compute synchrony score
            score = self.sync_detector(x1, x2)
            return float(score.cpu().numpy())
    
    def analyze_entrainment(self, signals: Dict[int, np.ndarray]) -> Dict[Tuple[int, int], EntrainmentScore]:
        """Analyze entrainment between multiple signals"""
        return self.entrainment_analyzer.analyze_entrainment(signals)
    
    def process_signals(self, signals: Dict[int, np.ndarray]) -> Dict:
        """Process multiple signals and return comprehensive analysis"""
        results = {
            'predictions': {},
            'synchrony': {},
            'entrainment': {}
        }
        
        # Generate predictions for each signal
        for device_id, signal in signals.items():
            results['predictions'][device_id] = self.predict_signal(signal)
        
        # Compute synchrony between all pairs
        device_ids = list(signals.keys())
        for i in range(len(device_ids)):
            for j in range(i+1, len(device_ids)):
                id1, id2 = device_ids[i], device_ids[j]
                sync_score = self.detect_synchrony(signals[id1], signals[id2])
                results['synchrony'][(id1, id2)] = sync_score
        
        # Analyze entrainment
        results['entrainment'] = self.analyze_entrainment(signals)
        
        return results 