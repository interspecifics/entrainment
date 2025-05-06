from machine import Pin, ADC, Timer
from time import sleep, ticks_ms, ticks_diff, ticks_us, time
from uosc.client import Client, Bundle
from neopixel import NeoPixel
import gc
import json
import array
import math
import ntptime
from device_config import DeviceConfig
import micropython

# Enable memory monitoring
micropython.alloc_emergency_exception_buf(100)

# Configuration class for better parameter management
class Config:
    def __init__(self):
        # Load device configuration
        device_config = DeviceConfig()
        self.id = device_config.get_device_id()
        self.advolt = 6500
        self.osc_servers = device_config.get_osc_servers()
        self.wifi = device_config.get_wifi_config()
        self.ntp_config = device_config.get_ntp_config()
        self.sampling_rate = 500  # Hz
        self.buffer_size = 32  # Power of 2 for efficient modulo operations
        self.alpha = 0.1
        self.hp_filter_alpha = 0.02
        self.k = 3
        self.refractory_period_ms = 350
        self.scale = 1000  # For fixed-point arithmetic
        self.threshold = -0.15
        self.ignore_window = 15
        self.sync_interval = 1000  # Sync interval in ms
        self.signal_quality_window = 50  # Window size for signal quality metrics
        self.min_signal_amplitude = 100  # Minimum amplitude for valid signal
        self.max_signal_amplitude = 3000  # Maximum amplitude for valid signal
        self.time_offset = 0  # Offset between local and NTP time
        self.gc_threshold = 10000  # Memory threshold for garbage collection

# Ring Buffer implementation for efficient sampling
class RingBuffer:
    def __init__(self, size):
        self.size = size
        self.buffer = array.array('i', [0] * size)  # Using array for better memory efficiency
        self.head = 0
        self.tail = 0
        self.count = 0
        self.lock = False  # Simple lock mechanism
    
    def is_full(self):
        return self.count == self.size
    
    def is_empty(self):
        return self.count == 0
    
    def push(self, value):
        if not self.is_full():
            self.buffer[self.head] = value
            self.head = (self.head + 1) & (self.size - 1)  # Fast modulo for power of 2
            self.count += 1
            return True
        return False
    
    def pop(self):
        if not self.is_empty():
            value = self.buffer[self.tail]
            self.tail = (self.tail + 1) & (self.size - 1)  # Fast modulo for power of 2
            self.count -= 1
            return value
        return None

# QRS Detection class with timer-based sampling
class QRSDetector:
    def __init__(self, config):
        self.config = config
        self.pot = ADC(Pin(4))
        self.pot.atten(ADC.ATTN_11DB)
        
        # Initialize ring buffer for sampling
        self.sample_buffer = RingBuffer(config.buffer_size)
        
        # Initialize signal processing variables
        self.previous_filtered_signal = 0
        self.ema_baseline = 0
        self.ema_baseline_2 = 0
        self.ema_abs_derivative = 0
        self.last_beat_time = ticks_ms() - config.refractory_period_ms
        self.signal_level = 0
        self.noise_level = 0
        self.average_rr_interval = 1000
        
        # Time synchronization
        self.last_ntp_sync = 0
        self.time_offset = 0
        
        # Signal quality metrics
        self.signal_quality_buffer = array.array('i', [0] * config.signal_quality_window)
        self.signal_quality_index = 0
        self.signal_quality_sum = 0
        self.signal_quality_count = 0
        
        # Initialize processing buffer
        self.processing_buffer = array.array('i', [0] * 8)
        self.buffer_index = 0
        
        # Initialize network clients
        self.osc_clients = []
        self.setup_network()
        
        # Initialize LED
        self.setup_led()
        
        # Initialize timer for sampling
        self.sampling_timer = Timer(0)
        self.last_sync_time = ticks_ms()
        
        # Memory monitoring
        self.last_memory_check = ticks_ms()
        self.memory_warning_threshold = 100000  # 100KB
        
        # Initial NTP sync
        self.sync_ntp_time()
        
    def setup_network(self):
        """Setup network connection and OSC clients"""
        from network import WLAN, STA_IF
        sta_if = WLAN(STA_IF)
        sta_if.active(False)
        
        if not sta_if.isconnected():
            sta_if.active(True)
            sta_if.connect(self.config.wifi['ssid'], self.config.wifi['password'])
            
            for _ in range(150):
                if sta_if.isconnected():
                    print('Network config:', sta_if.ifconfig())
                    break
                sleep(1)
        
        # Initialize OSC clients
        for server in self.config.osc_servers:
            client = Client(server['ip'], server['port'])
            client.send(f"/c{self.config.id}/start", 1)
            self.osc_clients.append(client)
    
    def setup_led(self):
        """Setup LED with device-specific color"""
        self.pin_pix = Pin(18, Pin.OUT)
        self.npx = NeoPixel(self.pin_pix, 1)
        
        # Set LED color based on device ID
        colors = {
            1: ((255, 0, 0), (127, 0, 0)),
            2: ((0, 255, 0), (0, 127, 0)),
            3: ((0, 0, 255), (0, 0, 127)),
            4: ((255, 255, 0), (127, 127, 0)),
            5: ((255, 0, 255), (127, 0, 127))
        }
        self.co1, self.co2 = colors.get(self.config.id, ((255, 0, 255), (127, 0, 127)))
        self.npx[0] = self.co1
        self.npx.write()
    
    def check_memory(self):
        """Check memory usage and trigger GC if needed"""
        current_time = ticks_ms()
        if ticks_diff(current_time, self.last_memory_check) > 5000:  # Check every 5 seconds
            self.last_memory_check = current_time
            free_memory = gc.mem_free()
            if free_memory < self.memory_warning_threshold:
                print(f"Low memory warning: {free_memory} bytes free")
                gc.collect()
                print(f"After GC: {gc.mem_free()} bytes free")
    
    def sampling_isr(self, timer):
        """Timer ISR for sampling ECG signal"""
        if not self.sample_buffer.lock:
            self.sample_buffer.lock = True
            try:
                value = self.pot.read()
                if not self.sample_buffer.push(value):
                    print("Buffer full, sample dropped")
            finally:
                self.sample_buffer.lock = False
    
    def process_signal(self, pot_value):
        """Process ECG signal with optimized QRS detection"""
        # High-pass filter (two-stage)
        self.ema_baseline = (self.config.hp_filter_alpha * pot_value + 
                           (1 - self.config.hp_filter_alpha) * self.ema_baseline)
        filtered_signal = pot_value - self.ema_baseline
        self.ema_baseline_2 = (self.config.hp_filter_alpha * filtered_signal + 
                             (1 - self.config.hp_filter_alpha) * self.ema_baseline_2)
        filtered_signal = filtered_signal - self.ema_baseline_2
        
        # Update processing buffer
        self.processing_buffer[self.buffer_index] = filtered_signal
        self.buffer_index = (self.buffer_index + 1) & 7  # Fast modulo for power of 2
        
        # Compute derivative (optimized Pan-Tompkins)
        derivative = (2 * filtered_signal + 
                     self.processing_buffer[(self.buffer_index - 1) & 7] - 
                     self.processing_buffer[(self.buffer_index - 3) & 7] - 
                     2 * self.processing_buffer[(self.buffer_index - 4) & 7]) // 8
        
        # Square the derivative (fixed-point arithmetic)
        squared_derivative = (derivative * derivative) // self.config.scale
        
        # Moving window integration (optimized)
        integrator = sum(self.processing_buffer) // 8
        
        # Update EMA of absolute derivative
        self.ema_abs_derivative = (self.config.alpha * abs(derivative) + 
                                 (1 - self.config.alpha) * self.ema_abs_derivative)
        
        # Compute adaptive threshold
        threshold = (self.noise_level + 
                    (self.signal_level - self.noise_level) // 4) * self.config.k // self.config.scale
        
        # Time since last beat
        current_time = ticks_ms()
        time_since_last_beat = ticks_diff(current_time, self.last_beat_time)
        
        # Adaptive threshold based on time since last beat
        if time_since_last_beat > self.average_rr_interval * 3 // 2:
            threshold = threshold * 2 // 3
        
        # Beat detection with width validation
        beat_detected = False
        if squared_derivative > threshold and time_since_last_beat > self.config.refractory_period_ms:
            beat_detected = True
            self.signal_level = (integrator + 7 * self.signal_level) // 8
            self.last_beat_time = current_time
            
            # Update average RR interval
            rr_interval = time_since_last_beat
            self.average_rr_interval = (rr_interval + 7 * self.average_rr_interval) // 8
        else:
            self.noise_level = (integrator + 7 * self.noise_level) // 8
        
        return beat_detected, pot_value, filtered_signal
    
    def calculate_signal_quality(self, signal_value):
        """Calculate signal quality metrics"""
        # Update signal quality buffer
        self.signal_quality_sum -= self.signal_quality_buffer[self.signal_quality_index]
        self.signal_quality_buffer[self.signal_quality_index] = signal_value
        self.signal_quality_sum += signal_value
        self.signal_quality_index = (self.signal_quality_index + 1) % self.config.signal_quality_window
        self.signal_quality_count = min(self.signal_quality_count + 1, self.config.signal_quality_window)
        
        if self.signal_quality_count < 2:
            return 0.0
        
        # Calculate metrics
        mean = self.signal_quality_sum / self.signal_quality_count
        variance = sum((x - mean) ** 2 for x in self.signal_quality_buffer[:self.signal_quality_count]) / self.signal_quality_count
        std_dev = math.sqrt(variance)
        
        # Calculate SNR (Signal-to-Noise Ratio)
        snr = 20 * math.log10(abs(mean) / (std_dev + 1e-10)) if std_dev > 0 else 0
        
        # Calculate signal amplitude
        amplitude = max(self.signal_quality_buffer[:self.signal_quality_count]) - min(self.signal_quality_buffer[:self.signal_quality_count])
        
        # Calculate signal quality score (0-1)
        quality_score = 0.0
        
        # Check amplitude range
        if self.config.min_signal_amplitude <= amplitude <= self.config.max_signal_amplitude:
            quality_score += 0.4
        
        # Check SNR
        if snr > 10:  # Good SNR threshold
            quality_score += 0.3
        elif snr > 5:  # Acceptable SNR threshold
            quality_score += 0.15
        
        # Check signal stability
        if std_dev < 100:  # Low standard deviation indicates stable signal
            quality_score += 0.3
        
        return quality_score

    def sync_ntp_time(self):
        """Synchronize time with NTP server"""
        try:
            ntptime.host = self.config.ntp_config['server']
            ntptime.settime()
            # Calculate offset between local time and NTP time
            self.time_offset = time() - (ticks_ms() // 1000)
            self.last_ntp_sync = ticks_ms()
            print(f"Time synchronized with NTP. Offset: {self.time_offset}s")
        except Exception as e:
            print(f"NTP sync failed: {e}")

    def get_synchronized_time(self):
        """Get current time synchronized with NTP"""
        current_ms = ticks_ms()
        if current_ms - self.last_ntp_sync > self.config.ntp_config['sync_interval'] * 1000:
            self.sync_ntp_time()
        return (current_ms // 1000) + self.time_offset

    def send_data(self, beat_detected, pot_value, filtered_signal):
        """Send data to all OSC clients with optimized bundle"""
        try:
            current_time = self.get_synchronized_time()
            signal_quality = self.calculate_signal_quality(filtered_signal)
            
            # Create message with minimal memory allocation
            message = {
                'device_id': self.config.id,
                'timestamp': current_time,
                'local_ms': ticks_ms(),
                'raw_value': pot_value,
                'filtered_value': filtered_signal,
                'signal_quality': signal_quality,
                'is_beat': beat_detected,
                'rr_interval': ticks_diff(ticks_ms(), self.last_beat_time) if beat_detected else 0,
                'time_offset': self.time_offset
            }
            
            # Convert to JSON string
            message_json = json.dumps(message)
            
            # Send to all clients
            for client in self.osc_clients:
                try:
                    if beat_detected:
                        client.send(f"/beat/{self.config.id}", message_json)
                    else:
                        client.send(f"/signal/{self.config.id}", message_json)
                except Exception as e:
                    print(f"Error sending to {client}: {e}")
                    # Attempt to reconnect
                    self.setup_network()
        except Exception as e:
            print(f"Error in send_data: {e}")
            gc.collect()  # Try to recover memory
    
    def run(self):
        """Main processing loop"""
        gc_beat_counter = 0
        ignore_counter = 0
        
        # Start sampling timer
        self.sampling_timer.init(period=int(1000/self.config.sampling_rate), 
                               mode=Timer.PERIODIC, 
                               callback=self.sampling_isr)
        
        while True:
            try:
                # Check memory usage
                self.check_memory()
                
                # Process samples from buffer
                while not self.sample_buffer.is_empty():
                    pot_value = self.sample_buffer.pop()
                    beat_detected, pot_value, filtered_signal = self.process_signal(pot_value)
                    
                    # Handle beat detection with ignore window
                    if beat_detected and ignore_counter == 0:
                        self.send_data(True, pot_value, filtered_signal)
                        ignore_counter = self.config.ignore_window
                    else:
                        self.send_data(False, pot_value, filtered_signal)
                        if ignore_counter > 0:
                            ignore_counter -= 1
                
                # Garbage collection
                gc_beat_counter += 1
                if gc_beat_counter > 10:
                    gc.collect()
                    gc_beat_counter = 0
                
                # Small sleep to prevent busy waiting
                sleep(0.001)
                
            except Exception as e:
                print('Error in main loop:', e)
                gc.collect()  # Try to recover memory
                sleep(1)  # Wait before retrying

# Main execution
if __name__ == "__main__":
    try:
        # Initial garbage collection
        gc.collect()
        
        config = Config()
        detector = QRSDetector(config)
        detector.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        # Attempt to save error to flash for debugging
        try:
            with open('error_log.txt', 'a') as f:
                f.write(f"{ticks_ms()}: {str(e)}\n")
        except:
            pass
        # Reboot after a delay
        sleep(5)
        import machine
        machine.reset() 