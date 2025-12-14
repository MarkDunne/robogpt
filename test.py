#!/usr/bin/env python3
import sys
import time
import os
import requests

robot_ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.100"
base_url = f"http://{robot_ip}"

# Test status
r = requests.get(f"{base_url}/api/status")
print(f"Status: {r.status_code} - {r.json()}")

# Test motors
for action in ["forward", "backward", "left", "right", "stop"]:
    r = requests.get(f"{base_url}/api/motor/{action}")
    time.sleep(1)
    print(f"Motor {action}: {r.status_code} - {r.json()}")

# Test camera and save
r = requests.get(f"{base_url}/api/camera/photo", timeout=10)
if r.status_code == 200:
    os.makedirs("photos", exist_ok=True)
    with open("photos/test_photo.jpg", "wb") as f:
        f.write(r.content)
    print(
        f"Camera: {r.status_code} - saved photos/test_photo.jpg ({len(r.content)} bytes)"
    )
else:
    try:
        error_msg = r.json()
        print(f"Camera: {r.status_code} - {error_msg}")
    except:
        print(f"Camera: {r.status_code} - FAILED ({r.text[:200]})")
