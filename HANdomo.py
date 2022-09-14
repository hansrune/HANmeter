#!/usr/bin/env python3
#
# Try HANdomo -h for help 
#
# Needs python3-serial and python3-crcmod
#
# Create RFX meter sensor:
# 	curl -s "http://127.0.0.1:8080/json.htm?type=createvirtualsensor&idx=762&sensorname=Energy&sensortype=113"
#

import serial, time, sys, getopt, os, urllib.request, datetime
from HANobis import *

prog     = os.path.splitext(os.path.basename(sys.argv[0]))[0]
verbose  = debugpkt = debugobis = debughex = debugfields = debugdomo = filedata = logdata = False
useescape= False  
managedidx = meteridx = poweridx = energyidx = sumpower = npower = sumusagewh = lastmeterswh = diffmeterwh = periodwh = sumusagewh = currmeterwh = lastupdatetime = lastpower = 0
powerkey = "act_pow_pos"
energykey= "act_energy_pos"
minupdateinterval = 30

def usage():
	print( "Usage:",prog,"[-p|--pktdebug][-x|--hexdump][-o|--obisdebug][-f|--fieldsdebug][-d|--domodebug][-l|--log logfilename] file_or_device [poweridx [energyidx]]" )
	sys.exit(1)

def updatedomodevice(idx, nvalue, svalue):
	url="http://127.0.0.1:8080/json.htm?type=command&param=udevice&idx=" + str(idx) + "&nvalue=" + nvalue + "&svalue=" + svalue
	if filedata:
		print("File data URL:", url)
		return
	if idx <= 0:
		return
	try:
		res = urllib.request.urlopen(url, data=None, timeout=10);
	except Exception as e:
		print("URL", url, "ERROR:", str(e))
		return
	if debugdomo:
		print("URL", url, "-->", res.read(100))

def gen_callback(fields):
	global npower, sumpower, lastupdatetime, lastpower, lastmeterswh, currmeterwh, diffmeterwh, periodwh, sumusagewh
	if logdata:
		outputFile.flush()
	if debugfields:
		for key in sorted(fields.keys()):
			print(key,"=",fields[key])
		print("")
	sec = int(time.time())
	if powerkey in fields.keys():
		if lastupdatetime == 0:
			lastupdatetime = sec
			lastpower      = fields[powerkey]
			return
		npower    = npower + 1
		currpower = fields[powerkey]
		sumpower  = sumpower + currpower
		if npower > 0 and sec - minupdateinterval > lastupdatetime:
			avgpower = int( sumpower / npower )
			periodwh = ( sumpower / npower ) * ( sec - lastupdatetime )  / 3600
			sumusagewh = sumusagewh + periodwh

			updatedomodevice(poweridx, "0", str(avgpower) + ";0")

			npower  = sumpower = 0
			lastupdatetime = sec
			lastpower = currpower
	if energykey in fields.keys():
		currmeterwh = fields[energykey]
		updatedomodevice(energyidx, "0", str(currmeterwh))
		if lastmeterswh > 0:
			diffmeterwh = currmeterwh - lastmeterswh
		if verbose:
			print(f"Last hour meter: diffmeterwh={diffmeterwh} integrated energy: sumusagewh={sumusagewh}")
		lastmeterswh = currmeterwh
		sumusagewh = 0
	if verbose:
		print(f"energyidx={energyidx} poweridx={poweridx} power={currpower} npower={npower} sumpower={sumpower} periodwh={periodwh:.1f} sumusagewh={sumusagewh:.1f} currmeterwh={currmeterwh:.1f} diffmeterwh={diffmeterwh:.1f} sec={sec} lastupdatetime={lastupdatetime}")
		
try:
	options, fileargs = getopt.getopt(sys.argv[1:],'pxl:ofdvE',['useescapes','pktdebug','hexdump','log=','obisdebug','fieldsdebug','domodebug','verbose'])
except:
	usage()
#print('OPTIONS:', options)

for opt, arg in options:
	if opt in ('-p','--pktdebug'):
		debugpkt = True
	elif opt in ('-x','--hexdump'):
		debughex = True
	elif opt in ('-o','--obisdebug'):
		debugobis = True
	elif opt in ('-f','--fieldsdebug'):
		debugfields = True
	elif opt in ('-E','--useescapes'):
		useescape = True
	elif opt in ('-l','--log'):
		logdata = True
		print("Logging received data to ",arg)
		outputFile = open(arg, mode='wb')
	elif opt in ('-d','--domodebug'):
		debugdomo = True
	elif opt in ('-v','--verbose'):
		verbose = True

if len(fileargs) < 1: usage();
if len(fileargs) >= 2: energyidx=int(fileargs[1]);
if len(fileargs) >= 3: poweridx=int(fileargs[2]);

if '/dev/' in fileargs[0]:
	print("Using serial port",fileargs[0])
	f = serial.Serial(port=fileargs[0], baudrate=2400, timeout=0.05, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
	serial=True
else:
	print("Reading from file",fileargs[0])
	f = open(fileargs[0], "rb")
	serial=False
	filedata=True
	minupdateinterval = 0

o = genobis(gen_callback, debugobis, debugpkt, debughex, useescape)

while(1):
	byte_s = f.read(1) 
	if not byte_s:
		if serial:
			continue 	# read timeout
		else:
			break		# end of file
	o.decode(byte_s)
	if logdata:
		outputFile.write(byte_s)

f.close()
if logdata:
	outputFile.close()
# vim:ts=4:sw=4
