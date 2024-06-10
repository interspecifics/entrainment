"""
buffer stream sample counting version
"""

import queue
from oscpy.server import OSCThreadServer
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from time import time

nams=['Beat detection','Raw ECG','Moving Average']

past_ts = [[0 for i in range(5)] for j in range(4)]
ts = [0 for _ in range(4)]

d0 = [0 for _ in range(4)]
t0s = [0 for _ in range(4)]
t1s = [0 for _ in range(4)]
d0s = [[0 for i in range(5)] for j in range(4)]
bpms = [0 for _ in range(4)]
bpmsm = [0 for _ in range(4)]

def handler_c1(*args):
    try:
        vals_c1 = [float(arg) for arg in args[0:3]]  # Assuming the values are floats
        for i, v_c1 in enumerate(vals_c1):
            queues_c1[i].put(v_c1)
            if queues_c1[i].qsize() > MAX_QUEUE_SIZE:
                queues_c1[i].get()  # Remove the oldest value if queue is full
        #count
        if vals_c1[0] == 1:
            t1s[0] = time()
            d0[0] = t1s[0] - t0s[0]
            #print("C1.T: {}, C1.TM:{}".format(d0s[0], ))
            d0s[0].append(d0[0])
            d0s[0] = d0s[0][1:]
            mb1 = 0.00001 + sum(d0s[0])/len(d0s[0])
            bpms[0] = 60/d0[0]
            bpmsm[0] = 60.0/mb1
            #print("C1.T: {:.6f}, C1.BPM:{:.2f}, C1.BPM_M:{:.2f}".format( d0[0], bpms[0], bpmsm[0]))
    except (ValueError, IndexError):
        print(f"Received invalid value: {args}")

def handler_c2(*args):
    try:
        vals_c2 = [float(arg) for arg in args[0:3]]  # Assuming the values are floats
        for i, v_c2 in enumerate(vals_c2):
            queues_c2[i].put(v_c2)
            if queues_c2[i].qsize() > MAX_QUEUE_SIZE:
                queues_c2[i].get()  # Remove the oldest value if queue is full
        #count
        if vals_c2[0] == 1:
            t1s[1] = time()
            d0[1] = t1s[1] - t0s[1]
            t0s[1] = t1s[1]
            #print("C1.T: {}, C1.TM:{}".format(d0s[0], ))
            d0s[1].append(d0[1])
            d0s[1] = d0s[1][1:]
            mb2 = 0.00001 + sum(d0s[1])/len(d0s[1])
            bpms[1] = 60/d0[1]
            bpmsm[1] = 60.0/mb2
            #print("C2.T: {:.6f}, C2.BPM:{:.2f}, C2.BPM_M:{:.2f}".format( d0[1], bpms[1], bpmsm[1]))
    except (ValueError, IndexError):
        print(f"Received invalid value: {args}")

def handler_c3(*args):
    #global past_ts, tsq
    try:
        vals_c3 = [float(arg) for arg in args[0:3]]  # Assuming the values are floats
        for i, v_c3 in enumerate(vals_c3):
            queues_c3[i].put(v_c3)
            if queues_c3[i].qsize() > MAX_QUEUE_SIZE:
                queues_c3[i].get()  # Remove the oldest value if queue is full
        #count
        if vals_c3[0] == 1:
            t1s[2] = time()
            d0[2] = t1s[2] - t0s[2]
            t0s[2] = t1s[2]
            #print("C1.T: {}, C1.TM:{}".format(d0s[0], ))
            d0s[2].append(d0[2])
            d0s[2] = d0s[2][1:]
            mb3 = 0.00001 + sum(d0s[2])/len(d0s[2])
            bpms[2] = 60/d0[2]
            bpmsm[2] = 60.0/mb3
            #print("C3.T: {:.6f}, C3.BPM:{:.2f}, C3.BPM_M:{:.2f}".format( d0[2], bpms[2], bpmsm[2]))
    except (ValueError, IndexError):
        print(f"Received invalid value: {args}")

def handler_c4(*args):
    try:
        vals_c4 = [float(arg) for arg in args[0:3]]  # Assuming the values are floats
        for i, v_c4 in enumerate(vals_c4):
            queues_c4[i].put(v_c4)
            if queues_c4[i].qsize() > MAX_QUEUE_SIZE:
                queues_c4[i].get()  # Remove the oldest value if queue is full
        #count
        if vals_c4[0] == 1:
            t1s[3] = time()
            d0[3] = t1s[3] - t0s[3]
            t0s[3] = t1s[3]
            #print("C1.T: {}, C1.TM:{}".format(d0s[0], ))
            d0s[3].append(d0[3])
            d0s[3] = d0s[3][1:]
            mb4 = 0.00001 + sum(d0s[3])/len(d0s[3])
            bpms[3] = 0.00001 + 60/d0[3]
            bpmsm[3] = 60.0/mb4
            #print("C4.T: {:.6f}, C4.BPM:{:.2f}, C4.BPM_M:{:.2f}".format( d0[3], bpms[3], bpmsm[3]))
    except (ValueError, IndexError):
        print(f"Received invalid value: {args}")


def update_plot(frame):
    lines = []
    for i in range(3):
        while not queues_c1[i].empty():
            latest_v_c1 = queues_c1[i].get()
            vals_c1[i].append(latest_v_c1)
            if len(vals_c1[i]) > MAX_QUEUE_SIZE:
                vals_c1[i].pop(0)  # Remove the old vals if list exceeds max size
        while not queues_c2[i].empty():
            latest_v_c2 = queues_c2[i].get()
            vals_c2[i].append(latest_v_c2)
            if len(vals_c2[i]) > MAX_QUEUE_SIZE:
                vals_c2[i].pop(0)  # Remove the old vals if list exceeds max size
        while not queues_c3[i].empty():
            latest_v_c3 = queues_c3[i].get()
            vals_c3[i].append(latest_v_c3)
            if len(vals_c3[i]) > MAX_QUEUE_SIZE:
                vals_c3[i].pop(0)  # Remove the old vals if list exceeds max size
        while not queues_c4[i].empty():
            latest_v_c4 = queues_c4[i].get()
            vals_c4[i].append(latest_v_c4)
            if len(vals_c4[i]) > MAX_QUEUE_SIZE:
                vals_c4[i].pop(0)  # Remove the old vals if list exceeds max size
        ax[i].clear()
        ax[i].plot(vals_c1[i], linestyle='-', color='r')
        ax[i].plot(vals_c2[i], linestyle='-', color='g')
        ax[i].plot(vals_c3[i], linestyle='-', color='b')
        ax[i].plot(vals_c4[i], linestyle='-', color='k')
        ax[i].set_title(f"{nams[i]}> T:{d0[3]:.4f}, bpm:{bpms[3]:.2f}, mbpm:{bpmsm[3]:.2f}")
        #ax[i].set_xlabel("BufferPos")
        #ax[i].set_ylabel("Value")
        lines.append(ax[i])

if __name__ == "__main__":
    MAX_QUEUE_SIZE = 200
    queues_c1 = [queue.Queue(maxsize=MAX_QUEUE_SIZE) for _ in range(3)]
    vals_c1 = [[] for _ in range(3)]
    queues_c2 = [queue.Queue(maxsize=MAX_QUEUE_SIZE) for _ in range(3)]
    vals_c2 = [[] for _ in range(3)]
    queues_c3 = [queue.Queue(maxsize=MAX_QUEUE_SIZE) for _ in range(3)]
    vals_c3 = [[] for _ in range(3)]
    queues_c4 = [queue.Queue(maxsize=MAX_QUEUE_SIZE) for _ in range(3)]
    vals_c4 = [[] for _ in range(3)]

    # osc server
    server = OSCThreadServer()
    socket = server.listen(address="0.0.0.0", port=8000, default=True)
    server.bind(b'/r1', handler_c1, socket)
    server.bind(b'/r2', handler_c2, socket)
    server.bind(b'/r3', handler_c3, socket)
    server.bind(b'/r4', handler_c4, socket)
    server.listen()

    # Set up the real-time plot
    fig, ax = plt.subplots(3, 1, figsize = (16, 9))  # Create 3 subplots for 3 signals
    #plt.figtext(200, 100, "Period: {}".format(ts[2]))
    ani = animation.FuncAnimation(fig, update_plot, interval=10, cache_frame_data=False)  # Update every 10 ms

    plt.show()  # Display the plot