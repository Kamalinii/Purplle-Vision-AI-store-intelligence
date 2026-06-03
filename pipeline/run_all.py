import subprocess
import sys
import time
from pathlib import Path

try:
    import msvcrt
except ImportError:
    msvcrt = None

ROOT_DIR = Path(__file__).resolve().parents[1]
DETECT_SCRIPT = ROOT_DIR / "pipeline" / "detect.py"

videos = [
    ROOT_DIR / "data" / "CCTV Footage" / "CAM 1.mp4",
    ROOT_DIR / "data" / "CCTV Footage" / "CAM 2.mp4",
    ROOT_DIR / "data" / "CCTV Footage" / "CAM 3.mp4",
    ROOT_DIR / "data" / "CCTV Footage" / "CAM 4.mp4",
    ROOT_DIR / "data" / "CCTV Footage" / "CAM 5.mp4",
]

def enter_pressed():
    if msvcrt is None:
        return False
    if not msvcrt.kbhit():
        return False
    key = msvcrt.getwch()
    return key in ("\r", "\n")

processes = []

for v in videos:
    print(f"Starting {v.name}")
    process = subprocess.Popen(
        [sys.executable, str(DETECT_SCRIPT), "--video", str(v), "--web"],
        cwd=ROOT_DIR
    )
    processes.append((v.name, process))

print("All cameras started. Open http://127.0.0.1:8000/dashboard")
print("Press Enter to stop...")

try:
    while True:
        for name, process in processes:
            code = process.poll()
            if code is not None:
                print(f"{name} stopped with exit code {code}")
                processes.remove((name, process))
        if not processes:
            break
        if enter_pressed():
            break
        time.sleep(1)
finally:
    for _, process in processes:
        process.terminate()
