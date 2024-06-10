from machine import Pin, ADC
from time import sleep, time
from uosc.client import Bundle, Client, create_message
from neopixel import NeoPixel

# config params ---------------------------------------------
id = 1
advolt = 6500
#osc_ip = '192.168.0.103'
#osc_port = 8000
osc_ip = '192.168.0.104'
osc_port = 8000
osc_ip2 = '192.168.0.104'
osc_port2 = 8000

#
#ssid = "INFINITUM2064"
#passw = "wrW2kUnr94"
#ssid = "codex1"
#passw = "87654321"

#ssid = "000_000"
#passw = "elbichojake"
ssid = "TP-Link_F048"
passw = "46573629"



# osc route and led color ----------------------------------

if id==1:
    co1 = (255, 0, 0)
    co2 = (127, 0, 0)
    msg_route = "/r1"
    msg_route_b = "/b1"
elif id==2:
    co1 = (0, 255, 0)
    co2 = (0, 127, 0)
    msg_route = "/r2"
    msg_route_b = "/b2"
elif id==3:
    co1 = (0, 0, 255)
    co2 = (0, 0, 127)
    msg_route = "/r3"
    msg_route_b = "/b3"
elif id==4:
    co1 = (255, 255, 0)
    co2 = (127, 127, 0)
    msg_route = "/r4"
    msg_route_b = "/b4"
else:
    co1 = (255, 0, 255)
    co2 = (127, 0, 127)
    msg_route = "/r5"
    msg_route_b = "/b5"



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


def moving_average_detection(ecg_signal, past_signals, past_mean_sum, n=30, threshold=-0.1):
    """
    Analyze ECG signal to detect heart beat by looking at the pondered signal diferential.

    This function calculates a processed value by comparing the current ECG signal data 
    point to the moving average of the last `n` data points in the past_signals list. 
    The moving average is adjusted dynamically with each new data point. 
    A processed value is deemed significant and indicative of a potential heart event 
    if it is below a predefined `threshold`.
    
    The algorithm is complexity O(1)  :)

    Args:
    ecg_signal (float): The current ECG signal data point.
    past_signals (list of float): A historical list of ECG signal data points.
    past_mean_sum (float): The cumulative sum of the last `n` ECG signals, used to compute the moving average efficiently.
    n (int): The number of data points to consider in the moving average.
    threshold (float): The critical value below which a signal is considered significantly deviant.

    Returns:
    float: The normalized deviation of the current signal from the moving average.
    bool: A flag indicating whether the deviation is significant (True if below the threshold).
    """
    
    if len(past_signals) < n:
        past_mean_sum += ecg_signal
        past_signals.append(ecg_signal)
        return 0, False, past_signals, past_mean_sum  # Not enough data to process

    # Update the list of past signals
    past_signals.append(ecg_signal)

    # Update the moving average sum in O(1) time complexity
    mean_past_n = float(past_mean_sum / n)
    past_mean_sum = past_mean_sum - past_signals[0] + past_signals[-1]

    if len(past_signals) > n:
        past_signals.pop(0)

    # Calculate the difference from the last signal
    signal_diff = ecg_signal - past_signals[-2]
    processed_value = float(signal_diff / mean_past_n) if mean_past_n != 0 else 0

    # Check if the processed value is below the threshold
    is_heart_beat = processed_value < threshold

    return processed_value, is_heart_beat, past_signals, past_mean_sum


# variables for processing algorithm
past_signals = []
past_mean_sum = 0
ignore_window_len = 15

ignore_counter = 0

while True:
  try:
    pot_value = pot.read()

    processed_pot_val, is_heart_beat, past_signals, past_mean_sum  = moving_average_detection(pot_value, past_signals, past_mean_sum, n=30, threshold=-0.15)

    if (is_heart_beat and ignore_counter == 0):
      osc.send(msg_route, 1, pot_value, processed_pot_val)
      osc2.send(msg_route_b, 1)
      ignore_counter = ignore_window_len # reinitialize counter
    else:
      osc.send(msg_route, 0, pot_value, processed_pot_val)
      if ignore_counter > 0:
         ignore_counter = ignore_counter - 1 # reduce counter

    sleep(0.002)
  except Exception as e:
      print('somethon gone bad [x.x]',e)
#"""
