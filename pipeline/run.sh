#!/bin/bash
echo "Running detection pipeline..."
python3 pipeline/detect.py --video data/CCTV\ Footage/CAM\ 1.mp4 --store ST1008
echo "Pipeline finished."
