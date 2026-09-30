#!/bin/bash
sudo modprobe -r v4l2loopback
sudo modprobe v4l2loopback exclusive_caps=1 devices=1 video_nr=9 max_buffers=2
motion-mask -m live -d /dev/video9 -a "./avatars/kanisan"
