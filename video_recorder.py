#!/usr/bin/python3

#
# KE5GDB 2021
# PiBalloonV image and video recorder
#

import picamera
import time
from datetime import datetime, timedelta
import logging
import threading
from gps import *
import os
from shutil import copy2
from digitalio import DigitalInOut, Direction, DriveMode
import board

# Video length in secods
video_length = 45

gps_info = [0.0, 0.0, 0.0, 'NaN', 'NaN']

def capture_thread():
    with picamera.PiCamera() as camera:
        while True:
            # Get timestamp for filename
            now = datetime.now() #
            timestamp = now.strftime("%Y%m%d-%H%M%S")

            logging.info("capture: starting video capture {}".format(timestamp))

            # Record video
            camera.resolution = (1920, 1080)
            camera.rotation = 180
            camera.annotate_background = picamera.Color('black')
            video_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            camera.annotate_text = f"KE5GDB - PiBalloon5 - {video_timestamp}\n{get_gps_string()}"
            camera.start_recording('video/{}.h264'.format(timestamp))
            start = datetime.now()
            while (datetime.now() - start).seconds < video_length:
                video_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                camera.annotate_text = f"KE5GDB - PiBalloon5 - {video_timestamp}\n{get_gps_string()}"
                camera.wait_recording(0.2)

            camera.stop_recording()

            logging.info("capture: starting image capture {}".format(timestamp))

            # Capture image
            camera.resolution = (3280, 2464)
            camera.rotation = 180
            camera.start_preview()
            time.sleep(2)
            now = datetime.now() #
            timestamp = now.strftime("%Y%m%d-%H%M%S")
            camera.capture(f"images/img_{timestamp}.jpg")
            copy2(f"images/img_{timestamp}.jpg", "images/latest.jpg")


def gps_thread():
    global gps_info
    gpsd = gps(mode=WATCH_ENABLE|WATCH_NEWSTYLE) 
    while True:
        try:
            report = gpsd.next() #
            if report['class'] == 'TPV':
                gps_info[0] = getattr(report,'lat',0.0)
                gps_info[1] = getattr(report,'lon',0.0)
                gps_info[2] = getattr(report,'alt', 0.0)
                gps_info[3] = getattr(report,'speed','NaN')
                gps_info[4] = getattr(report,'climb','NaN')
        except:
            logging.error("GPS error!")

def get_gps_string():
    if gps_info[2] == 0.0:
        return "No GPS lock!"
    else:
        return f"Lat: {gps_info[0]:.4f}* Lon: {gps_info[1]:.4f}* Alt: {(gps_info[2] * 3.28084):.0f}ft"

def sstv_thread():
    # Button C
    ptt = DigitalInOut(board.D21)
    ptt.direction = Direction.OUTPUT
    ptt.drive_mode = DriveMode.PUSH_PULL
    while True:
        # Enter wait info here
        logging.error("SSTV: Converting image to .wav file")
        os.system("/usr/bin/convert images/latest.jpg -resize 320x240 sstv_image320.jpg")

        sstv_text = f"RWK/PHAB-17 / {(gps_info[2] * 3.28084):.0f}ft / KE5GDB"

        os.system(f"/usr/bin/convert  sstv_image320.jpg -gravity south \
          -stroke '#000C' -strokewidth 2 -pointsize 17 -annotate 0 '{sstv_text}' \
          -stroke  none   -fill white    -pointsize 17 -annotate 0 '{sstv_text}' \
          sstv_image.jpg")
        os.system("/usr/local/bin/pisstv -r 22050 -p m2 sstv_image.jpg")

        while datetime.now().minute % 3 != 0:
            time.sleep(0.5)

        logging.error("SSTV: Transmitting")
        ptt.value = 1
        time.sleep(1)
        os.system("aplay sstv_image.jpg.wav")
        time.sleep(0)
        ptt.value = 0
        logging.error("SSTV: Done transmitting")


if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"

    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

    threads=[]
    threads.append(threading.Thread(target=capture_thread, daemon=True))
    threads.append(threading.Thread(target=gps_thread, daemon=True))
    threads.append(threading.Thread(target=sstv_thread, daemon=True))

    for thread in threads:
        thread.start()

    #we need this thread to keep ticking
    while True:
        if not any([thread.isAlive() for thread in threads]):
            logging.info("Thread died!")
            break
        else:
            time.sleep(1)

    logging.info("All threads have terminated, exiting main thread...")
