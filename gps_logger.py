#!/usr/bin/python3

#
# KE5GDB 2021
# PiBalloonV GPS logger
#

import time
from datetime import datetime
import logging
import threading
from gps import *

gps_info = [0.0, 0.0, 'NaN', 'NaN', 'NaN']

def gps_thread():
    global gps_info
    gpsd = gps(mode=WATCH_ENABLE|WATCH_NEWSTYLE) 
    f = open("gps_log.csv", "a")
    while True:
        #try:
            report = gpsd.next()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if report['class'] == 'TPV':
                gps_info[0] = getattr(report,'lat',0.0)
                gps_info[1] = getattr(report,'lon',0.0)
                gps_info[2] = getattr(report,'alt','NaN')
                gps_info[3] = getattr(report,'speed','NaN')
                gps_info[4] = getattr(report,'climb','NaN')
                f.write(f"{timestamp},tpv,{gps_info[0]},{gps_info[1]},{gps_info[2]},{gps_info[3]},{gps_info[4]}\n")
                f.flush()
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

                f.write(f"{timestamp},sky,{hdop},{vdop},{sats[0]},{sats[1]}\n")
                f.flush()
        #except:
        #    logging.error("GPS error!")

    # we never reach this, but that's OK because we flush
    f.close()




if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"

    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

    threads=[]
    threads.append(threading.Thread(target=gps_thread, daemon=True))

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