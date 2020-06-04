# Imports
from ast import literal_eval as make_tuple
import configparser
import os
import time

from PIL import Image
import cv2
import imutils
import numpy as np

from encrypt_archive import p7zip

fn_config = 'biometric.cfg'


class FacialCamera:
    def __init__(self, pn_output="./"):
        """ Initialize application which uses OpenCV + Tkinter. It displays
            a video stream in a Tkinter window and stores current snapshot on
            disk. """
        # Initialize the video stream, then allow the camera sensor to warm up
        print("[INFO] starting video stream...")
        self.vs = cv2.VideoCapture(0)  # Capture video frames, 0 is default video camera
        time.sleep(2.0)

        # Load config
        config = configparser.ConfigParser()
        config.read(fn_config)
        self.pn_guest_images = config['DEFAULT']['pn_guest_images_archive']
        self.guest_archive = p7zip(self.pn_guest_images)
        self.camera_rot = int(config['DEFAULT']['camera_rot'])
        self.image_width = int(config['DEFAULT']['image_width'])
        self.max_capture_interval = float(config['DEFAULT']['capture_interval'])
        self.max_capture_length = int(config['DEFAULT']['max_capture_length'])
        self.max_images = int(config['DEFAULT']['max_images'])

        # Capture Vars
        self.curr_pic = None  # Current image from the camera
        self.gst_capture = None
        self.start_time = time.time()
        self.save_time = time.time()
        self.pic_num = None
        self.pn_gstcap_out = None

        # Face Detection Model
        self.min_detec_conf = float(config['DEFAULT']['min_detec_conf'])
        self.min_face_px = make_tuple(config['DEFAULT']['min_face_px'])
        pn_detector_model = config['DEFAULT']['pn_detector_model']
        self.trainRBGavg = make_tuple(config['DEFAULT']['detector_trainrgbavg'])
        print("[INFO] loading face detector and embedding model...")
        protoPath = os.path.sep.join([pn_detector_model, "deploy.prototxt"])
        modelPath = os.path.sep.join([pn_detector_model,
                                      "res10_300x300_ssd_iter_140000.caffemodel"])
        self.detector = cv2.dnn.readNetFromCaffe(protoPath, modelPath)
        self.detector.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        # Face Recognition (extract/recognize embeddings) Model
        self.min_recog_prob = float(config['DEFAULT']['min_recog_prob'])
        fn_embedding_model = config['DEFAULT']['fn_embedding_model']
        self.embedder = cv2.dnn.readNetFromTorch(fn_embedding_model)
        self.embedder.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self.gst_identify = False
        self.guest_ids = {}

        # Guest Info (update outside of function)
        self.known_guest_meta = None

    def query_camera(self):
        """
        Query camera for current image.
        """
        ok, orig_pic = self.vs.read()  # Read video stream
        if ok:  # If no errors
            orig_pic = imutils.rotate(orig_pic, angle=self.camera_rot)
            curr_pic = imutils.resize(orig_pic, width=self.image_width)
            return curr_pic, orig_pic
        else:
            return None, None

    def convert_imgpil(self, pic):
        """
        Convert image to something that can be saved.
        """
        curr_pic = cv2.cvtColor(pic, cv2.COLOR_BGR2RGBA)
        return Image.fromarray(curr_pic)  # Convert image for PIL

    def save_pic(self, path_pic, pic):
        """
        Save image to disk.
        """
        path_dir = os.path.dirname(path_pic)
        if not os.path.exists(path_dir):
            print("[INFO] Directory \"{}\" does not exist, creating..."
                  .format(path_dir))
            os.makedirs(path_dir)

        cv2.imwrite(path_pic, pic)

    def save_pic_archive(self, path_pic, pic):
        """
        Save image to archive on disk.
        """
        self.guest_archive.add_image(path_pic, pic)

    def guest_capture_func(self, pic_save, pic_display):
        """
        Capture guest (capture images to be trained upon in
        separate step).
        """
        capture_time_curr = time.time()
        (pic_height, pic_width) = pic_display.shape[:2]
        image_blob = cv2.dnn.blobFromImage(
            cv2.resize(pic_display, (300, 300)),
            1.0,
            (300, 300),
            self.trainRBGavg,
            swapRB=False,
            crop=False)

        # Use previously loaded face detector on the blob
        self.detector.setInput(image_blob)
        detections = self.detector.forward()

        # Loop over detected faces
        for i in range(0, detections.shape[2]):
            curr_conf = detections[0, 0, i, 2]
            if curr_conf > self.min_detec_conf:
                bound_box = detections[0, 0, i, 3:7] * np.array([pic_width,
                                                                 pic_height,
                                                                 pic_width,
                                                                 pic_height])
                (x_start, y_start, x_end, y_end) = bound_box.astype("int")
                # Only detect faces fully in the frame
                if x_start < 0 or y_start < 0:
                    continue
                if x_end > self.image_width or y_end > self.image_width:
                    continue
                # Draw face bounding box
                cv2.rectangle(pic_display,
                              (x_start, y_start),
                              (x_end, y_end),
                              (0, 255, 0),
                              2)

        elap_seconds = capture_time_curr - self.capture_time_prev
        if elap_seconds >= self.max_capture_interval and \
                np.any(detections[0, 0, :, 2] > self.min_detec_conf):
            # Capture image and save to file
            pn_pic = os.path.sep.join([self.pn_gstcap_out, "{}.png".format(
                str(self.pic_num).zfill(5))])
            self.save_pic_archive(pn_pic, pic_save)
            self.pic_num += 1
            self.capture_time_prev = capture_time_curr
            print("[INFO] Saved image {}.".format(self.pic_num))

            if capture_time_curr - self.start_time > self.max_capture_length:
                print('[INFO] {} seconds elapsed, completed capturing images.'
                      .format(self.max_capture_length))
                self.gst_capture = False

            if self.pic_num >= self.max_images:
                print('[INFO] Max of {} images captured, completed capturing images.'
                      .format(self.max_images))
                self.gst_capture = False

        return pic_display

    def determine_guest_info(self, known_guest_meta, guest_id):
        """
        Return guest metadata (if available).
        """
        if known_guest_meta is not None:
            if guest_id in known_guest_meta:
                guest_info = known_guest_meta[guest_id]
            else:
                print('[ERROR] {} not in guest trained data. '
                      'Please delete the folder {}/{} and '
                      'run "Embed & Train" again.'
                      .format(guest_id, self.pn_guest_images, guest_id))
                guest_info = 'No Guest Info'
        else:
            print('[ERROR] Guest data not present.')
            guest_info = 'Guest Data Load Error'
        return guest_info

    def guest_identify_func(self, pic_display):
        """
        Identify guests within a picture.
        """
        (pic_height, pic_width) = pic_display.shape[:2]

        # Create OpenCV image blob
        image_blob = cv2.dnn.blobFromImage(
            cv2.resize(pic_display, (300, 300)),
            1.0,
            (300, 300),
            self.trainRBGavg,
            swapRB=False,
            crop=False)

        # Use previously loaded face detector on the blob
        self.detector.setInput(image_blob)
        detections = self.detector.forward()

        self.guest_ids = {}
        for i in range(0, detections.shape[2]):
            # Determine detection confidence
            curr_confidence = detections[0, 0, i, 2]

            # Threshold confidence via configuration file
            if curr_confidence > self.min_detec_conf:
                # Return bounding box (x,y)-coordinates
                bound_box = detections[0, 0, i, 3:7] * np.array([pic_width,
                                                                 pic_height,
                                                                 pic_width,
                                                                 pic_height])
                (x_start, y_start, x_end, y_end) = bound_box.astype("int")

                # Return face region of interest dimensions
                face = pic_display[y_start:y_end, x_start:x_end]

                # Skip faces below a min size
                (face_height, face_width) = face.shape[:2]
                if face_height < self.min_face_px[0] \
                   or face_width < self.min_face_px[1]:
                    continue
                # Only detect faces fully in the frame
                if x_start < 0 or y_start < 0:
                    continue
                if x_end > self.image_width or y_end > self.image_width:
                    continue

                # Create OpenCV blob for face region of interest
                face_blob = cv2.dnn.blobFromImage(cv2.resize(face, (96, 96)),
                                                  1.0 / 255,
                                                  (96, 96),
                                                  (0, 0, 0),
                                                  swapRB=True,
                                                  crop=False)
                # Pass face blob into embedder,
                # return 128-D describing vector
                self.embedder.setInput(face_blob)
                face_vec = self.embedder.forward()

                # Use previously loaded recognizer on the face blob
                # to recognize the face
                preds = self.recognizer.predict_proba(face_vec)[0]
                max_pred_ind = np.argmax(preds)
                prob = preds[max_pred_ind]
                guest_id = self.label_encoder.classes_[max_pred_ind]

                # Filter out low classification probabilies
                # I.e. camera images must have a facial detection
                # of min_detect_conf and facial recognition
                # classification probability of min_recog_prob

                #print(curr_confidence,  # Keep for optimizing the detect/recog %
                #      prob,
                #      self.determine_guest_info(self.known_guest_meta,
                #                                guest_id))
                if prob >= self.min_recog_prob:
                    # Store guest_id info as dict of {guest_id:prob}
                    self.guest_ids[guest_id] = round(prob, 4)

                    # Print guest_info from known_guest_meta data
                    guest_info = self.determine_guest_info(self.known_guest_meta,
                                                           guest_id)

                    # Write out guest_info and recog probability
                    text = "{:.2f}%: {}".format(round(prob*100, 2), guest_info)
                    y = y_start - 15 if y_start - 15 > 15 else y_start + 15
                    cv2.rectangle(pic_display,
                                  (x_start, y_start),
                                  (x_end, y_end),
                                  (17, 190, 252),
                                  2)
                    cv2.putText(pic_display,
                                text,
                                (x_start, y),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.45,
                                (17, 190, 252),
                                2)
        return pic_display  # Show the output frame

    def destructor(self):
        """ Destroy the root object and release all resources """
        cv2.destroyAllWindows()
