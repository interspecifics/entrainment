
**interspecifics**
# entrainment: ecg wifi device


## 1. Updating firmware on ESP32-S2-DevKitC

    0. download latest micropython ESP32 bin file from [micropython](https://micropython.org/download/?port=esp32) 
        Save it to a known location.

    a. install esptool python module
        + $ pip install esptool
        + $ python -m esptool

    b. erase and load micropython firmware on ESP32-S2-DevKitC
        I.  while holding the boot button, connect the ESP32 via usb and run the following:
            $ python -m esptool --chip esp32 erase_flash
        II. flash the new firmware with:
            $ python -m esptool --chip esp32 --port COM6 write_flash -z 0x1000 /firmware/ESP32_GENERIC_S2-20240222-v1.22.2.bin
            replacing the corresponding port name and file path
        III. reference:
            [flashing micropython](https://randomnerdtutorials.com/flashing-micropython-firmware-esptool-py-esp32-esp8266/)

    c. connect to thonny
        i. Install thonny, download it from: https://thonny.org/
        ii. Follow the instructions to connect the device as on: 
            [micropython on esp32](https://randomnerdtutorials.com/getting-started-thonny-micropython-python-ide-esp32-esp8266/)

    d. programming the ESP32-S2-DevKitC
        i. Load the /micropython/main.py file in thonny
        ii. Replace the following lines:
                osc_ip = '192.168.1.84'
                osc_port = 8000
                osc_ip2 = '192.168.1.96'
                osc_port2 = 8001
            and:
                ssid = "network"
                passw = "87654321"
            in case of more than one device on same server also assign different ids (1-4) on line:
                id = 4
        iii. OSC Reception:
            osc host 1 receive the full signal 100 messages/second
            osc host 2 receive only a pulse for each heartbeat, variable rate
        iv. Save the file on the board as main.py
        v.  Run or disconnect from pc and run


## 2. Breakout Board

    It contains a voltage regulator and a voltage divider circuit to operate with the bitalino sensor:
    Reference for the sensor:
        [bitalino ecg sensor](https://www.bitalino.com/storage/uploads/media/revolution-ecg-sensor-datasheet-revb-1.pdf)


![image](ecg_device/hardware/entrainment_bb.png)
