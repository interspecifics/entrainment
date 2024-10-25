from machine import Pin, ADC
from time import sleep, time, ticks_ms, ticks_diff
from uosc.client import Bundle, Client, create_message
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
alpha = 0.1
hp_filter_alpha = 0.02
k = 3
refractory_period_ms = 350

# Initialize variables
previous_pot_value = pot.read()
previous_filtered_signal = 0
ema_baseline = previous_pot_value
ema_baseline_2 = ema_baseline
ema_abs_derivative = 0
last_beat_time = ticks_ms() - refractory_period_ms
signal_level = 0
noise_level = 0
average_rr_interval = 1000  # Initial guess, will be updated
gc_beat_counter = 0

# Constants for fixed-point arithmetic
SCALE = 1000

# Circular buffer for signal
BUFFER_SIZE = 10
signal_buffer = [0] * BUFFER_SIZE
buffer_index = 0

while True:
    try:
        pot_value = pot.read()

        # High-pass filter (two-stage)
        ema_baseline = hp_filter_alpha * pot_value + (1 - hp_filter_alpha) * ema_baseline
        filtered_signal = pot_value - ema_baseline
        ema_baseline_2 = hp_filter_alpha * filtered_signal + (1 - hp_filter_alpha) * ema_baseline_2
        filtered_signal = filtered_signal - ema_baseline_2

        # Update circular buffer
        signal_buffer[buffer_index] = filtered_signal
        buffer_index = (buffer_index + 1) % BUFFER_SIZE

        # Compute derivative (Pan-Tompkins inspired)
        derivative = (2 * filtered_signal + signal_buffer[(buffer_index - 1) % BUFFER_SIZE] - 
                      signal_buffer[(buffer_index - 3) % BUFFER_SIZE] - 
                      2 * signal_buffer[(buffer_index - 4) % BUFFER_SIZE]) // 8

        # Square the derivative (fixed-point arithmetic)
        squared_derivative = (derivative * derivative) // SCALE

        # Moving window integration
        integrator = sum(signal_buffer) // BUFFER_SIZE

        # Update EMA of absolute derivative
        ema_abs_derivative = (alpha * abs(derivative) + (1 - alpha) * ema_abs_derivative)

        # Compute adaptive threshold
        threshold = (noise_level + (signal_level - noise_level) // 4) * k // SCALE

        # Time since last beat
        current_time = ticks_ms()
        time_since_last_beat = ticks_diff(current_time, last_beat_time)

        # Adaptive threshold based on time since last beat
        if time_since_last_beat > average_rr_interval * 3 // 2:
            threshold = threshold * 2 // 3  # Lower threshold to catch missed beats

        # Beat detection with width validation
        if squared_derivative > threshold:
            if time_since_last_beat > refractory_period_ms:
                # Potential beat detected
                beat_detected = True
                signal_level = (integrator + 7 * signal_level) // 8
                last_beat_time = current_time

                # Update average RR interval
                rr_interval = time_since_last_beat
                average_rr_interval = (rr_interval + 7 * average_rr_interval) // 8

                # Send beat detection signal
                osc.send(msg_route, 1, pot_value)
                osc2.send(msg_route, 1)

                # Garbage collection
                gc_beat_counter += 1
                if gc_beat_counter > 10:
                    gc.collect()
                    gc_beat_counter = 0
            else:
                beat_detected = False
        else:
            beat_detected = False
            noise_level = (integrator + 7 * noise_level) // 8

        # Send continuous signal
        if not beat_detected:
            osc.send(msg_route, 0, pot_value)

        # Compute SNR and adjust parameters
        snr = signal_level // (noise_level + 1)
        if snr > SCALE * 3 // 2:
            k = 5 * SCALE // 2
        elif snr < SCALE:
            k = 7 * SCALE // 2
        else:
            k = 3 * SCALE

        sleep(0.002)
    except Exception as e:
        print('Something went wrong [x.x]', e)