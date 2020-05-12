#!/bin/bash

# Set up script - best run from docker container 
# or a fully functional runtime environment

# Check the config is present
FN_CONFIG=src/biometric.cfg
if [[ ! -f "${FN_CONFIG}" ]]; then
  echo "Creating config file..."
  cd src && \
    python config_creator.py && \
    cd ..
fi

# Check the data dictionary is present
FN_DATADICT=data/data_dict.json
if [[ ! -f "${FN_DATADICT}" ]]; then
  echo "Creating data dictionary for db..."
  mkdir -p $(dirname "${FN_DATADICT}")
  cd src && \
    python data_dict.py && \
    cd ..
fi

# Obtain face detection model if missing
PN_FACEDETECT=models/face_detection_model
if [[ ! -d ${PN_FACEDETECT} ]]; then
  echo "Downloading pretrained face detection model..."
  mkdir -p ${PN_FACEDETECT} 
  wget -O ${PN_FACEDETECT}/deploy.prototxt https://raw.githubusercontent.com/vinuvish/Face-detection-with-OpenCV-and-deep-learning/master/models/deploy.prototxt.txt
  wget -O ${PN_FACEDETECT}/res10_300x300_ssd_iter_140000.caffemodel https://github.com/vinuvish/Face-detection-with-OpenCV-and-deep-learning/raw/master/models/res10_300x300_ssd_iter_140000.caffemodel
fi

# Obtain embedding model if missing
PN_OPENFACE=models/face_embedding_model
if [[ ! -d ${PN_OPENFACE} ]]; then
  echo "Downloading openface face embedding model..."
  mkdir -p ${PN_OPENFACE}
  wget -O ${PN_OPENFACE}/openface_nn4.small2.v1.t7 https://storage.cmusatyalab.org/openface-models/nn4.small2.v1.t7
fi

echo "Setup complete."
