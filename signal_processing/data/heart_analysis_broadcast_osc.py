from oscpy.server import OSCThreadServer
from oscpy.client import OSCClient
import time
from collections import defaultdict


OSC_CLIENT_HOST = 'localhost'
OSC_CLIENT_PORT = 9000


# Store the last beat timestamps and the previous beat timestamps for each channel
last_beat_timestamps = defaultdict(lambda: None)
previous_beat_timestamps = defaultdict(lambda: None)

# OSC client setup
osc_client = OSCClient(OSC_CLIENT_HOST, OSC_CLIENT_PORT)  # Update with the target address and port


def log_beat(channel, values):
    current_time = time.time_ns() // 1_000_000  # Millisecond precision
    #current_time = int(time.time() * 1000)      # milliseconds int time
    if values[0] == 1:
        if last_beat_timestamps[channel] is not None:
            elapsed_time = current_time - last_beat_timestamps[channel]
        else:
            elapsed_time = None
        # update the registers
        previous_beat_timestamps[channel] = last_beat_timestamps[channel]
        last_beat_timestamps[channel] = current_time
        # do the calculation        
        calculate_and_broadcast_differences(channel)
    else:
        elapsed_time = None


# diffs between base signal and the other
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
                    # this is the difference between reference and each channel
                    time_diff = channel_time - reference_time
                    # SEND IT
                    osc_client.send_message(f'/diff/c{channel}', [time_diff])
                    print(f"Time difference between channel {channel} and {reference_channel}: {time_diff} ms")
        
        # Also send individual time difference for the current channel
        if previous_beat_timestamps[current_channel] is not None:
            individual_diff = last_beat_timestamps[current_channel] - previous_beat_timestamps[current_channel]
            osc_client.send_message(f'/individual_diff/c{current_channel}', [individual_diff])
            print(f"Individual time difference for channel {current_channel}: {individual_diff} ms")

def reco1(*values):
    log_beat(1, values)

def reco2(*values):
    log_beat(2, values)

def reco3(*values):
    log_beat(3, values)

def reco4(*values):
    log_beat(4, values)

# OSC server
server = OSCThreadServer()
socket = server.listen(address="0.0.0.0", port=8000, default=True)
server.bind(b'/c1', reco1, socket)
server.bind(b'/c2', reco2, socket)
server.bind(b'/c3', reco3, socket)
server.bind(b'/c4', reco4, socket)
server.listen()
print(f"[osc] listening on: {server.getaddress()}")

# Keep the script running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopped.")
