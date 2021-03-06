#!/bin/bash

# Start script for application.
# Mounts a few volumes for x11, run scripts, and starts script.

# Assumes the desired camera id is 0 and the display is 0 (defaults).

docker run \
	--interactive \
	--tty \
	--rm \
	--env DISPLAY=:0.0 \
	--env TZ=$(cat /etc/timezone) \
	--volume /tmp/.X11-unix:/tmp/.X11-unix:ro \
	--volume ${HOME}/.Xauthority:/hom/biom/.Xauthority:ro \
	--volume /home/pi/biometric_camera_signin:/home/biom/biometric_camera_signin \
	--device=/dev/video0:/dev/video0 \
	--net=host \
	--workdir /home/biom/biometric_camera_signin/src \
	--name biometric_signin \
	blakeflei/arm32v7-biometric:20200604 \
	python start_gui.py
