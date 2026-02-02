#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Simple script to detect MediaTek (MTK) Preloader USB VCOM devices
# Listens for newly-enumerated serial ports and exits once an MTK
# Preloader / MediaTek USB device is detected.
#
# Depends on pyserial, otherwise fully cross-platform (Windows/Linux/macOS)
#
# Usage: python3 mtk-COMFinder.py
#
# The script will continuously poll available serial interfaces and
# look for known MTK identifiers (e.g. "MediaTek", "MTK", "Preloader",
# "USB VCOM") in the port description / hardware ID, or VID/PID of 0E8D.
#
# Once a matching device is found, the COM/TTY port name is printed
# (e.g. COM6, /dev/ttyUSB0, /dev/ttyACM0) and the script exits.
#
# Intended use cases:
#  - Detecting short-lived MTK Preloader ports
#  - Assisting with SP Flash Tool / mtkclient workflows
#  - Debugging MTK USB enumeration timing issues
#  - Figuring out which port/path to use with mtk-bootseq.py
#
# Note:
#  MTK Preloader ports may only exist for a very short time (often
#  less than one second). It is recommended to connect the device
#  powered off or via the appropriate key/test-point method.


import time
from serial.tools import list_ports

MTK_KEYWORDS = (
    "MediaTek",
    "MTK",
    "Preloader",
    "USB VCOM"
)

MTK_VID = 0x0E8D  # MediaTek USB VID


def find_mtk_preloader(poll_interval=0.002):
    print("Waiting for MTK Preloader device...")

    seen_ports = set()

    while True:
        ports = list_ports.comports()

        for port in ports:
            port_id = (port.device, port.hwid)

            if port_id in seen_ports:
                continue

            seen_ports.add(port_id)

            desc = (port.description or "") + " " + (port.hwid or "")

            # Check keywords
            keyword_match = any(keyword.lower() in desc.lower() for keyword in MTK_KEYWORDS)

            # Check VID/PID
            vid_pid_match = False
            if port.vid is not None and port.pid is not None:
                if port.vid == MTK_VID:
                    vid_pid_match = True

            if keyword_match or vid_pid_match:
                print(f"MTK Preloader detected on {port.device}")
                return port.device

        time.sleep(poll_interval)


if __name__ == "__main__":
    find_mtk_preloader()
