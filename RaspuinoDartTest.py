#!/usr/bin/python

import serial
from time import sleep

# look-up table to match byte numbers to board areas
# the byte numbers are created from pin numbers on the Arduino
# byte = (outpin << 4) + inpin 
serial_matrix = {
   51:'D20',  67:'o20',  83:'T20',  99:'i20',
   50:'D01',  66:'o01',  82:'T01',  98:'i01',
   49:'D18',  65:'o18',  81:'T18',  33:'i18',
   48:'D04',  64:'o04',  96:'T04',  16:'i04',
   68:'D13',  80:'o13',  32:'T13',   0:'i13',
   84:'D06',  97:'o06',  17:'T06',   1:'i06',
  100:'D10',  34:'o10',  18:'T10',   2:'i10',
   36:'D15',  35:'o15',  19:'T15',   3:'i15',
   38:'D02',  39:'o02',   7:'T02',  23:'i02',
  102:'D17',  40:'o17',   8:'T17',  24:'i17',
   86:'D03',  41:'o03',   9:'T03',  25:'i03',
   70:'D19', 106:'o19',  10:'T19',  26:'i19',
   54:'D07',  91:'o07',  43:'T07',  27:'i07',
   59:'D16',  75:'o16', 107:'T16',  11:'i16',
   58:'D08',  74:'o08',  90:'T08',  42:'i08',
   57:'D11',  73:'o11',  89:'T11', 105:'i11',
   56:'D14',  72:'o14',  88:'T14', 104:'i14',
   55:'D09',  71:'o09',  87:'T09', 103:'i09',
   53:'D12',  69:'o12', 101:'T12',   5:'i12',
   52:'D05',  85:'o05',  37:'T05',  21:'i05',
    4:' BE',   6:'DBE'
}

if __name__ == "__main__":
    DEVICE = '/dev/ttyACM0'

    ser = serial.Serial(DEVICE, 115200)
    sleep(1) # wait for Arduino
    while True:
	print serial_matrix[ord(ser.read(1))]

