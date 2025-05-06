# ECG Server with ML-Enhanced Entrainment Analysis

A real-time ECG server that handles multiple devices, provides ML-enhanced signal analysis, and performs comprehensive entrainment analysis between devices.

## Features

### Core Functionality
- Multi-device support (up to 5 devices)
- Real-time ECG signal processing
- UDP-based communication
- Jitter buffer implementation
- Clock synchronization
- Heart rate monitoring

### Machine Learning Capabilities
1. **Predictive Completion**
   - LSTM-based ECG signal prediction
   - Real-time signal completion
   - Confidence scoring
   - Adaptive learning

2. **Synchrony Detection**
   - Neural network-based synchrony analysis
   - Real-time device pair comparison
   - Synchronization scoring
   - Pattern recognition

3. **Entrainment Analysis**
   - Phase synchronization measurement
   - Amplitude coupling analysis
   - Temporal alignment detection
   - Comprehensive entrainment scoring

### Visualization
1. **Real-time Plots**
   - ECG signals
   - Heart rate trends
   - Clock offsets
   - Network jitter
   - ML predictions vs actual signals

2. **Analysis Panels**
   - Entrainment metrics
   - ML engine status
   - Device synchronization status
   - Performance metrics

### Integration
- Max/MSP support via OSC
- TouchDesigner integration
- Real-time data streaming
- Custom visualization options

## Installation

1. **Prerequisites**
```bash
pip install -r requirements.txt
```

2. **Required Packages**
```
numpy
torch
scipy
matplotlib
pythonosc
pandas
```

3. **Model Files**
Place pre-trained models in the `models/` directory:
- `predictor.pth`: Predictive completion model
- `sync_detector.pth`: Synchrony detection model

## Usage

### Starting the Server
```bash
python ecg_server.py
```

### Configuration
The server can be configured through the following parameters:
```python
server = ECGServer(
    host='0.0.0.0',  # Server host
    port=8000,       # Server port
)
```

### Device Connection
Devices should connect via UDP and send data in the following format:
```json
{
    "device_id": 1,
    "timestamp": 1234567890.123,
    "sample": 0.5
}
```

### OSC Integration
The server sends data to:
- Max/MSP: `127.0.0.1:8001`
- TouchDesigner: `127.0.0.1:8002`

## ML Features

### Predictive Completion
- Input: Recent ECG samples (10 samples)
- Output: Predicted next sample
- Confidence score included

### Synchrony Detection
- Analyzes pairs of devices
- Computes synchronization score
- Real-time updates

### Entrainment Analysis
1. **Phase Synchronization**
   - Hilbert transform-based analysis
   - Phase locking value computation
   - Real-time phase difference tracking

2. **Amplitude Coupling**
   - Envelope correlation analysis
   - Amplitude relationship detection
   - Coupling strength measurement

3. **Temporal Alignment**
   - Peak detection and comparison
   - Interval correlation analysis
   - Timing pattern matching

## Visualization

### Real-time Plots
1. **ECG Signals**
   - Raw signal display
   - Multiple device overlay
   - Color-coded by device

2. **Heart Rate**
   - Real-time HR calculation
   - Trend visualization
   - Device comparison

3. **Timing Information**
   - Clock offset tracking
   - Jitter measurement
   - Synchronization status

4. **ML Predictions**
   - Predicted vs actual signals
   - Confidence visualization
   - Error tracking

5. **Entrainment Analysis**
   - Phase sync scores
   - Amplitude coupling
   - Temporal alignment
   - Overall entrainment

6. **ML Status**
   - Model loading status
   - Prediction confidence
   - Sync detection scores
   - Update frequency

## Performance Considerations

### Memory Usage
- ECG data buffer: 1000 samples per device
- HR data buffer: 100 samples per device
- Timing data buffer: 100 samples per device

### Processing Requirements
- Real-time signal processing
- ML model inference
- Visualization updates
- OSC message handling

### Network Requirements
- UDP communication
- Low latency connection
- Stable network conditions

## Troubleshooting

### Common Issues
1. **Connection Problems**
   - Check UDP port availability
   - Verify device IP addresses
   - Ensure network connectivity

2. **ML Model Issues**
   - Verify model file presence
   - Check model compatibility
   - Monitor prediction confidence

3. **Visualization Problems**
   - Check matplotlib backend
   - Monitor system resources
   - Verify data flow

### Logging
- Log file: `ecg_server.log`
- Log level: INFO
- Includes errors and warnings

