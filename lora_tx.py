#!/usr/sbin/python3

# Import Python System Libraries
import time
# Import Blinka Libraries
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
# Import the SSD1306 module.
import adafruit_ssd1306
# Import RFM9x
import adafruit_rfm9x

from datetime import datetime
import logging
from queue import Queue
from threading import Thread
from gps import *
import zlib

# Button A
btnA = DigitalInOut(board.D5)
btnA.direction = Direction.INPUT
btnA.pull = Pull.UP

# Button B
btnB = DigitalInOut(board.D6)
btnB.direction = Direction.INPUT
btnB.pull = Pull.UP

# Button C
btnC = DigitalInOut(board.D12)
btnC.direction = Direction.INPUT
btnC.pull = Pull.UP

# Create the I2C interface.
i2c = busio.I2C(board.SCL, board.SDA)

# 128x32 OLED Display
reset_pin = DigitalInOut(board.D4)
display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, reset=reset_pin)
# Clear the display.
display.fill(0)
display.show()
width = display.width
height = display.height

# Configure LoRa Radio
CS = DigitalInOut(board.CE1)
RESET = DigitalInOut(board.D25)
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 434.5)
rfm9x.tx_power = 23

rfm9x.signal_bandwidth = 125000
rfm9x.coding_rate = 5
rfm9x.spreading_factor = 10
#rfm9x.enable_crc = True

prev_packet = None

def transmitter_thread(q):
    while True:
        packet = q.get()
        packet = zlib.compress(packet)
        rfm9x.send(packet)
        time.sleep(0.1)

def gps_thread(q):
    gpsd = gps(mode=WATCH_ENABLE|WATCH_NEWSTYLE) 
    while True:
        report = gpsd.next()
        timestamp = datetime.now().timestamp()
        if report['class'] == 'TPV':
            lat = float(getattr(report,'lat',0.0))
            lon = float(getattr(report,'lon',0.0))
            alt = getattr(report,'alt',0.0)
            spd = getattr(report,'speed',0.0)
            clm = getattr(report,'climb',0.0)
            tx_string = f"pbvtpv,{timestamp:.2f},{lat:.6f},{lon:.6f},{alt:.1f},{spd},{clm}"
            q.put(bytes(tx_string, "utf-8"))
            logging.info("Sent position data")

        if report['class'] == 'SKY':
            hdop = getattr(report,'hdop',-99)
            vdop = getattr(report,'vdop',-99)
            sats = [0, 0] # used, visible
            for sat in report.satellites:
                if sat.used:
                    sats[0] += 1
                    sats[1] += 1
                else:
                    sats[1] += 1

            tx_string = f"pbvsky,{timestamp:.2f},{hdop:.2f},{vdop:.2f},{sats[0]},{sats[1]}"
            q.put(bytes(tx_string, "utf-8"))
            logging.info("Sent SKY data")

q = Queue()
t1 = Thread(target = transmitter_thread, args =(q, ))
t2 = Thread(target = gps_thread, args =(q, ))
t1.start()
t2.start()

"""

while True:
    packet = None
    # draw a box to clear the image
    display.fill(0)
    display.text('KE5GDB PiBalloonV', 35, 0, 1)

    # check for packet rx
    packet = rfm9x.receive()
    if packet is None:
        display.show()
        display.text('- Waiting for PKT -', 15, 20, 1)
    else:
        # Display the packet text and rssi
        display.fill(0)
        prev_packet = packet
        packet_text = str(prev_packet, "utf-8")
        display.text('RX: ', 0, 0, 1)
        display.text(packet_text, 25, 0, 1)
        time.sleep(1)

    if not btnA.value:
        # Send Button A
        display.fill(0)
        button_a_data = bytes("Button A!\r\n","utf-8")
        rfm9x.send(button_a_data)
        display.text('Sent Button A!', 25, 15, 1)
    elif not btnB.value:
        # Send Button B
        display.fill(0)
        button_b_data = bytes("Button B!\r\n","utf-8")
        rfm9x.send(button_b_data)
        display.text('Sent Button B!', 25, 15, 1)
    elif not btnC.value:
        # Send Button C
        display.fill(0)
        button_c_data = bytes("Button C!\r\n","utf-8")
        rfm9x.send(button_c_data)
        display.text('Sent Button C!', 25, 15, 1)


    display.show()
    time.sleep(0.1)

"""

