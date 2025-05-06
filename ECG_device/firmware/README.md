# ECG Device Firmware

## Version History and Comparison

| Version | Key Features | Configuration | Signal Processing | ML Integration |
|---------|-------------|---------------|-------------------|----------------|
| 2.0.0 (Current) | • NVS-based config<br>• Signal quality metrics<br>• JSON message format<br>• Error logging | • Persistent storage<br>• Factory reset<br>• WiFi management<br>• OSC settings | • 500Hz sampling<br>• Adaptive thresholding<br>• High-pass filtering<br>• Quality assessment | • Timestamp sync<br>• Quality metrics<br>• RR intervals<br>• Beat events |
| 1.1.0 | • JSON file config<br>• Basic signal processing<br>• OSC messaging | • File-based storage<br>• Basic WiFi setup<br>• Single OSC server | • 500Hz sampling<br>• Fixed thresholding<br>• Basic filtering | • Basic beat detection<br>• Raw signal data |
| 1.0.0 | • Basic ECG processing<br>• Simple configuration | • Hard-coded settings<br>• Basic WiFi | • 500Hz sampling<br>• Simple thresholding | • Basic beat detection |

## Latest Version: 2.0.0

### Pan-Tompkins QRS Detection Algorithm

The firmware implements an optimized version of the Pan-Tompkins algorithm, which is a widely-used method for QRS complex detection in ECG signals. Here's how it works in our implementation:

#### 1. Signal Preprocessing
- **Bandpass Filtering**: 
  - Low-pass filter (5-15 Hz) to reduce high-frequency noise
  - High-pass filter (0.5-5 Hz) to remove baseline wander
  - Implemented using exponential moving averages for efficiency

#### 2. Signal Processing Steps
- **Differentiation**:
  - Computes signal slope to enhance QRS complex
  - Uses 5-point derivative for real-time processing
  - Formula: `derivative = (2x[n] + x[n-1] - x[n-3] - 2x[n-4])/8`

- **Squaring**:
  - Squares the differentiated signal
  - Makes all values positive
  - Emphasizes higher frequencies

- **Integration**:
  - Moving window integration
  - Window size: 8 samples
  - Smoothes the signal while preserving QRS information

#### 3. Adaptive Thresholding
- **Dynamic Thresholds**:
  - Signal level (SPKI): Updated when QRS is detected
  - Noise level (NPKI): Updated during non-QRS periods
  - Formula: `threshold = NPKI + 0.25(SPKI - NPKI)`

- **Refractory Period**:
  - 350ms after each QRS detection
  - Prevents multiple detections of the same beat
  - Adjusts based on heart rate

#### 4. Search Back
- **Backward Search**:
  - If no QRS detected for 1.5x average RR interval
  - Threshold is reduced by 50%
  - Searches for missed beats

#### 5. Performance Optimizations
- **Memory Efficiency**:
  - Ring buffer implementation
  - Fixed-point arithmetic
  - Minimal memory allocation

- **Real-time Processing**:
  - 500Hz sampling rate
  - < 2ms processing delay
  - Efficient modulo operations

#### 6. Quality Assessment
- **Signal Quality Metrics**:
  - SNR calculation
  - Amplitude validation
  - Stability assessment
  - Quality score (0-1)

### Files Included
```
firmware/
├── main-QRS-timer.py      # Main ECG processing and QRS detection
├── device_config.py       # Device configuration management (NVS-based)
└── README.md             # This documentation file
```

### Overview
This firmware implements a real-time ECG signal processing and QRS detection system for ESP32-based devices. It features advanced signal processing, device configuration management, and ML server integration capabilities.

### Key Features

#### 1. Real-time ECG Processing
- 500Hz sampling rate
- Optimized QRS detection algorithm
- Adaptive thresholding
- High-pass filtering
- Signal quality assessment

#### 2. Device Configuration (NVS-based)
- Persistent device ID storage
- WiFi configuration management
- OSC server settings
- Factory reset capability
- Unique device identification

#### 3. ML Server Integration
- Standardized JSON message format
- Timestamp synchronization
- Signal quality metrics
- Beat detection events
- RR interval calculation

### Message Format
```json
{
    "device_id": 1,
    "timestamp": 1234567890,
    "raw_value": 2048,
    "filtered_value": 1024,
    "signal_quality": 0.85,
    "is_beat": true,
    "rr_interval": 800
}
```

### Signal Quality Metrics
- Signal-to-Noise Ratio (SNR)
- Signal amplitude validation
- Signal stability assessment
- Quality score (0-1 scale)

### Configuration
The device can be configured through the `DeviceConfig` class:
- Device ID
- WiFi credentials
- OSC server addresses
- Signal processing parameters

### Hardware Requirements
- ESP32 microcontroller
- ECG sensor input (ADC pin 4)
- NeoPixel LED (pin 18)
- WiFi connectivity

### Dependencies
- MicroPython
- uosc library
- neopixel library
- esp32 NVS support

### Usage
1. Flash the firmware to ESP32
2. Configure device settings (optional)
3. Power on the device
4. Monitor output through OSC messages

### Error Handling
- Automatic error logging
- Recovery mechanisms
- Factory reset capability
- Signal quality degradation handling

### Performance Considerations
- Optimized memory usage
- Efficient flash storage
- Real-time processing capabilities
- Low latency communication

### Security Features
- Secure WiFi configuration
- Device identification
- Configuration protection
- Error logging

### Development Notes
- Uses ESP32's NVS for configuration
- Implements ring buffer for sampling
- Optimized for low memory usage
- Supports multiple OSC servers

