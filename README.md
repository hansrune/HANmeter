# HANmeter
A python3 tool to read/decode/debug AMS/HAN data from smart electrical meter

This is based on aidon_obis.py from https://github.com/skagmo/meter_reading

Tested to work with Aidon and Hafslund smart meter using M-bus interfaces like 
[this one](https://www.aliexpress.com/item/32894249052.html) and 
[this one](https://www.aliexpress.com/item/32751482255.html). The first type is preferred as the serial chip is a USB-2 device with some buffering, which provides fewer packets lost on a busy system.

## Dependencies

You will need to install python3 serial and crcmod, i.e on a Raspberry Pi

    sudo apt-get install python3-serial python3-crcmod

## Setup 

The implementation described here is for a Raspberry Pi, but should work on any similar system

### /dev/HANserial port

I find it useful to use a `/dev/HANserial` device as a persistent name. Any serial port name will do, so this step is optional

Rules for /etc/udev/rules.d are provided in the [udev](./udev/71-HANserial.rules) rule file. Copy to `/etc/udev/rules.d/71-HANserial.rules`, attach your device,  then reboot

### HANdomo systemctl service

Before setting up as a systemctl service, please make sure things work as desciribed for Standalone use (below)

A systemctl service setup is provided in the [service](./service/HANdomo.service) systemctl service file. Copy to `/lib/systemd/system/HANdomo.service`
You can change some behavior options by copying the [config](./config/HANdomo) file to `/etc/default/HANdomo`. The DOMOIDX variables are set to 0 by default to do nothing. If you use Domoticz home automation, you can change these to update a local Domoticz kW-meter and kWh-meter device indexes as needed

To enable the service, start / enable and check progress:

    sudo systemctl daemon-reload
    sudo systemctl enable HANdomo
    sudo systemctl start HANdomo
    sudo journalctl -f -u HANdomo
	
## Standalone use

You can use `HANdomo.py` script as a HAN utility in a number of ways 

### Read from /dev/HANserial 

You can read from a HAN serial port and display packet hexdumps (`-x`), OBIS fields (`-f`), packet processing debug (`-p`) in any combination like 

    HANdomo.py -x -f -p /dev/HANserial


### Log to file and replay 

You can read from a HAN serial port and log the binary data stream to a file. Any input path including */dev* in the name is opened and read as a serial device. Everything else assumes the input is a file.

    HANdomo.py -l /tmp/packets.log /dev/HANserial

... then later replay the same data

     HANdomo.py -x -f -p /tmp/packets.log

Replaying files captured with the utilities in the *han-port-c-lib* library also works. 

## Examples

### Output from a running service

This service instance runs with `-f` (OBIS field outputs). Domoticz is updated just every minute or so 

    $ journalctl -f -u HANdomo
    Mar 15 11:10:21 xxxx-pi1 python3[599]: act_pow_neg = 0
    Mar 15 11:10:21 xxxx-pi1 python3[599]: act_pow_pos = 307
    Mar 15 11:10:21 xxxx-pi1 python3[599]: curr_L1 = 1.41
    Mar 15 11:10:21 xxxx-pi1 python3[599]: curr_L2 = 0.99
    Mar 15 11:10:21 xxxx-pi1 python3[599]: curr_L3 = 0.44
    Mar 15 11:10:21 xxxx-pi1 python3[599]: meter_ID = b'5706567270xxxxxx'
    Mar 15 11:10:21 xxxx-pi1 python3[599]: meter_model = b'6841121BN243101040'
    Mar 15 11:10:21 xxxx-pi1 python3[599]: react_pow_neg = 4
    Mar 15 11:10:21 xxxx-pi1 python3[599]: react_pow_pos = 0
    Mar 15 11:10:21 xxxx-pi1 python3[599]: volt_L1 = 241
    Mar 15 11:10:21 xxxx-pi1 python3[599]: volt_L2 = 241
    Mar 15 11:10:21 xxxx-pi1 python3[599]: volt_L3 = 243
    Mar 15 11:10:21 xxxx-pi1 python3[599]: URL http://127.0.0.1:8080/json.htm?type=command&param=udevice&idx=1938&nvalue=0&svalue=203 --> b'{\n\t"status" : "OK",\n\t"title" : "Update Device"\n}\n'

### Packet hex dumps

Packet hex dumps will look something like this:

     $ HANdomo.py -x /tmp/packets.log
     7e <-- Start of frame
     a0 d2 <-- ExpectedLength 210
     41 08 83 13 82 d6 e6 e7 00 0f 40 00 00 00 00 01 09 02 ...
     02 02 09 06 00 00 60 01 07 ff 0a 04 36 35 31 35 02 03 ...
     09 06 01 00 01 07 00 ff 06 00 00 03 3a 02 02 0f 00 16 ...
     .
     . 
     .
     7e <-- End of frame at length= 210
     CRC OK on packet of length 210 value 5272

### Packet structural dumps

Packet structual dumps will look something like this:

    $ HANdomo.py -p /tmp/packets.log

    Frame length is 207
         Data type 01 remaining packet length is 193 index 17 level 1
         ARRAY: 9 elements at level 1
             Data type 02 remaining packet length is 191 index 19 level 2
             STRUCT: 2 elements at level 2
                 Data type 09 remaining packet length is 189 index 21 level 3
                 Object 1 OCTETS b'\x01\x01\x00\x02\x81\xff'
                 Data type 0a remaining packet length is 181 index 29 level 3
                 Object 2 STRING b'AIDON_V0001'
             Data type 02 remaining packet length is 168 index 42 level 2
             STRUCT: 2 elements at level 2
                 Data type 09 remaining packet length is 166 index 44 level 3
                 Object 3 OCTETS b'\x00\x00`\x01\x00\xff'
                 Data type 0a remaining packet length is 158 index 52 level 3
                 Object 4 STRING b'7359992890xxxxxx'
             Data type 02 remaining packet length is 140 index 70 level 2
             STRUCT: 2 elements at level 2
                 Data type 09 remaining packet length is 138 index 72 level 3
                 Object 5 OCTETS b'\x00\x00`\x01\x07\xff'
                 Data type 0a remaining packet length is 130 index 80 level 3
                 Object 6 STRING b'6515'
             Data type 02 remaining packet length is 124 index 86 level 2
             STRUCT: 3 elements at level 2
                 Data type 09 remaining packet length is 122 index 88 level 3
                 Object 7 OCTETS b'\x01\x00\x01\x07\x00\xff'
                 Data type 06 remaining packet length is 114 index 96 level 3
                 Object 8 UINT32 826
                 Data type 02 remaining packet length is 109 index 101 level 3
                 STRUCT: 2 elements at level 3
                     Data type 0f remaining packet length is 107 index 103 level 4
                     Object 9 SCALAR 0
                     Data type 16 remaining packet length is 105 index 105 level 4
                     Object 10 VARIABLE 27
                     .
                     .
                     .
                     .

### Packet field dumps

Packet OBIS field dumps will look something like this:

    $ HANdomo.py -f /tmp/packets.log
    act_pow_neg = 0
    act_pow_pos = 826
    curr_L1 = 3.9000000000000004
    meter_ID = b'7359992890xxxxxx'
    meter_model = b'6515'
    obis_list_version = b'AIDON_V0001'
    react_pow_neg = 78
    react_pow_pos = 0
    volt_L1 = 236.20000000000002
    

