# HANmeter
A python3 tool to read/decode/debug AMS/HAN data from smart electrical meter

This is based on aidon_obis.py from https://github.com/skagmo/meter_reading

Tested to work with Aidon and Hafslund smart meter using M-bus interfaces like 
[this one](https://www.aliexpress.com/item/32894249052.html) and 
[this one](https://www.aliexpress.com/item/32751482255.html). The first type is preferred as the serial chip is a USB-2 device with some buffering, which provides fewer packets lost on a busy system.

## Dependencies

You will need to install python3 serial and crcmod, i.e on a Raspberry Pi

    sudo apt-get install python3-serial pyhon3-crcmod

## Setup 

This is for a Raspberry Pi, but should work on any similar system

### /dev/HANserial port

I find it useful to use a /dev/HANserial device. Any serial port name will do, so this step is optional

Rules for /etc/udev/rules.d are provided in the [udev](./udev/71-HANserial.rules) rule file. Copy to /etc/udev/rules.d/71-HANserial.rules, then reboot

### HANdomo systemctl service

Before setting up as a systemctl service, please make sure things work as desciribed for Standalone use (below)

A systemctl service setup is provided in the [service](./service/HANdomo.service) systemctl service file. Copy to /lib/systemd/system/HANdomo.service
You can change some behavior options by copying the [config](./config/HANdomo) file to /etc/default/HANdomo. The DOMOIDX variables are set to 0 by default to do nothing. If you use Domoticz home automation, you can change these to update a local Domoticz kW-meter and kWh-meter device indexes as needed

To enable the service, start / enable and check progress:

    sudo systemctl daemon-reload
    sudo systemctl enable HANdomo
    sudo systemctl start HANdomo
    sudo journalctl -f -u HANdomo
	
## Standalone use

You can use the HANdomo.py as a HAN utility in a number of ways 

### Read from /dev/HANserial 

You can read from a HAN serial port and display packet hexdumps (-x), OBIS fields (-f), packet processing debug (-p) in any combination like 

    HANdomo.py -x -f -p /dev/HANserial


### Log to file and replay 

You can read from a HAN serial port and log the data to a file 

    HANdomo.py -l /tmp/packets.log /dev/HANserial

... then later replay the same data

     HANdomo.py -x -f -p /tmp/packets.log

