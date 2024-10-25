"""
HUBB
----
\ recibe datos de:
    0. 2-3 SENSORES

\ envia datos a:
    I. Less.AUDIO           -- PULSE train
    V. Less.AUDIO           -- CLASS train    

    II. Feli.PANTALLAS      -- PULSE train
    III. Feli.PROY          -- RAW signal    
    VI. Feli.PROY           -- CLASS train

------
no jal'o, muchos retrasos
////


send to multiple clients from sensors


"""



import queue
from oscpy.server import OSCThreadServer
from oscpy.client import OSCClient
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from time import time

def handle_r1(*values):
    #print(f"/r1: {values}")
    client.send_message(b'/r1', values)
def handle_r2(*values):
    #print(f"/r2: {values}")
    client.send_message(b'/r2', values)
def handle_r3(*values):
    #print(f"/r3: {values}")
    client.send_message(b'/r3', values)

def handle_b1(*values):
    #print(f"/b1: {values}")
    client.send_message(b'/b1', values)
def handle_b2(*values):
    #print(f"/b2: {values}")
    client.send_message(b'/b2', values)
def handle_b3(*values):
    #print(f"/b3: {values}")
    client.send_message(b'/b3', values)



def setup_osc_server():
    server = OSCThreadServer()
    socket = server.listen(address='0.0.0.0', port=8000, default=True)
    
    # Routes for the first group
    #server.bind(b'/r1', handle_r1, socket)
    #server.bind(b'/r2', handle_r2, socket)
    #server.bind(b'/r3', handle_r3, socket)
    
    # Routes for the second group
    server.bind(b'/b1', handle_b1, socket)
    server.bind(b'/b2', handle_b2, socket)
    server.bind(b'/b3', handle_b3, socket)

    return server

def setup_osc_client():
    # Assuming the host and port to forward are known
    client = OSCClient('192.168.0.105', 8001)
    return client

# Initialize OSC server and client
osc_server = setup_osc_server()
osc_server.listen()
client = setup_osc_client()

# Keep the server running
try:
    while True:
        pass
except KeyboardInterrupt:
    print("Server shutdown.")


# 0 mins inicio
# 4 mins cargar bebe
# 8 mins movimientos
# 10 mins ending


