ARG BASE_CONTAINER=arm32v7/python:3.7.7-slim-buster@sha256:2694bf1a524f4ba1eec250220f72b74f02a73af305efe272f2884ca1e8394485
FROM $BASE_CONTAINER as build-stage

LABEL maintainer="Blake Fleischer <blakeflei@gmail.com>"

# General package builds
RUN sed -i -e 's/^/#/' /etc/apt/sources.list
RUN \
  echo 'deb http://httpredir.debian.org/debian buster main contrib' >> /etc/apt/sources.list && \
  echo 'deb-src http://httpredir.debian.org/debian buster main contrib' >> /etc/apt/sources.list && \
  echo 'deb http://httpredir.debian.org/debian buster-updates main contrib' >> /etc/apt/sources.list && \
  echo 'deb-src http://httpredir.debian.org/debian buster-updates main contrib' >> /etc/apt/sources.list && \
  echo 'deb http://security.debian.org/ buster/updates main contrib' >> /etc/apt/sources.list && \
  echo 'deb-src http://security.debian.org/ buster/updates main contrib' >> /etc/apt/sources.list

RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  # General Usage
  build-essential \
  pkg-config \
  tmux \
  unzip \
  vim \
  wget \
  # Building Software
  cmake \
  g++ \
  gfortran \
  tcl \
  # Image libraries
  libjpeg-dev \
  libpng16-16 \
  libtiff5-dev \
  # Video libraries
  libavcodec-dev \
  libavformat-dev \
  libswscale-dev \
  libv4l-dev \
  libx264-dev \
  libxvidcore-dev \
  # GUI libraries 
  libgtk2.0-dev \
  libgtk-3-dev \
  tk \
  # Computation libraries  
  libatlas-base-dev \
  # Encryption 
  libssl-dev \
  libsqlcipher-dev \
  && rm -rf /var/lib/apt/lists/*

# Install python libraries
# Done before building due to dependencies
WORKDIR /tmp
COPY requirements.txt requirements.txt
RUN pip install -v -r requirements.txt

# Build OpenCV
ENV OPENCV_VERSION=4.3.0
ARG BUILDDIR=/tmp/build/opencv
RUN mkdir -p $BUILDDIR
WORKDIR $BUILDDIR
RUN wget -O opencv-${OPENCV_VERSION}.zip https://github.com/opencv/opencv/archive/${OPENCV_VERSION}.zip
RUN unzip opencv-${OPENCV_VERSION}.zip
RUN wget -O opencv_contrib-${OPENCV_VERSION}.zip https://github.com/opencv/opencv_contrib/archive/${OPENCV_VERSION}.zip
RUN unzip opencv_contrib-${OPENCV_VERSION}.zip

RUN mkdir $BUILDDIR/opencv-${OPENCV_VERSION}/build
WORKDIR $BUILDDIR/opencv-${OPENCV_VERSION}/build
RUN  cmake -D CMAKE_BUILD_TYPE=RELEASE \
    -D CMAKE_INSTALL_PREFIX=/usr/local \
    -D OPENCV_EXTRA_MODULES_PATH=${BUILDDIR}/opencv_contrib-${OPENCV_VERSION}/modules \
    -D ENABLE_NEON=ON \
    -D ENABLE_VFPV3=ON \
    -D BUILD_TESTS=OFF \
    -D OPENCV_ENABLE_NONFREE=ON \
    -D CMAKE_SHARED_LINKER_FLAGS=-latomic \
    -D INSTALL_PYTHON_EXAMPLES=OFF \
    -D BUILD_EXAMPLES=OFF ..
RUN make -j4
RUN make install

FROM $BASE_CONTAINER as release
LABEL maintainer="Blake Fleischer <blakeflei@gmail.com>"

# Execute as non-root, create user/group
ARG B_USER="biom"
ARG B_UID=1000
ARG B_GROUP=${B_USER}
ARG B_GID=${B_UID}
RUN groupadd -r \
  -g ${B_GID} \
  ${B_GROUP} && \
  useradd -r \
  -m \
  -u ${B_UID} \
  -g ${B_GROUP} \
  ${B_USER}
# Add user to video group so can access camera
RUN usermod -a -G video ${B_USER}

# Copy OpenCV and Python shared objects from build-stage
COPY --from=build-stage /usr/local/lib /usr/local/lib
COPY --from=build-stage /usr/local/include /usr/local/include
COPY --from=build-stage /usr/lib/arm-linux-gnueabihf /usr/lib/arm-linux-gnueabihf

ENV PKG_CONFIG_PATH /usr/local/lib/pkgconfig
ENV LD_LIBRARY_PATH /usr/local/lib:/usr/lib/arm-linux-gnueabihf/atlas
ENV CGO_CPPFLAGS -I/usr/local/include

RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  gosu \
  libkeyutils1 \
  tcl \
  tk \
  tmux \
  vim \
  wget \
  xorg \
  && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /home/${B_USER}
ENTRYPOINT ["entrypoint.sh"]
