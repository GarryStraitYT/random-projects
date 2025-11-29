import os
import tempfile
import requests
import subprocess
import time

# ---------------------------
# Device Detection Functions
# ---------------------------
def run(cmd):
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return None, None

def adb_device_present():
    out, _ = run(["adb", "devices"])
    if out is None:
        return False
    for line in out.splitlines()[1:]:
        if line.strip().endswith("device"):
            return True
    return False

def detect_oneplus_n200_adb():
    out, _ = run(["adb", "shell", "getprop"])
    if out is None:
        return False
    for line in out.splitlines():
        if "ro.product.name" in line and "OnePlusN200" in line:
            return True
    return False

def fastboot_device_present():
    out, err = run(["fastboot", "devices"])
    combined = (out or "") + (err or "")
    return bool(combined.strip())

def detect_fastboot_mode():
    out, err = run(["fastboot", "getvar", "is-userspace"])
    combined = (out or "") + (err or "")
    low = combined.lower()
    if "is-userspace: yes" in low:
        return "fastbootd"
    if "is-userspace: no" in low:
        return "bootloader"
    return "unknown"

def ensure_fastbootd():
    print("\n=== Ensuring fastbootd ===")
    while True:
        mode = detect_fastboot_mode()
        if not fastboot_device_present():
            print("No fastboot device detected.")
            return False
        if mode == "fastbootd":
            print("✔ Device is in fastbootd (userspace).")
            return True
        if mode == "bootloader":
            print("↻ Device is in bootloader fastboot. Rebooting to fastbootd...")
            run(["fastboot", "reboot", "fastboot"])
            print("Waiting 15 seconds for fastbootd...")
            time.sleep(15)
            continue
        print("⚠ Unknown fastboot mode. Retrying in 3s...")
        time.sleep(3)

def detect_oneplus_n200_fastboot():
    out, err = run(["fastboot", "getvar", "all"])
    combined = (out or "") + (err or "")
    for line in combined.splitlines():
        if "system-fingerprint" in line.lower() and "oneplusn200" in line.lower():
            return True
    return False

# ---------------------------
# Download & Extract Functions
# ---------------------------
FILES = [
    "abl.img.zst", "bluetooth.img.zst", "core_nhlos.img.zst", "devcfg.img.zst",
    "dsp.img.zst", "featenabler.img.zst", "hyp.img.zst", "imagefv.img.zst",
    "keymaster.img.zst", "logo.img.zst", "modem.img.zst", "oplusstanvbk.img.zst",
    "qupfw.img.zst", "rpm.img.zst", "tz.img.zst", "uefisecapp.img.zst",
    "xbl_config.img.zst", "xbl.img.zst"
]

BASE_URL = "https://github.com/elginsk8r/oplus_archive/releases/download/DE2117_11_C.37/"

def download_files(file_list):
    tmp_dir = tempfile.mkdtemp(prefix="oplus_download_")
    print(f"[+] Temporary download directory: {tmp_dir}")
    for filename in file_list:
        url = BASE_URL + filename
        dest_path = os.path.join(tmp_dir, filename)
        if os.path.exists(dest_path):
            continue
        print(f"[*] Downloading {filename}...")
        resp = requests.get(url, stream=True)
        if resp.status_code != 200:
            print(f"[-] Failed to download {filename}: HTTP {resp.status_code}")
            continue
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"[+] Downloaded {filename}")
    return tmp_dir

def extract_zst_files(directory):
    for filename in os.listdir(directory):
        if filename.endswith(".zst"):
            zst_path = os.path.join(directory, filename)
            out_path = os.path.join(directory, filename[:-4])
            print(f"[*] Extracting {filename} -> {out_path}")
            cmd = ["zstd", "-d", "-f", zst_path, "-o", out_path]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                print(f"[-] Failed to extract {filename}: {result.stderr}")
            else:
                print(f"[+] Extracted {filename}")

# ---------------------------
# Flashing Logic
# ---------------------------
FLASH_COMMANDS = [
    ("abl", "abl.img"),
    ("bluetooth", "bluetooth.img"),
    ("core_nhlos", "core_nhlos.img"),
    ("devcfg", "devcfg.img"),
    ("dsp", "dsp.img"),
    ("featenabler", "featenabler.img"),
    ("hyp", "hyp.img"),
    ("imagefv", "imagefv.img"),
    ("keymaster", "keymaster.img"),
    ("logo", "logo.img"),
    ("modem", "modem.img"),
    ("oplusstanvbk", "oplusstanvbk.img"),
    ("qupfw", "qupfw.img"),
    ("rpm", "rpm.img"),
    ("tz", "tz.img"),
    ("uefisecapp", "uefisecapp.img"),
    ("xbl_config", "xbl_config.img"),
    ("xbl", "xbl.img"),
]

def flash_images(directory):
    print("\n=== Flashing images ===")
    if not detect_oneplus_n200_fastboot():
        print("[-] Device is no longer detected as OnePlus N200! Aborting.")
        return

    for partition, img_file in FLASH_COMMANDS:
        path = os.path.join(directory, img_file)
        if not os.path.exists(path):
            print(f"[-] File missing: {img_file}. Skipping.")
            continue
        cmd = ["fastboot", "flash", "--slot=all", partition, path]
        print(f"[*] Flashing {partition} -> {img_file}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"[-] Failed to flash {partition}: {result.stderr}")
        else:
            print(f"[+] Successfully flashed {partition}")

# ---------------------------
# Main Flow
# ---------------------------
def main():
    import sys

    # ---- Disclaimer ----
    def print_disclaimer():
        disclaimer = """
================================================================================
⚠ WARNING — READ CAREFULLY ⚠

I am providing this resource on the condition that you, the end user, know what 
you are doing and know how to recover if/when something were to go wrong. I am 
not responsible for your actions, which include but are not limited to choosing 
to download and/or use this script. 

You, by being the one using the script, accept that I, the developer, will take 
no responsibility in the event the device or ROM bricks, and I am not required 
to assist in debricking or to provide the debricking service for free. I am 
additionally not required to provide updates to the script, provided that it 
functions as intended. However, I will say that this script does work, as I 
have tested it myself.

By proceeding, you accept full responsibility for any outcome.
================================================================================

NOTICE: During testing, the device exhibited behavior where it automatically 
wiped the /data/app folder and all application data, while returning the device 
to the Out-Of-Box Experience (OOBE). Userdata and root modules were preserved. 
This may be related to an internal device-protection mechanism, though this 
cannot be guaranteed. 

Regardless, back up all data beforehand to prevent any data loss. If you fail 
to do so, I will not be responsible for any lost work, data, or time.
"""
        print(disclaimer)

    # ---- Print disclaimer and prompt user ----
    print_disclaimer()
    proceed = input("Do you want to continue? (yes/[no]): ").strip().lower()
    if proceed != "yes":
        print("Aborted by user.")
        sys.exit(0)

    print("\n=== OnePlus N200 C.37 Blobs Autoflasher ===\n")
    print("\n=== Starting Device Detection Logic ===\n")

    # ---- ADB Mode ----
    if adb_device_present():
        print("[*] Device detected in ADB mode.")
        if detect_oneplus_n200_adb():
            print("✔ Device is a OnePlus N200 (ADB mode). Rebooting to fastbootd...")
            run(["adb", "reboot", "fastboot"])
            time.sleep(15)
            ensure_fastbootd()
        else:
            print("✘ ADB device detected, but it is NOT a OnePlus N200.")
            return  # valid here because we're inside main()

    # ---- Fastboot / Fastbootd Mode ----
    if fastboot_device_present():
        print("[*] Device detected in fastboot mode.")
        ensure_fastbootd()  # enforce fastbootd before detection
        if not detect_oneplus_n200_fastboot():
            print("✘ Fastbootd device detected, but NOT a OnePlus N200. Aborting.")
            return
        print("✔ Device confirmed as OnePlus N200 in fastbootd.")

    # ---- Download and extract blobs ----
    print("\n=== Downloading Needed Update Files ===\n")
    tmp_dir = download_files(FILES)
    extract_zst_files(tmp_dir)

    # ---- Flash all images ----
    print("\n=== Flashing Update Files ===\n")
    flash_images(tmp_dir)

    # ---- Cleanup temp directory ----
    print(f"[*] Cleaning up temporary files: {tmp_dir}")
    import shutil
    shutil.rmtree(tmp_dir)
    print("[+] Cleanup complete.")
    print("Rebooting Device")
    run(["fastboot", "reboot"])
    print("\n[+] All done.")


if __name__ == "__main__":
    main()
