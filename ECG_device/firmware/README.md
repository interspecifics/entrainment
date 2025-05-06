# ECG Device Firmware

## Version History and Comparison

| Version | Key Features | Configuration | Signal Processing | ML Integration |
|---------|-------------|---------------|-------------------|----------------|
| 2.0.0 (Current) | • NVS-based config<br>• Signal quality metrics<br>• JSON message format<br>• Error logging | • Persistent storage<br>• Factory reset<br>• WiFi management<br>• OSC settings | • 500Hz sampling<br>• Adaptive thresholding<br>• High-pass filtering<br>• Quality assessment | • Timestamp sync<br>• Quality metrics<br>• RR intervals<br>• Beat events |
| 1.1.0 | • JSON file config<br>• Basic signal processing<br>• OSC messaging | • File-based storage<br>• Basic WiFi setup<br>• Single OSC server | • 500Hz sampling<br>• Fixed thresholding<br>• Basic filtering | • Basic beat detection<br>• Raw signal data |
| 1.0.0 | • Basic ECG processing<br>• Simple configuration | • Hard-coded settings<br>• Basic WiFi | • 500Hz sampling<br>• Simple thresholding | • Basic beat detection |

## Latest Version: 2.0.0

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

### Future Improvements
- [ ] Web-based configuration interface
- [ ] OTA updates
- [ ] Advanced signal processing
- [ ] Battery management
- [ ] Sleep mode optimization

### Contributing
Please follow the standard development workflow and ensure all changes are properly tested before submission.

### License
[Add your license information here] 