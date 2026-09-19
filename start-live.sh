#!/bin/bash
sudo modprobe -r v4l2loopback
sudo modprobe v4l2loopback exclusive_caps=1
.venv/bin/python main.py -m live -d v4l2loopback -a "./avatars/kanisan"
