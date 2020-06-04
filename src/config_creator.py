#! /usr/bin/env python
# Create config file for all scripts
import configparser
import os

config = configparser.ConfigParser()

biometric_dir = '/home/biom/biometric_camera_signin/'

# Init config
config['DEFAULT'] = {}

# System PW:
#config['DEFAULT']['pw_guestdb'] = 'ChangEmEPleasE'  # Comment to force manual entry

# Camera Settings
config['DEFAULT']['camera_rot'] = '90'
config['DEFAULT']['capture_interval'] = '0.5'
config['DEFAULT']['max_capture_length'] = '120'  # Max capture guest seconds
config['DEFAULT']['max_images'] = '60'  # Max capture guest images?
config['DEFAULT']['image_width'] = '600'

# Sign-in Options
# Display db clients table row entry when recognized
config['DEFAULT']['display_name'] = 'first_name'
# How sure are we that a face is present?
config['DEFAULT']['min_detec_conf'] = '0.50'
# How sure are we that a particular name is that face?
config['DEFAULT']['min_recog_prob'] = '0.70'
config['DEFAULT']['min_face_px'] = '(20, 20)'

# Path and filenames:
config['DEFAULT']['fn_meal_log_default'] = os.path.join(biometric_dir,
                                                        'meal_logs',
                                                        'meal_log.csv')
config['DEFAULT']['fn_guestdb'] = os.path.join(biometric_dir,
                                               'data',
                                               'biometric_db.sqlite')
config['DEFAULT']['fn_datadict'] = os.path.join(biometric_dir,
                                                'data',
                                                'data_dict.json')
config['DEFAULT']['pn_guest_images_archive'] = os.path.join(biometric_dir,
                                                            'data',
                                                            'guest_images.7z')

# Pretrained OpenCV caffe model for localizing faces
# Build instructions are here:
# https://github.com/opencv/opencv/tree/master/samples/dnn/face_detector
# It's also hosted here:
# https://github.com/vinuvish/Face-detection-with-OpenCV-and-deep-learning/tree/master/models
config['DEFAULT']['pn_detector_model'] = os.path.join(biometric_dir,
                                                      'models',
                                                      'face_detection_model')
config['DEFAULT']['detector_trainrgbavg'] = '(104.0, 177.0, 123.0)'
# Pretrained OpenCV Torch model for extracting facial embeddings from the OpenFace project
# Available at https://storage.cmusatyalab.org/openface-models/nn4.small2.v1.t7
config['DEFAULT']['fn_embedding_model'] = os.path.join(biometric_dir,
                                                       'models',
                                                       'face_embedding_model',
                                                       'openface_nn4.small2.v1.t7')

# Guest-specific datastore and models:
# Serialized faces with names
config['DEFAULT']['fn_serialized_embeddings'] = os.path.join(biometric_dir,
                                                             'models',
                                                             'guest_specific',
                                                             'embeddings.pickle')
# Label encoder
config['DEFAULT']['fn_label_encoder'] = os.path.join(biometric_dir,
                                                     'models',
                                                     'guest_specific',
                                                     'le.pickle')
config['DEFAULT']['fn_recognizer_model'] = os.path.join(biometric_dir,
                                                        'models',
                                                        'guest_specific',
                                                        'recognizer.pickle')

with open('biometric.cfg', 'w') as configfile:
    config.write(configfile)
