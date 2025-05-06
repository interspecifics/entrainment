from machine import Pin, ADC
from time import sleep, ticks_ms, ticks_diff
from uosc.client import Client, Bundle
from neopixel import NeoPixel
import gc
import json

# Configuration class for better parameter management
class Config:
    def __init__(self):
        self.id = 1
        self.advolt = 6500
        self.osc_servers = [
            {'ip': '192.168.1.81', 'port': 8001},
            {'ip': '192.168.1.81', 'port': 8002}
        ]
        self.wifi = {
            'ssid': "aa_aa",
            'password': "elbichojake"
        }
        self.sampling_rate = 500  # Hz
        self.buffer_size = 8  # Reduced from 10 for better performance
        self.alpha = 0.1
        self.hp_filter_alpha = 0.02
        self.k = 3
        self.refractory_period_ms = 350
        self.scale = 1000  # For fixed-point arithmetic
        self.threshold = -0.15
        self.ignore_window = 15

# QRS Detection class for better organization
class QRSDetector:
    def __init__(self, config):
        self.config = config
        self.pot = ADC(Pin(4))
        self.pot.atten(ADC.ATTN_11DB)
        
        # Initialize signal processing variables
        self.previous_pot_value = self.pot.read()
        self.previous_filtered_signal = 0
        self.ema_baseline = self.previous_pot_value
        self.ema_baseline_2 = self.ema_baseline
        self.ema_abs_derivative = 0
        self.last_beat_time = ticks_ms() - config.refractory_period_ms
        self.signal_level = 0
        self.noise_level = 0
        self.average_rr_interval = 1000
        
        # Initialize buffers
        self.signal_buffer = [0] * config.buffer_size
        self.buffer_index = 0
        self.past_signals = []
        self.past_mean_sum = 0
        
        # Initialize network clients
        self.osc_clients = []
        self.setup_network()
        
        # Initialize LED
        self.setup_led()
        
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
    
    def process_signal(self, pot_value):
        """Process ECG signal with optimized QRS detection"""
        # High-pass filter (two-stage)
        self.ema_baseline = (self.config.hp_filter_alpha * pot_value + 
                           (1 - self.config.hp_filter_alpha) * self.ema_baseline)
        filtered_signal = pot_value - self.ema_baseline
        self.ema_baseline_2 = (self.config.hp_filter_alpha * filtered_signal + 
                             (1 - self.config.hp_filter_alpha) * self.ema_baseline_2)
        filtered_signal = filtered_signal - self.ema_baseline_2
        
        # Update circular buffer
        self.signal_buffer[self.buffer_index] = filtered_signal
        self.buffer_index = (self.buffer_index + 1) % self.config.buffer_size
        
        # Compute derivative (optimized Pan-Tompkins)
        derivative = (2 * filtered_signal + 
                     self.signal_buffer[(self.buffer_index - 1) % self.config.buffer_size] - 
                     self.signal_buffer[(self.buffer_index - 3) % self.config.buffer_size] - 
                     2 * self.signal_buffer[(self.buffer_index - 4) % self.config.buffer_size]) // 8
        
        # Square the derivative (fixed-point arithmetic)
        squared_derivative = (derivative * derivative) // self.config.scale
        
        # Moving window integration (optimized)
        integrator = sum(self.signal_buffer) // self.config.buffer_size
        
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
    
    def send_data(self, beat_detected, pot_value, filtered_signal):
        """Send data to all OSC clients with optimized bundle"""
        bundle = Bundle()
        
        # Add beat detection message
        if beat_detected:
            bundle.add(f"/c{self.config.id}", 1, pot_value, filtered_signal)
            bundle.add(f"/g{self.config.id}", 1)
        else:
            bundle.add(f"/c{self.config.id}", 0, pot_value, filtered_signal)
        
        # Send bundle to all clients
        for client in self.osc_clients:
            try:
                client.send(bundle)
            except Exception as e:
                print(f"Error sending to {client}: {e}")
    
    def run(self):
        """Main processing loop"""
        gc_beat_counter = 0
        ignore_counter = 0
        
        while True:
            try:
                pot_value = self.pot.read()
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
                
                sleep(1 / self.config.sampling_rate)
                
            except Exception as e:
                print('Error in main loop:', e)
                sleep(1)  # Wait before retrying

# Main execution
if __name__ == "__main__":
    config = Config()
    detector = QRSDetector(config)
    detector.run() 