# Dasboard for HRV Entrainment Real Time Visualization

## Overview

This system shows graphs for the analysis of heart rate variability (HRV) entrainment between pairs of subjects in real-time. It receives ECG data via OSC protocol, processes it to detect QRS complexes, calculates HRV, and provides real-time visualization and recording capabilities.

## Features

- **Multi-subject analysis**: Monitors up to 6 subjects organized in 3 pairs
- **Real-time visualization**: ECG waveforms, HRV trends, cross-correlation analysis
- **Data recording**: Records beat detection, raw ECG, timestamps, and HRV
- **Interactive controls**: Adjust time ranges, select subject pairs, toggle recording

## System Requirements

- Python 3.6+
- PyQt5
- PyQtGraph
- numpy
- scipy
- python-osc

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install numpy scipy pyqt5 pyqtgraph python-osc
   ```

## Usage

### Basic Usage

Run the application with default settings:

```
python main.py
```

### Command Line Options

- `--record`: Enable data recording at startup
- `--visualize`: Enable visualization (default: True)
- `--ip ADDRESS`: Set OSC server IP address
- `--port PORT`: Set OSC server port
- `--sample-rate RATE`: Set ECG sample rate in Hz

Example:
```
python main.py --record --ip 192.168.1.100 --port 8001
```

### Keyboard Controls

- `+/-`: Increase/decrease HRV time range
- `1-3`: Select subject pair (1-3) for detailed view
- `R`: Toggle recording on/off

## Data Input Format

The system expects OSC messages with the following format for each channel (e.g., "/c1", "/c2", etc.):

1. **Beat detected** (boolean):
   - `1` or `True` if a beat was detected
   - `0` or `False` if no beat was detected

2. **Raw ECG** (integer): 
   - Integer value representing the raw ECG reading

Example OSC message to channel "/c1":
```
/c1 1 520
```
This represents a beat detected (1) with raw ECG value of 520.

## Output Format

Recorded data is saved as tab-separated values (TSV) files with the following columns:

1. **Beat**: Boolean indicating beat detection (1=detected, 0=not detected)
2. **Raw_ECG**: Raw integer ECG values from the sensor
3. **Timestamp**: Unix epoch time in seconds
4. **HRV**: Heart Rate Variability calculated using SDNN method

Example output:
```
Beat    Raw_ECG    Timestamp    HRV
1       520        1621345678   0.053241
0       498        1621345679   0.053241
0       505        1621345680   0.053241
1       523        1621345681   0.054012
```

## Architecture

The system consists of several modules:

- **main.py**: Entry point and integration
- **network.py**: OSC communication and data handling
- **processing.py**: Signal processing and HRV calculation
- **graphs.py**: Real-time visualization
- **record_data.py**: Data recording and file management
- **config.py**: Centralized configuration

## Recording Data

Data is recorded in a timestamped folder (e.g., "ECG_HRV_Recording_20220228_120000") with one file per channel (e.g., "ECG_c1.txt"). A metadata file ("recording_info.txt") provides details about the recording session.

Start/stop recording using:
- The `R` key
- The recording button in the GUI
- The `--record` command line option

## Customization

Most settings can be adjusted in the `config.py` file:

- Network parameters (IP, port)
- Sample rate and filtering parameters
- Visualization settings
- Subject pairing configuration

## Troubleshooting

- **No data received**: Check OSC IP address and port configuration
- **Missing dependencies**: Install required packages using pip
- **Visualization issues**: Make sure PyQt and PyQtGraph are properly installed
- **High CPU usage**: Decrease sample rate or disable visualization for headless operation

## License

This software is provided as-is under the MIT License.
