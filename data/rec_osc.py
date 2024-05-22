from oscpy.server import OSCThreadServer
import time, math, io, pickle, os

ls1 = []
fs1 = []
a1 = 0
ls2 = []
fs2 = []
a2 = 0
ls3 = []
fs3 = []
a3 = 0
ls4 = []
fs4 = []
a4 = 0

def reco1(*values):
    global a1, fs1, ls1
    #print (values)
    l = "{}\t{}\t{}\n".format(values[0], values[1], values[2])
    ls1.append(l)
    a1 = a1+1
    if a1%100==0:
        fs1.writelines(ls1)
        ls1.clear()
    #time.sleep(1)
    return

def reco2(*values):
    global a2, fs2, ls2
    #print (values)
    l = "{}\t{}\t{}\n".format(values[0], values[1], values[2])
    ls2.append(l)
    a2 = a2+1
    if a2%100==0:
        fs2.writelines(ls2)
        ls2.clear()
    #time.sleep(1)
    return

def reco3(*values):
    global a3, fs3, ls3
    #print (values)
    l = "{}\t{}\t{}\n".format(values[0], values[1], values[2])
    ls3.append(l)
    a3 = a3+1
    if a3%100==0:
        fs3.writelines(ls3)
        ls3.clear()
    #time.sleep(1)
    return

def reco4(*values):
    global a4, fs4, ls4
    #print (values)
    l = "{}\t{}\t{}\n".format(values[0], values[1], values[2])
    ls4.append(l)
    a4 = a4+1
    if a4%100==0:
        fs4.writelines(ls4)
        ls4.clear()
    #time.sleep(1)
    return

fs4 = open("./T10/ECG_c4.txt",'w+')
fs3 = open("./T10/ECG_c3.txt",'w+')
fs2 = open("./T10/ECG_c2.txt",'w+')
fs1 = open("./T10/ECG_c1.txt",'w+')


# osc server
server = OSCThreadServer()
socket = server.listen(address="0.0.0.0", port=8000, default=True)
#server.bind(b'/codex/',     got_message,    socket)
server.bind(b'/c1', reco1, socket)
server.bind(b'/c2', reco2, socket)
server.bind(b'/c3', reco3, socket)
server.bind(b'/c4', reco4, socket)
server.listen()
print ("[osc] listening on: {}".format(server.getaddress()))
## const init

while(a3<72000 or a4<72000):
    b=0
    print (a1,' ',a2,' ',a3,' ',a4)

fs1.close()
fs2.close()
fs3.close()
fs4.close()

