
Biometric Camera Sign in
========================

An Python3 application to facilitate biometric sign in via an edge device with a camera. Developed on a Raspberry Pi 4.

This project came about from conversations with the Atlanta-based non-profit `SafeHouse Outreach <https://www.safehouseoutreach.org>`__, dedicated to `breaking the cycle of poverty <https://www.safehouseoutreach.org/about-us/>`__, which is apparent on just about any walk through downtown (Peachtree Center) Atlanta.

One service SafeHouse provides is a meal several times a week, and each time a list of guests (i.e.  individuals living on the streets) is required by the Georgia Department of Community Affairs `Homeless Management Information System (HMIS) <https://www.dca.ga.gov/safe-affordable-housing/homeless-special-needs-housing/homeless-management-information-system-hmis>`__. There are many repeat guests so in collaboration with SafeHouse, a biometric sign in device that could output list of guests (i.e. a meal log) was settled upon as a solution. 

A `Raspberry Pi 4 <https://www.raspberrypi.org/products/raspberry-pi-4-model-b/>`__ + `camera <https://www.raspberrypi.org/products/camera-module-v2/>`__ was used for development, but future iterations could leverage more powerful hardware like a `NVIDIA Jetson Nano <https://developer.nvidia.com/embedded/jetson-nano-developer-kit>`__.

Special thanks to SafeHouse for their support!

Installation
------------
Instructions assume a default 'pi' user and sources cloned into the home directory:

- Install Docker:
    ``curl -sSL https://get.docker.com | sh``

    More info is available `here <https://www.raspberrypi.org/blog/docker-comes-to-raspberry-pi/>`__.

- Clone the repo to the home directory with the commands::

    cd /home/pi

    git clone https://github.com/blakeflei/biometric_camera_signin.git

- Create default configuration and download pretrained models::

    docker run \
          --rm \
          -v /home/pi/biometric_camera_signin:/home/biom/biometric_camera_signin  \
          -w /home/biom/biometric_camera_signin \
          blakeflei/arm32v7-biometric:20200508 \
          bash biometric_setup.sh

- Start sign in app::

    cd /home/pi/biometric_cameeera_signin

    bash start.sh


Building the docker image:
While the dockerfile is available for building in the ``docker`` folder, arm32 libraries for python and opencv-4.3.0 aren't available via pip or debian buster repos, so the build process requires compilation and takes several hours.

A `docker image is available on docker hub <https://hub.docker.com/r/blakeflei/arm32v7-biometric>`__ and is recommended for use.

Dependencies
~~~~~~~~~~~~
While the python code is platform independent, the docker image presumes arm32 architecture.


References
~~~~~~~~~~
- `https://opencv.org/ <https://opencv.org/>`__
- `https://www.pyimagesearch.com/ <https://www.pyimagesearch.com/>`__
- `https://scikit-learn.org/stable/index.html <https://scikit-learn.org/stable/index.html>`__

License
~~~~~~~
BSD 3-Clause License. Please see LICENSE file.
