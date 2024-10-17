from machine import Pin, ADC
from time import sleep, ticks_ms, ticks_diff
from uosc.client import Client
from neopixel import NeoPixel

import gc

# config params ---------------------------------------------
id = 1
advolt = 6500
#osc_ip = '192.168.0.103'
#osc_port = 8000
osc_ip = '192.168.1.81'
osc_port = 8001
osc_ip2 = '192.168.1.81'
osc_port2 = 8002

#
#ssid = "INFINITUM2064"
#passw = "wrW2kUnr94"
#ssid = "codex1"
#passw = "87654321"
ssid = "aa_aa"
passw = "elbichojake"

# osc route and led color ----------------------------------

if id==1:
    co1 = (255, 0, 0)
    co2 = (127, 0, 0)
    msg_route = "/c1"
    msg_route_g = "/g1"
elif id==2:
    co1 = (0, 255, 0)
    co2 = (0, 127, 0)
    msg_route = "/c2"
    msg_route_g = "/g2"
elif id==3:
    co1 = (0, 0, 255)
    co2 = (0, 0, 127)
    msg_route = "/c3"
    msg_route_g = "/g3"
elif id==4:
    co1 = (255, 255, 0)
    co2 = (127, 127, 0)
    msg_route = "/c4"
    msg_route_g = "/g4"
else:
    co1 = (255, 0, 255)
    co2 = (127, 0, 127)
    msg_route = "/c5"
    msg_route = "/g5"



# analog sensor reading
pot = ADC(Pin(4))
pot.atten(ADC.ATTN_11DB)       #Full range: 3.3v
# onboard pixel
pin_pix = Pin(18, Pin.OUT)
npx = NeoPixel(pin_pix, 1)
npx[0] = co1
npx.write()

# the loop
def do_connect(ssid, password, tries=150):
    from network import WLAN, STA_IF
    from time import sleep
    sta_if = WLAN(STA_IF)
    sta_if.active(False)
    
    if not sta_if.isconnected():
        sta_if.active(True)
        sta_if.connect(ssid, password)

        for i in range(tries):
            print('Connecting to network (try {})...'.format(i+1))
            if sta_if.isconnected():
                print('network config:', sta_if.ifconfig())
                break
            sleep(1)
        else:
            print("Failed to connect in {} seconds.".format(tries))
    # end do connect function

# make the connection and osc client start
do_connect(ssid, passw)
osc = Client(osc_ip, osc_port)
osc.send(msg_route + '/start', 1)
osc2 = Client(osc_ip2, osc_port2)
osc2.send(msg_route + '/start', 1)



npx[0] = (0,0,0)
npx.write()
sleep(0.2)
npx[0] = co1
npx.write()
sleep(0.2)
npx[0] = (0,0,0)
npx.write()
sleep(0.2)
npx[0] = co1
npx.write()


# Adjusted parameters
alpha = 0.15
hp_filter_alpha = 0.05
k = 2.75
refractory_period_ms = 450  # Adjust as needed

# Initialize variables
previous_pot_value = pot.read()
previous_filtered_signal = 0
ema_baseline = previous_pot_value
ema_abs_derivative = 0
last_beat_time = ticks_ms() - refractory_period_ms

gc_beat_counter = 0

# New variables for improved algorithm
window_size = 10
signal_buffer = [0] * window_size
buffer_index = 0

last_beat_intervals = [refractory_period_ms] * 5
beat_interval_index = 0

while True:
    try:
        pot_value = pot.read()

        # High-pass filter (optional)
        ema_baseline = hp_filter_alpha * pot_value + (1 - hp_filter_alpha) * ema_baseline
        filtered_signal = pot_value - ema_baseline

        # Update signal buffer for smoothing
        signal_buffer[buffer_index] = filtered_signal
        buffer_index = (buffer_index + 1) % window_size
        smoothed_signal = sum(signal_buffer) / window_size

        # Compute derivative
        derivative = smoothed_signal - previous_filtered_signal
        previous_filtered_signal = smoothed_signal

        # Absolute value of derivative
        abs_derivative = abs(derivative)

        # Update EMA of absolute derivative
        ema_abs_derivative = alpha * abs_derivative + (1 - alpha) * ema_abs_derivative

        # Compute adaptive threshold
        threshold = k * ema_abs_derivative

        # Time since last beat
        current_time = ticks_ms()
        time_since_last_beat = ticks_diff(current_time, last_beat_time)

        # Detect heartbeat if derivative exceeds threshold and outside refractory period
        if abs_derivative > threshold and time_since_last_beat > refractory_period_ms:
            # Heartbeat detected
            osc.send(msg_route, 1, pot_value)
            osc2.send(msg_route, 1)
            
            # Update beat intervals for adaptive refractory period
            current_interval = time_since_last_beat
            last_beat_intervals[beat_interval_index] = current_interval
            beat_interval_index = (beat_interval_index + 1) % 5
            
            # Calculate new adaptive refractory period
            avg_interval = sum(last_beat_intervals) / len(last_beat_intervals)
            refractory_period_ms = max(int(avg_interval * 0.6), 200)  # Minimum 200ms
            
            last_beat_time = current_time  # Reset refractory period
            
            if gc_beat_counter > 10:
                gc.collect()
                gc_beat_counter = 0
            else:
                gc_beat_counter += 1
            
        else:
            osc.send(msg_route, 0, pot_value)

        # Compute SNR (simple ratio)
        signal_power = ema_abs_derivative
        noise_power = abs_derivative  # Assuming current derivative represents noise
        snr = signal_power / (noise_power + 1e-6)  # Avoid division by zero

        # Dynamically adjust `k`
        if snr > 1.5:
            k = max(1.5, k - 0.05)  # Decrease k if signal is clean, but not below 2.5
        elif snr < 1.0:
            k = min(4.5, k + 0.05)  # Increase k if signal is noisy, but not above 3.5
        else:
            k = 2.75  # Default value

        sleep(0.002)
    except Exception as e:
        print('Something went wrong [x.x]', e)


