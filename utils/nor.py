#==========================================================
# NOR utils
# part of ps4 wee tools project
#==========================================================
import hashlib, os, math, sys, ctypes
from utils.utils import *
import data.data as Data

NOR_DUMP_SIZE = 0x2000000
NOR_BACKUP_OFFSET = 0x3000
NOR_MBR_SIZE = 0x1000
NOR_BLOCK_SIZE = 0x200

PS4_REGIONS = {
	'00':'Japan',
	'01':'US, Canada (North America)',
	'15':'US, Canada (North America)',
	'02':'Australia / New Zealand (Oceania)',
	'03':'U.K. / Ireland',
	'04':'Europe / Middle East / Africa',
	'16':'Europe / Middle East / Africa',
	'05':'Korea (South Korea)',
	'06':'Southeast Asia / Hong Kong',
	'07':'Taiwan',
	'08':'Russia, Ukraine, India, Central Asia',
	'09':'Mainland China',
	'11':'Mexico, Central America, South America',
	'14':'Mexico, Central America, South America',
}

SWITCH_TYPES = [
	'Off',
	'Fat 10xx/11xx',
	'Fat/Slim/PRO 12xx/2xxx/7xxx',
	'General',
]

SWITCH_BLOBS = [
	{'t':1, 'v':[0xFF]*8 + [0x00]*8},
	{'t':1, 'v':[0x00]*8 + [0xFF]*8},
	{'t':2, 'v':[0xFF]*16},
	{'t':2, 'v':[0x00]*16},
	{'t':3, 'v':[0xFF]*4 + [0x00]*12},
	{'t':3, 'v':[0x00]*4 + [0xFF]*12},
	{'t':3, 'v':[0xFF]*12 + [0x00]*4},
	{'t':3, 'v':[0x00]*12 + [0xFF]*4},
]

BOOT_MODES = {b'\xFE':'Development', b'\xFB':'Assist', b'\xFF':'Release'}

# {'o':<offset>, 'l':<length>, 't':<type>, 'n':<name>}
NOR_PARTITIONS = {
	"s0_header"			: {"o": 0x00000000,	"l": 0x1000,	"n":"s0_head"},
	"s0_active_slot"	: {"o": 0x00001000,	"l": 0x1000,	"n":"s0_act_slot"},
	"s0_MBR1"			: {"o": 0x00002000,	"l": 0x1000,	"n":"s0_mbr1"},
	"s0_MBR2"			: {"o": 0x00003000,	"l": 0x1000,	"n":"s0_mbr2"},
	"s0_emc_ipl_a"		: {"o": 0x00004000,	"l": 0x60000,	"n":"sflash0s0x32"},
	"s0_emc_ipl_b"		: {"o": 0x00064000,	"l": 0x60000,	"n":"sflash0s0x32b"},
	"s0_eap_kbl"		: {"o": 0x000C4000,	"l": 0x80000,	"n":"sflash0s0x33"},
	"s0_wifi"			: {"o": 0x00144000,	"l": 0x80000,	"n":"sflash0s0x38"},
	"s0_nvs"			: {"o": 0x001C4000,	"l": 0xC000,	"n":"sflash0s0x34"},
	"s0_blank"			: {"o": 0x001D0000,	"l": 0x30000,	"n":"sflash0s0x0"},
	"s1_header"			: {"o": 0x00200000,	"l": 0x1000,	"n":"s1_head.crypt"},
	"s1_active_slot"	: {"o": 0x00201000,	"l": 0x1000,	"n":"s1_act_slot.crypt"},
	"s1_MBR1"			: {"o": 0x00202000,	"l": 0x1000,	"n":"s1_mbr1.crypt"},
	"s1_MBR2"			: {"o": 0x00203000,	"l": 0x1000,	"n":"s1_mbr2.crypt"},
	"s1_samu_ipl_a"		: {"o": 0x00204000,	"l": 0x3E000,	"n":"sflash0s1.cryptx2"},
	"s1_samu_ipl_b"		: {"o": 0x00242000,	"l": 0x3E000,	"n":"sflash0s1.cryptx2b"},
	"s1_idata"			: {"o": 0x00280000,	"l": 0x80000,	"n":"sflash0s1.cryptx1"},
	"s1_bd_hrl"			: {"o": 0x00300000,	"l": 0x80000,	"n":"sflash0s1.cryptx39"},
	"s1_VTRM"			: {"o": 0x00380000,	"l": 0x40000,	"n":"sflash0s1.cryptx6"},
	"s1_CoreOS_A"		: {"o": 0x003C0000,	"l": 0xCC0000,	"n":"sflash0s1.cryptx3"},
	"s1_CoreOS_B"		: {"o": 0x01080000,	"l": 0xCC0000,	"n":"sflash0s1.cryptx3b"},
	"s1_blank"			: {"o": 0x01D40000,	"l": 0x2C0000,	"n":"sflash0s1.cryptx40"},
}

# 'KEY':{'o':<offset>, 'l':<length>, 't':<type>, 'n':<name>}
NOR_AREAS = {
	
	'ACT_SLOT':	{'o':0x001000,	'l':1,			't':'b',	'n':'Active slot'},			# 0x00 - A 0x80 - B
	
	'MAC':		{'o':0x1C4021,	'l':6,			't':'b',	'n':'MAC Address'},
	'MB_SN':	{'o':0x1C8000,	'l':16,			't':'s',	'n':'Motherboard Serial'},
	'SN':		{'o':0x1C8030,	'l':17,			't':'s',	'n':'Console Serial'},
	'SKU':		{'o':0x1C8041,	'l':13,			't':'s',	'n':'SKU Version'},
	'REGION':	{'o':0x1C8047,	'l':2,			't':'s',	'n':'Region code'},
	
	'BOOT_MODE':{'o':0x1C9000,	'l':1,			't':'b',	'n':'Boot mode'},			# Development(FE), Assist(FB), Release(FF)
	'MEM_BGM':	{'o':0x1C9003,	'l':1,			't':'b',	'n':'Memory budget mode'},	# Large(FE), Normal(FF)
	'SLOW_HDD':	{'o':0x1C9005,	'l':1,			't':'b',	'n':'HDD slow mode'},		# On(FE), Off(FF)
	'SAFE_BOOT':{'o':0x1C9020,	'l':1,			't':'b',	'n':'Safe boot'},			# On(01), Off(00/FF)
	'FW_MIN':	{'o':0x1C9062,	'l':2,			't':'b',	'n':'Minimal FW version?'},
	'FW_VER':	{'o':0x1C906A,	'l':2,			't':'b',	'n':'FW in active slot'},
	'SAMUBOOT':	{'o':0x1C9323,	'l':1,			't':'b',	'n':'SAMU enc'},	
	'HDD':		{'o':0x1C9C00,	'l':60,			't':'s',	'n':'HDD'},
	'HDD_TYPE':	{'o':0x1C9C3C,	'l':4,			't':'s',	'n':'HDD type'},
	
	'SYS_FLAGS':{'o':0x1C9310,	'l':64,			't':'b',	'n':'System flags'},		# Clean FF*64
	'MEMTEST':	{'o':0x1C9310,	'l':1,			't':'b',	'n':'Memory test'},			# On(01), Off(00/FF)
	'RNG_KEY':	{'o':0x1C9312,	'l':1,			't':'b',	'n':'RNG/Keystorage test'},	# On(01), Off(00/FF)
	'UART':		{'o':0x1C931F,	'l':1,			't':'b',	'n':'UART'},				# On(01), Off(00)
	'MEMCLK':	{'o':0x1C9320,	'l':1,			't':'b',	'n':'GDDR5 Memory clock'},
	
	'BTNSWAP':	{'o':0x1CA040,	'l':1,			't':'b',	'n':'Buttons swap'},		# X(01), O(00/FF)
	'FW_C':		{'o':0x1CA5D8,	'l':1,			't':'b',	'n':'FW Counter'},
	'FW_PC':	{'o':0x1CA5D9,	'l':1,			't':'b',	'n':'FW Patch Counter'},
	'IDU':		{'o':0x1CA600,	'l':1,			't':'b',	'n':'IDU (Kiosk mode)'},	# On(01), Off(00/FF)
	'UPD_MODE':	{'o':0x1CA601,	'l':1,			't':'b',	'n':'Update mode'},			# On(10), Off(00)
	'REG_REC':	{'o':0x1CA603,	'l':1,			't':'b',	'n':'Registry recovery'},	# On(01), Off(00)
	'FW_V':		{'o':0x1CA606,	'l':2,			't':'s',	'n':'FW Version'},
	'ARCADE':	{'o':0x1CA609,	'l':1,			't':'s',	'n':'Arcade mode'},			# On(01), Off(00/FF)
	
	'MANU':		{'o':0x1CBC00,	'l':32,			't':'b',	'n':'MANU mode'},			# Enabled(0*32), Disabled(FF*32)
	
	'CORE_SWCH':{'o':0x201000,	'l':16,			't':'b',	'n':'Slot switch hack'},
}

SOUTHBRIDGES = {
	'Aeolia A2':	[0x0D, 0x0E],
	'Belize A0/B0':	[0x20, 0x21],
	'Baikal B1':	[0x24, 0x25],
	'Belize 2 A0':	[0x2A, 0x2B],
}

TORUS_VERS = {
	0x03: 'Version 1',
	0x22: 'Version 2',
	0x30: 'Version 3',
}

MAGICS = {
	"s0_header"			: {"o": 0x00,	"v":b'SONY COMPUTER ENTERTAINMENT INC.'},
	"s0_MBR1"			: {"o": 0x00,	"v":b'Sony Computer Entertainment Inc.'},
	"s0_MBR2"			: {"o": 0x00,	"v":b'Sony Computer Entertainment Inc.'},
}

# MBR parser

class Partition(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("start_lba",	ctypes.c_uint32),
        ("n_sectors",	ctypes.c_uint32),
        ("type",		ctypes.c_uint8),			# part_id?
        ("flag",		ctypes.c_uint8),
        ("unknown",		ctypes.c_uint16),
        ("padding",		ctypes.c_uint64)
    ]

class MBR_v1(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("magic", 		ctypes.c_uint8 * 0x20),	# SONY COMPUTER ENTERTAINMENT INC.
        ("version", 	ctypes.c_uint32),			# 1
        ("mbr1_start",	ctypes.c_uint32),			# ex: 0x10
        ("mbr2_start",	ctypes.c_uint32),			# ex: 0x18
        ("unk",			ctypes.c_uint32 * 4),		# ex: (1, 1, 8, 1)
        ("reserved",	ctypes.c_uint32),
        ("unused",		ctypes.c_uint8 * 0x1C0)
    ]

class MBR_v4(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("magic",		ctypes.c_uint8 * 0x20),	# Sony Computer Entertainment Inc.
        ("version",		ctypes.c_uint32),			# 4
        ("n_sectors",	ctypes.c_uint32),
        ("reserved",	ctypes.c_uint64),
        ("loader_start",ctypes.c_uint32),			# ex: 0x11, 0x309
        ("loader_count",ctypes.c_uint32),			# ex: 0x267
        ("reserved2",	ctypes.c_uint64),
        ("partitions",	Partition * 16)
	]

PARTITIONS_TYPES = {
	0:"empty",
	1:"idstorage",
	2:"sam_ipl",
	3:"core_os",
	6:"bd_hrl",
	13:"emc_ipl",
	14:"eap_kbl",
	32:"emc_ipl",
	33:"eap_kbl",
	34:"nvs",
	38:"wifi",
	39:"vtrm",
	40:"empty",
	41:"C0050100",
}

# Functions ===============================================

def getConsoleRegion(file):
	code = getNorData(file,'REGION').decode('utf-8','ignore')
	desc = PS4_REGIONS[code] if code in PS4_REGIONS else STR_UNKNOWN
	return [code, desc]



def getMemClock(file):
	raw1 = getNorData(file,'MEMCLK')[0]
	raw2 = getNorDataB(file,'MEMCLK')[0]
	return [raw1, rawToClock(raw1), raw2, rawToClock(raw2)]



def getSlotSwitchInfo(file):
	pattern = list(getNorData(file,'CORE_SWCH'))
	for i in range(0,len(SWITCH_BLOBS)):
		if SWITCH_BLOBS[i]['v'] == pattern:
			return SWITCH_TYPES[SWITCH_BLOBS[i]['t']]+' [#'+str(i+1)+']'
	return SWITCH_TYPES[0]+' '+getHex(bytes(pattern),'')



def getNorFW(f):
	old_fw = getNorData(f, 'FW_V')
	
	fw = getNorData(f, 'FW_VER') if old_fw[0] == 0xFF else old_fw
	fw = '{:X}.{:02X}'.format(fw[1], fw[0])
	
	mfw = getNorData(f, 'FW_MIN')
	mfw = '{:X}.{:02X}'.format(mfw[1], mfw[0]) if mfw[0] != 0xFF else ''
	
	return {'c':fw, 'min':mfw}


def getPartitionName(code):
	return PARTITIONS_TYPES[code] if code in PARTITIONS_TYPES else 'Unk_'+str(code)


def getNorPartition(f, name):
	if not name in NOR_PARTITIONS:
		return ''
	return getData(f, NOR_PARTITIONS[name]['o'], NOR_PARTITIONS[name]['l'])



def getNorPartitionMD5(f, name):
	data = getNorPartition(f, name)
	if len(data) > 0:
		return hashlib.md5(data).hexdigest()
	return ''



def checkNorPartMagic(f, name):
	data = getNorPartition(f, name)
	if len(data) <= 0:
		return False
	if name in MAGICS:
		offset = MAGICS[name]['o']
		length = offset + len(MAGICS[name]['v'])
		if data[offset:length] == MAGICS[name]['v']:
			return True
	return False



def getPartitionsInfo(f):
	# f - file in rb/r+b mode
	f.seek(NOR_MBR_SIZE)
	active = f.read(1)
	
	base = NOR_MBR_SIZE*2 if active == 0x00 else NOR_MBR_SIZE*3
	f.seek(base)
	mbr = MBR_v4()
	f.readinto(mbr)
	
	partitions = []
	
	for i in range(len(mbr.partitions)):
		
		p = mbr.partitions[i]
		
		partitions.append({
			'name'		: getPartitionName(p.type),
			'offset'	: p.start_lba * NOR_BLOCK_SIZE,
			'size'		: p.n_sectors * NOR_BLOCK_SIZE,
			'type'		: p.type,
		})
	
	return {'active':active, 'base':base, 'partitions':partitions}



def getTorusVersion(f):
	torus_md5 = getNorPartitionMD5(f, 's0_wifi')
	torus = Data.TORUS_FW_MD5[torus_md5]['t'] if torus_md5 in Data.TORUS_FW_MD5 else 0
	
	return TORUS_VERS[torus] if torus in TORUS_VERS else ''


def getSouthBridge(f):
	
	emc_md5 = getNorPartitionMD5(f, 's0_emc_ipl_a')
	eap_md5 = getNorPartitionMD5(f, 's0_eap_kbl')
	
	emc = Data.EMC_IPL_MD5[emc_md5]['t'] if emc_md5 in Data.EMC_IPL_MD5 else 0
	eap = Data.EAP_KBL_MD5[eap_md5]['t'] if eap_md5 in Data.EAP_KBL_MD5 else 0
	
	for key in SOUTHBRIDGES:
		if SOUTHBRIDGES[key] == [emc, eap]:
			return key
	
	return '[0x%02X, 0x%02X]'%(emc, eap)


# NOR Areas data utils

def getNorAreaName(key):
	if key in NOR_AREAS:
		return NOR_AREAS[key]['n']
	return STR_UNKNOWN



def setNorData(file, key, val):
	if not key in NOR_AREAS:
		return False
	return setData(file, NOR_AREAS[key]['o'], val)



def setNorDataB(file, key, val):
	if not key in NOR_AREAS:
		return False
	return setData(file, NOR_AREAS[key]['o'] + NOR_BACKUP_OFFSET, val)



def getNorData(file, key):
	if not key in NOR_AREAS:
		return False
	return getData(file, NOR_AREAS[key]['o'], NOR_AREAS[key]['l'])



def getNorDataB(file, key):
	if not key in NOR_AREAS:
		return False
	return getData(file, NOR_AREAS[key]['o'] + NOR_BACKUP_OFFSET, NOR_AREAS[key]['l'])