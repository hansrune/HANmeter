#
# This code builds upon the work from https://github.com/skagmo/meter_reading
#

import struct, crcmod, sys

# HDLC constants
FLAG = '\x7e'
ESCAPE = '\x7d'

# HDLC states
WAITING = 0
DATA = 1
ESCAPED = 2

# minimal data frame
MINFRAME=19
MAXFRAME=512

# Number of objects in known frames
OBJECTS_2P5SEC = 1
OBJECTS_10SEC1P = 9
OBJECTS_10SEC3P = 12
OBJECTS_1HOUR1P = 14
OBJECTS_1HOUR3P = 17

# OBIS types
TYPE_ARRAY  = 0x01
TYPE_STRUCT = 0x02
TYPE_UINT32 = 0x06
TYPE_OCTETS = 0x09
TYPE_STRING = 0x0a
TYPE_INT16  = 0x10
TYPE_UINT16 = 0x12
TYPE_I8SCALE= 0x0f
TYPE_I8VAR  = 0x16
#
# OBIS object identifiers
obisid = {
	# Common
	b'\x01\x01\x00\x02\x81\xff': ("obis_list_version", 0, "OBIS list version ID"),
	# Aidon / Kaifa
	b'\x00\x00\x60\x01\x00\xff': ("meter_ID",0,"Meter ID (GS1)"),
	b'\x00\x00\x60\x01\x07\xff': ("meter_model",0,"Meter type"),
	b'\x01\x00\x01\x07\x00\xff': ("act_pow_pos",0,"Active power+ (Q1+Q4)"),
	b'\x01\x00\x02\x07\x00\xff': ("act_pow_neg",0,"Active power- (Q2+Q3)"),
	b'\x01\x00\x03\x07\x00\xff': ("react_pow_pos",0,"Reactive power+ (Q1+Q4)"),
	b'\x01\x00\x04\x07\x00\xff': ("react_pow_neg",0,"Reactive power- (Q3+Q4)"),
	b'\x01\x00\x1f\x07\x00\xff': ("curr_L1",0.1,"IL1 Current phase L1"),
	b'\x01\x00\x33\x07\x00\xff': ("curr_L2",0.1,"IL2 Current phase L2"),
	b'\x01\x00\x47\x07\x00\xff': ("curr_L3",0.1,"IL3 Current phase L3"),
	b'\x01\x00\x20\x07\x00\xff': ("volt_L1",0.1,"UL1 Phase voltage 4W meter/Line voltage 3W meter"),
	b'\x01\x00\x34\x07\x00\xff': ("volt_L2",0.1,"UL2 Phase voltage 4W meter/Line voltage 3W meter"),
	b'\x01\x00\x48\x07\x00\xff': ("volt_L3",0.1,"UL3 Phase voltage 4W meter/Line voltage 3W meter"),
	b'\x00\x00\x01\x00\x00\xff': ("date_time",0,"Clock and date in meter"),
	b'\x01\x00\x01\x08\x00\xff': ("act_energy_pos",10,"Cumulative hourly active import energy (A+) (Q1+Q4)"),
	b'\x01\x00\x02\x08\x00\xff': ("act_energy_neg",10,"Cumulative hourly active export energy (A-) (Q2+Q3)"),
	b'\x01\x00\x03\x08\x00\xff': ("react_energy_pos",10,"Cumulative hourly reactive import energy (R+) (Q1+Q2)"),
	b'\x01\x00\x04\x08\x00\xff': ("react_energy_neg",10,"Cumulative hourly reactive export energy (R-) (Q3+Q4)"),
	# Kamstrup
	b'\x01\x01\x00\x00\x05\xff': ("meter_ID",0,"Meter ID (GS1)"),
	b'\x01\x01\x60\x01\x01\xff': ("meter_model",0,"Meter type"),
	b'\x01\x01\x01\x07\x00\xff': ("act_pow_pos",0,"Active power+ (Q1+Q4/P14)"),
	b'\x01\x01\x02\x07\x00\xff': ("act_pow_neg",0,"Active power- (Q2+Q3/P23)"),
	b'\x01\x01\x03\x07\x00\xff': ("react_pow_pos",0,"Reactive power+ (Q1+Q4/Q12)"),
	b'\x01\x01\x04\x07\x00\xff': ("react_pow_neg",0,"Reactive power- (Q3+Q4/Q34)"),
	b'\x01\x01\x1f\x07\x00\xff': ("curr_L1",0.01,"IL1 Current phase L1"),
	b'\x01\x01\x33\x07\x00\xff': ("curr_L2",0.01,"IL2 Current phase L2"),
	b'\x01\x01\x47\x07\x00\xff': ("curr_L3",0.01,"IL3 Current phase L3"),
	b'\x01\x01\x20\x07\x00\xff': ("volt_L1",0,"UL1 Phase voltage 4W meter/Line voltage 3W meter"),
	b'\x01\x01\x34\x07\x00\xff': ("volt_L2",0,"UL2 Phase voltage 4W meter/Line voltage 3W meter"),
	b'\x01\x01\x48\x07\x00\xff': ("volt_L3",0,"UL3 Phase voltage 4W meter/Line voltage 3W meter"),
	b'\x00\x01\x01\x00\x00\xff': ("date_time",0,"Clock and date in meter"),
	b'\x01\x01\x01\x08\x00\xff': ("act_energy_pos",10,"Cumulative hourly active import energy (A+) (Q1+Q4/A14)"),
	b'\x01\x01\x02\x08\x00\xff': ("act_energy_neg",10,"Cumulative hourly active export energy (A-) (Q2+Q3/A23)"),
	b'\x01\x01\x03\x08\x00\xff': ("react_energy_pos",10,"Cumulative hourly reactive import energy (R+) (Q1+Q2/R12)"),
	b'\x01\x01\x04\x08\x00\xff': ("react_energy_neg",10,"Cumulative hourly reactive export energy (R-) (Q3+Q4/R34)"),
}


class genobis:
	def __init__(self, callback, debugobis = False, debugpkt = False, debughex = False, useescape = False):
		self.state = WAITING
		self.pkt = b''
		self.idx = 0
		self.expect = 19
		self.received = 0
		self.crc_func = crcmod.mkCrcFun(0x11021, rev=True, initCrc=0xffff, xorOut=0x0000)
		self.callback = callback
		self.framedbg = debugpkt
		self.obisdbg = debugobis
		self.hexdump = debughex
		self.useescape = useescape


	# Does a lot of assumptions on Aidon/Hafslund COSEM format
	# Not a general parser! 
	def parseframe(self, pkt, pidx):
		# 0,1 frame format
		# 2 client address
		# 3,4 server address
		# 5 control
		# 6,7 HCS
		# 8,9,10 LLC
		frame_type = (pkt[0] & 0xf0) >> 4
		length = ((pkt[0] & 0x07) << 8) + pkt[1]
		if self.framedbg: print("\nFrame length is",len(pkt) - 3)
		data   = []
		fields = {}
		obis   = b''
		getobis= True
		
		# just the pragmatic way - probably not correct for all types of meters
		if (pkt[11] == 0x0f):
			pidx=16
		elif (pkt[10] == 0x0f):
			pidx=15
		else:
			if self.framedbg: print(indent,"Unknown frame format", format(pkt[10], "02x"),"and",format(pkt[11], "02x"))
			return

		def dataoctets():
			nonlocal pidx
			nonlocal getobis
			nonlocal obis
			l = pkt[pidx]
			pidx += 1
			if ( l > 0 ):
				b=pkt[pidx:pidx+l]
			else:
				b = b''
			pidx += l 
			if ( getobis ) and (len(b) == 6) and ( b[5] == 0xff ):
				obis = b
			return b
		
		def parseobj(lvl):
			nonlocal pidx 
			nonlocal obis 
			nonlocal getobis

			indent  = "    "*lvl
			dobject = ""
			dtype = pkt[pidx]
			if self.framedbg: 
				print(indent,"Data type", format(dtype, "02x"), \
					  "remaining packet length is",len(pkt) - pidx, \
					  "index", pidx, "level", lvl)
			pidx += 1
			dsize = 0
			if   (dtype == TYPE_ARRAY):
				nelem = pkt[pidx]
				pidx += 1
				if self.framedbg: print(indent, "ARRAY:", nelem, "elements at level", lvl )
				while ( nelem > 0 ):
					parseobj(lvl+1)
					nelem -= 1
				return
			elif (dtype == TYPE_STRUCT):
				nelem = pkt[pidx]
				pidx += 1
				if self.framedbg: print(indent, "STRUCT:", nelem, "elements at level", lvl)
				while ( nelem > 0 ):
					parseobj(lvl+1)
					nelem -= 1
				return
			elif (dtype == TYPE_STRING):
				dobject = "STRING"
				data.append(dataoctets())
			elif (dtype == TYPE_UINT32):
				dobject = "UINT32"
				dsize = 4
				data.append(struct.unpack(">I", pkt[pidx:pidx+dsize])[0])
			elif (dtype == TYPE_INT16):
				dobject = "INT16"
				dsize = 2
				data.append(struct.unpack(">h", pkt[pidx:pidx+dsize])[0])
			elif (dtype == TYPE_OCTETS):
				dobject = "OCTETS"
				data.append(dataoctets())
			elif (dtype == TYPE_UINT16):
				dobject = "UINT16"
				dsize = 2
				data.append(struct.unpack(">H", pkt[pidx:pidx+dsize])[0])
			elif (dtype == TYPE_I8VAR):
				dobject = "VARIABLE"
				dsize = 1
				data.append(pkt[pidx])
			elif (dtype == TYPE_I8SCALE):
				dobject = "SCALAR"
				dsize = 1
				data.append(pkt[pidx])
			else:
				# assuming 1 byte size
				if self.framedbg: print(indent, "Object of unknown type", format(dtype, "02x"))
				dsize = 1
				# not safe to continue as size is unknown
				return
			if (self.framedbg) and (dobject != ""):
				print(indent, "Object", len(data), dobject, data[-1])
			if ( obis != b'' ):
				if (getobis):
					getobis=False
					#if self.obisdbg: print(indent, "Got obis code",obis)
				else:
					if obis in obisid:
						multiplier=obisid[obis][1]
						if multiplier == 0:
							fields[obisid[obis][0]] = data[-1]
						else:
							fields[obisid[obis][0]] = data[-1]*multiplier
					else:
						print(indent,"Unknown OBIS code",obis)
						# avoid decoding the last 0xff
						# fields[obis[0:4]] = data[-1]
					if self.obisdbg: print(indent, "Insert obis field ",obis, "value", data[-1])
					getobis = True
					obis    = b''
			pidx += dsize

		dataoctets()
		while ( len(pkt) - pidx > 2 ):
			parseobj(1)

		self.callback(fields)
		# fix for issue #2 reported by espenbo
		sys.stdout.flush()

	# General HDLC decoder
	def decode(self, c):
		if self.hexdump: 
			if ( ord(c) == ord(FLAG) ): print("")
			sys.stdout.write(format(ord(c), "02x")+" ")

			#sys.stdout.write(format(ord(c), "2x")+"/"+format(self.received,"3d")+" ")

		# Waiting for packet start
		if (self.state == WAITING): 
			if (ord(c) == ord(FLAG)):
				self.state = DATA
				self.pkt = b''
				self.idx = 0
				self.expect = MINFRAME
				if self.hexdump: print("<-- Start of frame ")

		elif (self.state == ESCAPED):
			self.pkt += bytes(ord(c) ^ 0x20)
			if self.hexdump: sys.stdout.write("<-- Escaped="+format(ord(c), "02x")+" ")
			self.state = DATA

		elif (self.state == DATA):
			if (self.useescape) and (ord(c) == ord(ESCAPE)):
				self.state = ESCAPED
			elif (ord(c) == ord(FLAG) ) and (self.received >= self.expect):
				if self.hexdump: print("<-- End of frame at length=",len(self.pkt))
				
				# Minimum length check
				if (len(self.pkt) >= MINFRAME):
					# Check CRC
					crc = self.crc_func(self.pkt[:-2])
					crc ^= 0xffff
					pcrc = struct.unpack("<H", self.pkt[-2:])[0]
					if (crc == pcrc):
						if self.hexdump:
							print("CRC OK on packet of length",len(self.pkt),"value",format(pcrc,"04x"))
						self.parseframe(self.pkt, self.idx)
					else:
						print("CRC error on packet of length",len(self.pkt),"value",format(crc,"04x"), "versus",format(pcrc,"04x"))
					self.received = 0
					self.state = WAITING
			else:
				self.pkt += c
				self.received += 1
				if (self.received == 2):
					self.expect = ((self.pkt[0] & 0x07) << 8) + self.pkt[1]
					if self.hexdump: 
						print("<-- ExpectedLength",self.expect)
					if (self.expect > MAXFRAME):
						print("Oversized packet of length",self.expect)
						self.expect = MAXFRAME


		#if self.hexdump: sys.stdout.flush() 
# vim:ts=4:sw=4
