import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DETECT_SCRIPT = ROOT_DIR / "pipeline" / "detect.py"

videos = [
    ROOT_DIR / "data" / "CCTV Footage" / "CAM 1.mp4",
    ROOT_DIR / "data" / "CCTV Footage" / "CAM 2.mp4",
    ROOT_DIR / "data" / "CCTV Footage" / "CAM 3.mp4",
    ROOT_DIR / "data" / "CCTV Footage" / "CAM 4.mp4",
    ROOT_DIR / "data" / "CCTV Footage" / "CAM 5.mp4",
]

processes = []

for video in videos:
    print(f"Starting {video}")

    p = subprocess.Popen([
        sys.executable,
        str(DETECT_SCRIPT),
        "--video",
        str(video),
        "--web"
    ], cwd=ROOT_DIR)

    processes.append(p)

    time.sleep(3)

for p in processes:
    p.wait()
