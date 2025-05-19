# graphs.py
"""
Real-time Heart Rate Variability Entrainment Analysis
Graphs module - handles visualization using PyQtGraph

Modified to display all 6 subjects with 6-column layout (one column per subject)
Added support for recording control
"""
import numpy as np
import time
from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import sys
import config  # Import centralized configuration

# ============ PyQtGraph Visualization ============
class EntrainmentVisualizerQt:
    """PyQtGraph-based real-time visualization of entrainment analysis"""
    
    def __init__(self, osc_handler, subject_pairs=None):
        self.osc_handler = osc_handler
        self.subject_pairs = subject_pairs or config.SUBJECT_PAIRS
        self.active_pair_idx = 0  # Currently selected pair for detailed entrainment view
        
        # Collect all channels from all pairs
        self.all_channels = []
        for pair in self.subject_pairs:
            self.all_channels.extend(pair)
        
        # Create PyQtGraph application
        self.app = QtWidgets.QApplication.instance()
        if self.app is None:
            self.app = QtWidgets.QApplication(sys.argv)
        
        # Define colors using the configuration values
        self.colors = {
            "/c1": config.ECG_C1_COLOR,
            "/c2": config.ECG_C2_COLOR,
            "/c3": config.ECG_C3_COLOR,
            "/c4": config.ECG_C4_COLOR,
            "/c5": config.ECG_C5_COLOR,
            "/c6": config.ECG_C6_COLOR,
            "rr_interval": config.RR_INTERVAL_COLOR,
            "cross_corr": config.CROSS_CORR_COLOR
        }
        
        # Set up the main window using configured dimensions
        self.win = pg.GraphicsLayoutWidget(show=True)
        self.win.setWindowTitle('HRV Entrainment Analysis - All 6 Subjects')
        self.win.resize(config.WINDOW_SIZE, config.WINDOW_HEIGHT)
        
        # Set up plots
        self.setup_plots()
        
        # User-configurable settings from configuration section
        self.hrv_time_range = config.HRV_DISPLAY_RANGE
        
        # Timer for updates
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(50)  # 50ms = 20 fps
        
        # Add key press event handler for user controls
        self.win.keyPressEvent = self.keyPressEvent
        
        # Recording-related attributes
        self.recording_indicator = None
        self.record_button = None
        self.data_recorder = None
    
    def keyPressEvent(self, event):
        """Handle key press events for user control"""
        key = event.key()
        
        # HRV Time range controls
        if key == QtCore.Qt.Key_Plus or key == QtCore.Qt.Key_Equal:
            # Increase HRV time range (zoom out)
            self.hrv_time_range = min(120, self.hrv_time_range + 10)
            print(f"HRV time range: {self.hrv_time_range} seconds")
        elif key == QtCore.Qt.Key_Minus:
            # Decrease HRV time range (zoom in)
            self.hrv_time_range = max(10, self.hrv_time_range - 10)
            print(f"HRV time range: {self.hrv_time_range} seconds")
        
        # Pair selection controls for entrainment view
        elif key == QtCore.Qt.Key_1:
            self.active_pair_idx = 0
            self.update_pair_selection()
        elif key == QtCore.Qt.Key_2:
            self.active_pair_idx = 1
            self.update_pair_selection()
        elif key == QtCore.Qt.Key_3:
            self.active_pair_idx = 2
            self.update_pair_selection()
        
        # Default Qt key handling
        QtWidgets.QGraphicsView.keyPressEvent(self.win, event)
    
    def update_pair_selection(self):
        """Update UI to reflect the active pair selection"""
        if 0 <= self.active_pair_idx < len(self.subject_pairs):
            pair = self.subject_pairs[self.active_pair_idx]
            print(f"Selected pair {self.active_pair_idx + 1}: {pair[0]} - {pair[1]}")
            
            # Update title on correlation plot
            self.corr_plots[self.active_pair_idx].setTitle(
                f"HRV Cross-Correlation - Pair {self.active_pair_idx + 1}: {pair[0]} - {pair[1]}"
            )
    
    def setup_plots(self):
        """Set up all the plots in a 6-column layout - one column per subject"""
        
        # Create a layout with 6 columns (one for each subject)
        for i in range(6):
            self.win.ci.layout.setColumnStretchFactor(i, 1)
        
        # Initialize plot containers
        self.ecg_plots = {}
        self.ecg_curves = {}
        self.ecg_peaks = {}
        self.hrv_plots = {}
        self.hrv_curves = {}
        self.corr_plots = {}
        self.corr_curves = {}
        self.corr_history_plots = {}
        self.corr_history_imgs = {}
        self.colorbar_list = []
        
        # Row 1: ECG plots for all 6 channels (one in each column)
        for i, channel in enumerate(self.all_channels):
            col = i  # Each channel gets its own column (0-5)
            
            # ECG Plot
            self.ecg_plots[channel] = self.win.addPlot(row=0, col=col, title=f"ECG {channel}")
            self.ecg_plots[channel].setLabel('left', "Amplitude")
            self.ecg_plots[channel].setLabel('bottom', "Sample")
            self.ecg_plots[channel].showGrid(x=True, y=True, alpha=0.3)
            
            self.ecg_curves[channel] = self.ecg_plots[channel].plot(pen=pg.mkPen(self.colors[channel], width=1))
            self.ecg_peaks[channel] = pg.ScatterPlotItem(size=8, brush=pg.mkBrush(config.R_PEAK_COLOR))
            self.ecg_plots[channel].addItem(self.ecg_peaks[channel])
            
            # HRV Plot (below ECG)
            self.hrv_plots[channel] = self.win.addPlot(row=1, col=col, title=f"HRV {channel}")
            self.hrv_plots[channel].setLabel('left', "HRV")
            self.hrv_plots[channel].setLabel('bottom', "Time (s)")
            self.hrv_plots[channel].showGrid(x=True, y=True, alpha=0.3)
            
            self.hrv_curves[channel] = self.hrv_plots[channel].plot(
                pen=pg.mkPen(self.colors[channel], width=2),
                name=channel
            )
        
        # Row 3-4: Cross-correlation plots and history heatmaps for each pair (using 2 columns per plot)
        for pair_idx, (ch1, ch2) in enumerate(self.subject_pairs):
            # Calculate column position based on pair index
            col = pair_idx * 2  # Each plot spans 2 columns
            
            # Cross-correlation plot
            self.corr_plots[pair_idx] = self.win.addPlot(
                row=2, col=col, colspan=2,
                title=f"HRV Cross-Correlation - Pair {pair_idx + 1}: {ch1} - {ch2}"
            )
            self.corr_plots[pair_idx].setLabel('left', "Correlation")
            self.corr_plots[pair_idx].setLabel('bottom', "Lag (samples)")
            self.corr_plots[pair_idx].showGrid(x=True, y=True, alpha=0.3)
            self.corr_plots[pair_idx].setXRange(-config.MAX_CROSS_CORR_LAG, config.MAX_CROSS_CORR_LAG)
            self.corr_plots[pair_idx].setYRange(-1.1, 1.1)
            
            self.corr_curves[pair_idx] = self.corr_plots[pair_idx].plot(
                pen=pg.mkPen(self.colors["cross_corr"], width=2)
            )
            
            # Correlation History Heatmap (below correlation plot)
            self.corr_history_plots[pair_idx] = self.win.addPlot(
                row=3, col=col, colspan=2,
                title=f"Entrainment Evolution Over Time - Pair {pair_idx + 1}: {ch1} - {ch2}"
            )
            self.corr_history_plots[pair_idx].setLabel('left', "Time (newest at top)")
            self.corr_history_plots[pair_idx].setLabel('bottom', "Lag (samples)")
            self.corr_history_plots[pair_idx].showGrid(x=True, y=True, alpha=0.3)
            
            # Create the image item for the heatmap
            self.corr_history_imgs[pair_idx] = pg.ImageItem()
            self.corr_history_plots[pair_idx].addItem(self.corr_history_imgs[pair_idx])
            
            # Add color bar
            colorbar = pg.ColorBarItem(
                values=(-1, 1),
                colorMap=pg.colormap.get('viridis'),
                label='Correlation'
            )
            colorbar.setImageItem(self.corr_history_imgs[pair_idx])
            self.colorbar_list.append(colorbar)
        
        # Add update rate text item for debugging
        self.update_rate_text = pg.TextItem(text="", color=(255, 255, 255), anchor=(0, 0))
        self.corr_plots[0].addItem(self.update_rate_text)
        self.update_rate_text.setPos(-config.MAX_CROSS_CORR_LAG + 1, -1.05)
        
        # Make rows appropriately sized
        self.win.ci.layout.setRowStretchFactor(0, 1)  # ECG row
        self.win.ci.layout.setRowStretchFactor(1, 1)  # HRV row
        self.win.ci.layout.setRowStretchFactor(2, 1)  # Correlation row
        self.win.ci.layout.setRowStretchFactor(3, 1)  # Correlation history row
        
        # Add instructions text
        self.instruction_label = pg.TextItem(
            html='<div style="text-align: center">'
                 '<span style="color: #FFF;">Controls: +/- to adjust time range</span>'
                 '</div>',
            anchor=(0.5, 0),
            border=pg.mkPen(color=(100, 100, 100)),
            fill=pg.mkBrush(color=(50, 50, 50, 100))
        )
        self.corr_plots[2].addItem(self.instruction_label)
        self.instruction_label.setPos(0, -1.05)  # Position at bottom-center
    
    def update_plots(self):
        """Update all plots with the latest data"""
        # Update ECG and HRV plots for all channels
        self.update_ecg_plots(self.all_channels)
        self.update_hrv_plots(self.all_channels)
        
        # Update cross-correlation plots and history heatmaps for all pairs
        self.update_corr_plots()
        self.update_corr_history()
        
        # Update debug info
        self.update_debug_info()
        
        # Update recording status if available
        if hasattr(self, 'data_recorder') and self.data_recorder is not None:
            self.update_recording_status()
        
    def update_ecg_plots(self, channels):
        """Update ECG plots for the given channels"""
        for channel in channels:
            if channel in self.osc_handler.raw_data:
                raw_data = list(self.osc_handler.raw_data[channel])
                if raw_data:
                    x = np.arange(len(raw_data))
                    self.ecg_curves[channel].setData(x, raw_data)
                    
                    # Update R-peaks
                    qrs_detector = self.osc_handler.qrs_detectors[channel]
                    
                    # Get a list of all R-peak indices
                    r_indices = np.array(qrs_detector.r_peaks_indices)
                    
                    # Filter to only recent ones within the current view
                    buffer_start = qrs_detector.buffer_idx_counter - len(raw_data)
                    recent_indices = []
                    peak_values = []
                    
                    for i, idx in enumerate(r_indices):
                        if idx >= buffer_start and idx < qrs_detector.buffer_idx_counter:
                            # Convert to plot coordinates
                            plot_idx = idx - buffer_start
                            if 0 <= plot_idx < len(raw_data):
                                recent_indices.append(plot_idx)
                                peak_values.append(raw_data[plot_idx])
                    
                    # Update peak markers
                    if recent_indices:
                        self.ecg_peaks[channel].setData(recent_indices, peak_values)
                    else:
                        self.ecg_peaks[channel].setData([], [])
                    
                    # Set a fixed display range based on the ECG_DISPLAY_SECONDS constant
                    display_samples = config.SAMPLE_RATE * config.ECG_DISPLAY_SECONDS
                    
                    # Calculate the start point to display the most recent data
                    if len(raw_data) > display_samples:
                        start_idx = len(raw_data) - display_samples
                    else:
                        start_idx = 0
                    
                    end_idx = len(raw_data)
                    
                    # Set X range to show the specified time window
                    self.ecg_plots[channel].setXRange(start_idx, end_idx)
                    
                    # Set Y range based on the visible data
                    visible_data = raw_data[start_idx:end_idx]
                    if len(visible_data) > 0:
                        y_min = np.min(visible_data)
                        y_max = np.max(visible_data)
                        y_range = max(y_max - y_min, 0.1)
                        self.ecg_plots[channel].setYRange(
                            y_min - 0.1 * y_range,
                            y_max + 0.1 * y_range
                        )
    
    def update_hrv_plots(self, channels):
        """Update HRV plots for all channels"""
        t_ref = time.time()
        
        for channel in channels:
            # Find the pair this channel belongs to
            pair_idx = None
            for i, pair in enumerate(self.subject_pairs):
                if channel in pair:
                    pair_idx = i
                    break
                    
            if pair_idx is None:
                continue
                
            # Get the entrainment analyzer for this pair
            entrainment_analyzer = self.osc_handler.get_entrainment_analyzer(pair_idx)
            if entrainment_analyzer is None:
                continue
                
            hrv_data = entrainment_analyzer.get_hrv_data()
            
            if channel in hrv_data:
                # Calculate relative times in seconds (negative values, with 0 being the present)
                times = np.array([t_ref - t for t in hrv_data[channel]['times']])
                values = np.array(hrv_data[channel]['values'])
                
                if len(times) > 0:
                    # Filter to only show data within the user-selected time range
                    mask = times >= 0
                    mask &= times <= self.hrv_time_range
                    
                    if any(mask):
                        # Use negative time values on x-axis (0 = present, negative = past)
                        self.hrv_curves[channel].setData(-times[mask], values[mask])
                        
                        # Set HRV plot range based on user-configured time range
                        self.hrv_plots[channel].setXRange(-self.hrv_time_range, 0)
                        
                        # Set y-axis range for HRV plot
                        if len(values[mask]) > 0:
                            min_hrv = min(values[mask])
                            max_hrv = max(values[mask])
                            hrv_range = max_hrv - min_hrv
                            
                            if hrv_range < 0.01:
                                mean_hrv = np.mean(values[mask])
                                self.hrv_plots[channel].setYRange(max(0, mean_hrv - 0.005), mean_hrv + 0.005)
                            else:
                                self.hrv_plots[channel].setYRange(
                                    max(0, min_hrv - 0.1 * hrv_range),
                                    max_hrv + 0.1 * hrv_range
                                )
    
    def update_corr_plots(self):
        """Update correlation plots for all pairs"""
        for pair_idx in range(len(self.subject_pairs)):
            entrainment_analyzer = self.osc_handler.get_entrainment_analyzer(pair_idx)
            if entrainment_analyzer is None:
                continue
                
            lags, cross_corr = entrainment_analyzer.get_entrainment_results()
            if len(cross_corr) > 0:
                self.corr_curves[pair_idx].setData(lags, cross_corr)
    
    def update_corr_history(self):
        """Update correlation history heatmaps for all pairs"""
        for pair_idx in range(len(self.subject_pairs)):
            entrainment_analyzer = self.osc_handler.get_entrainment_analyzer(pair_idx)
            if entrainment_analyzer is None:
                continue
                
            timestamps, corr_history = entrainment_analyzer.get_correlation_history()
            
            if len(corr_history) > 1 and len(timestamps) > 1:
                # Create a 2D numpy array from the correlation history
                corr_matrix = np.array(corr_history)
                
                # Update the image
                self.corr_history_imgs[pair_idx].setImage(corr_matrix, levels=(-1, 1))
                
                # Set the scale of the image to match the lag values and time points
                # The rect is (left, top, width, height)
                lag_range = 2 * config.MAX_CROSS_CORR_LAG  # Fix: Use config.MAX_CROSS_CORR_LAG
                rect_x = -config.MAX_CROSS_CORR_LAG  # Fix: Use config.MAX_CROSS_CORR_LAG
                rect_y = 0
                rect_width = lag_range
                rect_height = len(corr_history)
                
                self.corr_history_imgs[pair_idx].setRect(QtCore.QRectF(
                    rect_x, rect_y, rect_width, rect_height
                ))
                
                # Update colorbar range
                if pair_idx < len(self.colorbar_list):
                    self.colorbar_list[pair_idx].setLevels((-1, 1))
    
    def update_debug_info(self):
        """Update debug information display"""
        update_rate = self.osc_handler.get_update_rate()
        time_range_info = f"HRV Display: {self.hrv_time_range}s (press +/- to adjust)"
        
        # Update the text in the correlation plot
        self.update_rate_text.setText(f"Update rate: {update_rate:.1f} Hz | {time_range_info}")
    
    def update_recording_status(self):
        """Update recording status indicator if available"""
        if not hasattr(self, 'recording_indicator') or self.recording_indicator is None:
            return
            
        if not hasattr(self, 'data_recorder') or self.data_recorder is None:
            return
            
        try:
            # Check if recording is active
            if hasattr(self.data_recorder, 'is_recording') and self.data_recorder.is_recording():
                # Get recording status
                if hasattr(self.data_recorder, 'get_recording_status'):
                    status = self.data_recorder.get_recording_status()
                    if isinstance(status, dict) and 'duration' in status and 'total_samples' in status:
                        # Update indicator with detailed info
                        self.recording_indicator.setHtml(
                            f'<div style="text-align: center">'
                            f'<span style="color: #FFF; background-color: #700; padding: 3px 10px;">'
                            f'RECORDING: {status["duration"]:.1f}s | {status["total_samples"]} samples</span>'
                            f'</div>'
                        )
        except Exception as e:
            # Handle any exceptions from status checking
            if config.DEBUG_MODE:  # Fix: Use config.DEBUG_MODE
                print(f"Error updating recording status: {e}")
    
    def add_recording_controls(self, data_recorder):
        """Add recording controls to the visualization
        
        Args:
            data_recorder: An instance of ECGDataRecorder
        """
        # Store the data recorder
        self.data_recorder = data_recorder
        
        # Add recording status indicator in a prominent position
        self.recording_indicator = pg.TextItem(
            html='<div style="text-align: center">'
                 '<span style="color: #FFF; background-color: #333; padding: 3px 10px;">RECORDING: OFF</span>'
                 '</div>',
            anchor=(0.5, 0),
            border=pg.mkPen(color=(100, 100, 100), width=2),
            fill=pg.mkBrush(color=(50, 50, 50, 200))
        )
        
        # Add to top-right of the first correlation plot for visibility
        self.corr_plots[0].addItem(self.recording_indicator)
        self.recording_indicator.setPos(0, 1.0)  # Position at top-center
        
        # Add a button for recording toggle
        self.record_button = QtWidgets.QPushButton("Start Recording")
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #444;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
        """)
        
        # Create proxy widget for the button
        proxy = QtWidgets.QGraphicsProxyWidget()
        proxy.setWidget(self.record_button)
        
        # Add to the bottom of the window for easy access
        self.win.addItem(proxy, row=4, col=2, colspan=2)
        
        # Connect button click event
        self.record_button.clicked.connect(self.toggle_recording)
        
        # Store the original keyPressEvent handler
        original_keyPressEvent = self.keyPressEvent
        
        # Create a new keyPressEvent handler that includes recording toggle
        def extended_keyPressEvent(event):
            key = event.key()
            
            # Toggle recording with R key
            if key == QtCore.Qt.Key_R:
                self.toggle_recording()
            else:
                # Call the original handler for other keys
                original_keyPressEvent(event)
        
        # Replace the key press event handler
        self.keyPressEvent = extended_keyPressEvent
        
        # Update instructions text to include recording control
        self.instruction_label.setHtml(
            '<div style="text-align: center">'
            '<span style="color: #FFF; background-color: #333; padding: 2px 10px;">'
            'Controls: +/- adjust time range, 1-3 select pair, R toggle recording</span>'
            '</div>'
        )
        
        print("Recording controls added - Press R or click 'Start Recording' button to toggle recording")
    
    def toggle_recording(self):
        """Toggle recording on/off"""
        if not hasattr(self, 'data_recorder') or self.data_recorder is None:
            print("Error: No data recorder connected")
            return
            
        if not self.data_recorder.is_recording():
            # Start recording
            if self.data_recorder.start_recording():
                self.recording_indicator.setHtml(
                    '<div style="text-align: center">'
                    '<span style="color: #FFF; background-color: #700; padding: 3px 10px;">RECORDING: ON</span>'
                    '</div>'
                )
                self.record_button.setText("Stop Recording")
                self.record_button.setStyleSheet("""
                    QPushButton {
                        background-color: #700;
                        color: white;
                        border: 1px solid #a00;
                        padding: 5px;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #900;
                    }
                    QPushButton:pressed {
                        background-color: #b00;
                    }
                """)
                print("Recording started")
        else:
            # Stop recording
            if self.data_recorder.stop_recording():
                self.recording_indicator.setHtml(
                    '<div style="text-align: center">'
                    '<span style="color: #FFF; background-color: #333; padding: 3px 10px;">RECORDING: OFF</span>'
                    '</div>'
                )
                self.record_button.setText("Start Recording")
                self.record_button.setStyleSheet("""
                    QPushButton {
                        background-color: #2a2a2a;
                        color: white;
                        border: 1px solid #444;
                        padding: 5px;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #3a3a3a;
                    }
                    QPushButton:pressed {
                        background-color: #555;
                    }
                """)
                print("Recording stopped")
    
    def start(self):
        """Start the visualization"""
        self.app.exec_()
