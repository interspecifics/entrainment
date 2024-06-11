from oscpy.server import OSCThreadServer
from oscpy.client import OSCClient
import time
from collections import defaultdict
import pandas as pd
from sklearn.cluster import KMeans
import pickle
import warnings

warnings.filterwarnings("ignore", category=UserWarning)


# Save last and prev beat timestamps each channel
last_beat_timestamps = defaultdict(lambda: None)
previous_beat_timestamps = defaultdict(lambda: None)


# OSC sender
osc_client_feli = OSCClient('192.168.0.105', 8001)  # Update with the target address and port
osc_client_less = OSCClient('192.168.0.103', 8002)  # Update with the target address and port


# the vectors
vector_comp = [0,0,0]
vector_self = [0,0,0]

#people#################################################################
k = 3
########################################################################

if k==2:
    kmeans = pickle.load(open("models/hearts-kmean10-2person.pkl", 'rb'))
if k==3:
    kmeans = pickle.load(open("models/hearts-kmean10-3person.pkl", 'rb'))


# 
def log_beat(channel, values):
    #
    global vector_comp, vector_self
    #
    current_time = time.time_ns() // 1_000_000  # Millisecond precision
    #current_time = int(time.time() * 1000)     # seconds milliseconds
    if values[0] == 1:
        if last_beat_timestamps[channel] is not None:
            elapsed_time = current_time - last_beat_timestamps[channel]
        else:
            elapsed_time = None
        previous_beat_timestamps[channel] = last_beat_timestamps[channel]
        last_beat_timestamps[channel] = current_time
        # time differences
        #calculate_and_broadcast_differences(channel)
        get_diffs(channel)
    else:
        elapsed_time = None


# 
def get_diffs(current_channel):
    #
    global vector_comp, vector_self
    #
    available_channels = sorted(last_beat_timestamps.keys())
    if not available_channels:
        return
    
    reference_channel = available_channels[0]
    reference_time = last_beat_timestamps[reference_channel]
    
    if reference_time is not None:
        for channel in available_channels:
            #if channel != reference_channel:
            if True:
                channel_time = last_beat_timestamps[channel]
                if channel_time is not None:
                    # this is the difference between reference channel last beat and current channel last beat
                    time_diff = channel_time - reference_time
                    # DONT SEND
                    # osc_client.send_message(f'/diff/c{channel}', [time_diff])
                    # SAVE TO VECTOR_COMP
                    if current_channel==0:
                        vector_comp[0] = time_diff/1000
                    if current_channel==1:
                        vector_comp[1] = time_diff/1000
                    if current_channel==2:
                        vector_comp[2] = time_diff/1000
                    #print(f"Time difference between channel {channel} and {reference_channel}: {time_diff} ms")
        
        # Also (dont) send individual time difference for the current channel
        if previous_beat_timestamps[current_channel] is not None:
            # this is the difference between consecutive pulses in the same channel
            individual_diff = last_beat_timestamps[current_channel] - previous_beat_timestamps[current_channel]
            # DONT SEND
            # osc_client.send_message(f'/individual_diff/c{current_channel}', [individual_diff])
            #SAVE TO VECTOR SELF
            #vector_self[current_channel-1]=int(60000/individual_diff+0.00001)
            vector_self[current_channel-1]=45000/individual_diff
            #print(f"Individual time difference for channel {current_channel}: {individual_diff} ms")


# 
def calculate_and_broadcast_differences(current_channel):
    available_channels = sorted(last_beat_timestamps.keys())
    if not available_channels:
        return
    
    reference_channel = available_channels[0]
    reference_time = last_beat_timestamps[reference_channel]
    
    if reference_time is not None:
        for channel in available_channels:
            if channel != reference_channel:
                channel_time = last_beat_timestamps[channel]
                if channel_time is not None:
                    # this is the difference between reference channel last beat and current channel last beat
                    time_diff = channel_time - reference_time
                    # DONT SEND
                    #osc_client.send_message(f'/diff/c{channel}', [time_diff])
                    print(f"Time difference between channel {channel} and {reference_channel}: {time_diff} ms")
        
        # Also (dont) send individual time difference for the current channel
        if previous_beat_timestamps[current_channel] is not None:
            # this is the difference between consecutive pulses in the same channel
            individual_diff = last_beat_timestamps[current_channel] - previous_beat_timestamps[current_channel]
            #
            #osc_client.send_message(f'/individual_diff/c{current_channel}', [individual_diff])
            print(f"Individual time difference for channel {current_channel}: {individual_diff} ms")

def reco1(*values):
    log_beat(1, values)

def reco2(*values):
    log_beat(2, values)

def reco3(*values):
    log_beat(3, values)

def reco4(*values):
    log_beat(4, values)



def classify():

    #osc_client_feli.send_message(f'/t', [0])
    #osc_client_less.send_message(f'/t', [0])
    return

# OSC server
server = OSCThreadServer()
socket = server.listen(address="0.0.0.0", port=8000, default=True)
server.bind(b'/b1', reco1, socket)
server.bind(b'/b2', reco2, socket)
server.bind(b'/b3', reco3, socket)
#server.bind(b'/b4', reco4, socket)
server.listen()
print(f"[osc] listening on: {server.getaddress()}")

# Keep the script running
try:
    while True:
        #classify()
        #print(f"VS: {vector_self}")
        #print(f"VC: {vector_comp}")
        if k==3:
            nvec = vector_comp+vector_self
        if k==2:
            nvec = vector_comp[0:2]+vector_self[0:2]
        clase = kmeans.predict([nvec])
        print(f"VVV: {nvec}, CCC:{clase}")
        fv = [int(clase[0])] + nvec
        #osc_client_feli.send_message(b'/t', fv)
        #osc_client_less.send_message(b'/t', fv)
        osc_client_feli.send_message(b'/t', [int(clase[0])])
        osc_client_less.send_message(b'/t', [int(clase[0])])
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopped.")
