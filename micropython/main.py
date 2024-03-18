from machine import Pin, ADC
from time import sleep, time
from uosc.client import Bundle, Client, create_message
from neopixel import NeoPixel

# config params ---------------------------------------------
id = 2
advolt = 6500
osc_ip = '192.168.1.84'
osc_port = 8000
#osc_ip2 = '192.168.0.105'
#osc_port2 = 8000

#
#ssid = "INFINITUM2064"
#passw = "wrW2kUnr94"
#ssid = "codex1"
#passw = "87654321"
ssid = "000_000"
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
#osc2 = Client(osc_ip2, osc_port2)
#osc2.send(msg_route + '/start', 1)



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
isup = 0

past = 0
t0 = time()
pot_value = 0
#
#while True:
#  osc.send(msg_route, 1)      
#  sleep(0.25)
  
#"""
while True:
  try:
    past = pot_value
    pot_value = pot.read()
    derivada = pot_value - past
    print(pot_value)
    #osc.send(msg_route_g, pot_value)      
    #osc2.send(msg_route_g, pot_value)
    #t1 = time() - t0
    if (pot_value > 5900 and isup == 0):
      osc.send(msg_route, 1, pot_value)
      #osc2.send(msg_route, 1)
      #t0 = time()
      isup = 1
      sleep(0.025)
    else:
      osc.send(msg_route, 0, pot_value)
    if (pot_value < 5300 and isup == 1):
      #osc.send(msg_route, 0)
      #osc2.send(msg_route, 0)
      isup = 0

    #else:
    #    osc.send(msg_route, 0)
    #sleep(0.01)
  except:
      print('somethon gone bad [x.x]')
#"""
