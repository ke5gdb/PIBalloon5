import time
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
import adafruit_ssd1306
import adafruit_rfm9x
from datetime import datetime
from queue import Queue
from threading import Thread
import logging
from math import modf
import aprs
import zlib

# Create the I2C interface.
i2c = busio.I2C(board.SCL, board.SDA)

# 128x32 OLED Display
if False:
    reset_pin = DigitalInOut(board.D4)
    display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, reset=reset_pin)
    # Clear the display.
    display.fill(0)
    display.show()
    width = display.width
    height = display.height
else:
    display = False

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

def receiver_thread(q):
    prev_packet = None
    prev_packet_time = datetime.now()
    display_text = ["", "", ""]

    while True:
        packet = rfm9x.receive(keep_listening=True, timeout=300) #, with_ack=True, timeout=None)
        try:
            packet = zlib.decompress(packet)
            delta = prev_packet_time - datetime.now()
            prev_packet_time = datetime.now()
            q.put([packet, delta, rfm9x.last_rssi, rfm9x.last_snr])
        except:
            continue

def processing_thread(q):
    loading_chars = ['-', '\\', '|', '/']
    i = 0
    j = 0
    prev_packet = None
    prev_packet_time = datetime.now()
    prev_aprs_time = datetime.now()
    display_text = ["", "", ""]
    skyinfo = ""

    if display:
        display_text[0] = "No packet received"
        display.fill(0)
        display.text(display_text[0], 0, 0, 1)
        display.show()

    while True:
        f = open("gps_log.csv", "a")
        a = aprs.TCP(b'KE5GDB', b'18850')
        a.start()

        while True:
            i = (i + 1) % 4
            if q.empty():
                time.sleep(0.5)
            else:
                packet = q.get()
                try:
                    if packet is not None and packet[0] is not None:
                        prev_packet = packet[0]
                        packet_text = str(prev_packet, "utf-8").split(',')
                        
                        if packet_text[0] == "pbvtpv":
                            prev_packet_time = datetime.now()
                            display_text[1] = f"{float(packet_text[2]):0.5f} / {float(packet_text[3]):0.5f}"
                            display_text[2] = f"Alt: {float(packet_text[4]) * 3.28084:0.0f} Speed: {float(packet_text[5]):0.0f}"
                            f.write(f"{packet_text[1]},{packet[2]},{packet[3]},pos,{float(packet_text[2]):0.4f},{float(packet_text[3]):0.4f},{float(packet_text[4]) * 3.28084:0.0f},{float(packet_text[5]):0.0f}\n")
                            f.flush()

                            aprs_time_delta = prev_packet_time - prev_aprs_time

                            if aprs_time_delta.total_seconds() >= 15:
                                lat = aprs.dec2dm_lat(float(packet_text[2]))
                                lon =  aprs.dec2dm_lng(float(packet_text[3]))
                                speed = (float(packet_text[5]) / 2.237)
                                alt = float(packet_text[4]) * 3.28084
                                lat_a = int(divmod(float(packet_text[2])*60,60)[1] % .01 * 10**3)
                                lon_o = int(divmod(float(packet_text[3])*60,60)[1] % .01 * 10**3)
                                dao = f"!W{lat_a}{lon_o}!"
                                aprs_packet = f"KE5GDB-11>APRS:!{lat}/{lon}O/A={alt:06.0f} RSSI={packet[2]}dBm SNR={packet[3]}dB {skyinfo}{dao}"
                                frame = aprs.parse_frame(aprs_packet)
                                a.send(frame)
                                
                                prev_aprs_time = prev_packet_time

                                print(aprs_packet)

                        elif packet_text[0] == "pbvsky":
                            f.write(f"{packet_text[1]},{packet[2]},{packet[3]},sky,{packet_text[2]},{packet_text[3]},{packet_text[4]},{packet_text[5]}\n")
                            f.flush()
                            skyinfo = f"HDOP={packet_text[2]} VDOP={packet_text[3]} sats={packet_text[4]}/{packet_text[5]}"

                        print(f"{packet_text} / RSSI: {packet[2]} / SNR: {packet[3]}")
                except:
                    logging.error("Decode error!")
                    break

            delta = prev_packet_time - datetime.now()
            display_text[0] = f"{loading_chars[i]}  Last Position: {abs(delta.total_seconds()):.0f}s"

            if display:
                display.fill(0)
                display.text(display_text[0], 0, 0, 1)
                display.text(display_text[1], 0, 10, 1)
                display.text(display_text[2], 0, 20, 1)
                display.show()

        f.close()


q = Queue()
t1 = Thread(target = receiver_thread, args =(q, ))
t2 = Thread(target = processing_thread, args =(q, ))
t1.start()
t2.start()

"""


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
"""