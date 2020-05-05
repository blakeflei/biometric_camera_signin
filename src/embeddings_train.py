# Imports
from ast import literal_eval as make_tuple
import configparser
import os
import pickle

from imutils import paths
from sklearn.model_selection import GridSearchCV
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC
import numpy as np
import imutils
import cv2

fn_config = 'biometric.cfg'


class ModelTrain:
    def __init__(self):
        """
        Initialize training and modeling steps
        """
        # Load config
        config = configparser.ConfigParser()
        config.read(fn_config)
        self.pn_guest_images = config['DEFAULT']['pn_guest_images']
        self.image_width = int(config['DEFAULT']['image_width'])

        # External pre-trained models
        self.min_detec_conf = float(config['DEFAULT']['min_detec_conf'])
        self.min_face_px = make_tuple(config['DEFAULT']['min_face_px'])
        self.pn_detector_model = config['DEFAULT']['pn_detector_model']
        self.trainRBGavg = make_tuple(config['DEFAULT']['detector_trainrgbavg'])
        self.fn_embedding_model = config['DEFAULT']['fn_embedding_model']

        # Paramerters determined from specific users trained with this system
        self.fn_serialized_embeddings = config['DEFAULT']['fn_serialized_embeddings']
        self.fn_recognizer_model = config['DEFAULT']['fn_recognizer_model']
        self.fn_label_encoder = config['DEFAULT']['fn_label_encoder']

    def extract_embeddings(self):
        """
        Determine and embed {guest_id: embedding} in a pickle file.
        Embeddings are drawn from a ROI determined via facial detection.
        """
        # Load serialized face detector from disk
        print("[INFO] Loading face detector...")
        protoPath = os.path.sep.join([self.pn_detector_model,
                                      "deploy.prototxt"])
        modelPath = os.path.sep.join([self.pn_detector_model,
                                      "res10_300x300_ssd_iter_140000.caffemodel"])
        detector = cv2.dnn.readNetFromCaffe(protoPath, modelPath)
        detector.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        # Load serialized face embedding model, set the
        # preferable target to CPU for raspberry Pi
        print("[INFO] Loading face recognizer...")
        embedder = cv2.dnn.readNetFromTorch(self.fn_embedding_model)
        embedder.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        # Determine image paths to the input images
        print("[INFO] Quantifying faces...")
        image_paths = list(paths.list_images(self.pn_guest_images))

        # Init extracted facial embeddings and
        # corresponding guest_ids
        guest_embeddings = []
        guest_ids = []

        # Total processed faces
        total_proc_faces = 0

        # Resize, detect largest face, and embed the largest
        # face in each image.
        for (i, image_path) in enumerate(image_paths):
            print("[INFO] Processing image {}/{}".format(i + 1,
                                                         len(image_paths)))
            guest_id = os.path.basename(os.path.dirname(image_path))
            image = cv2.imread(image_path)
            try:
                image = imutils.resize(image, width=600)
            except Exception as e:
                print("Error in {}:".format(image_path))
                print(e)
                print("Skipping...")
                continue
            (image_height, image_width) = image.shape[:2]

            # Create OpenCV image blob
            image_blob = cv2.dnn.blobFromImage(cv2.resize(image,
                                                          (int(self.image_width/2),
                                                           int(self.image_width/2))),
                                               1.0,
                                               (int(self.image_width/2), int(self.image_width/2)),
                                               self.trainRBGavg,
                                               swapRB=False,
                                               crop=False)

            # Use previously loaded face detector on the blob
            detector.setInput(image_blob)
            detections = detector.forward()

            # If at least one face
            if len(detections) > 0:
                # Assume one face per image;
                # use bounding box with largest confidence
                max_conf_ind = np.argmax(detections[0, 0, :, 2])
                confidence = detections[0, 0, max_conf_ind, 2]

                # Threshold confidence via configuration file
                if confidence > self.min_detec_conf:
                    # Return bounding box (x, y)-coordinates
                    bound_box = detections[0, 0, max_conf_ind, 3:7] * np.array([image_width,
                                                                                image_height,
                                                                                image_width,
                                                                                image_height])
                    (x_start, y_start, x_end, y_end) = bound_box.astype("int")

                    # Return face region of interest dimensions
                    face = image[y_start: y_end, x_start: x_end]

                    # Skip faces below a min size
                    (face_height, face_width) = face.shape[:2]
                    if face_height < self.min_face_px[0] \
                       or face_width < self.min_face_px[1]:
                        continue

                    # Create OpenCV blob for face ROI
                    face_blob = cv2.dnn.blobFromImage(face,
                                                      1.0 / 255,
                                                      (96, 96),
                                                      (0, 0, 0),
                                                      swapRB=True,
                                                      crop=False)
                    # Pass face blob into embedder,
                    # return 128-D describing vector
                    embedder.setInput(face_blob)
                    face_vec = embedder.forward()

                    # Append guest_id and embedding
                    guest_ids.append(guest_id)
                    guest_embeddings.append(face_vec.flatten())
                    total_proc_faces += 1

        # Save embedding and guest_id to disk
        print("[INFO] Serializing {} encodings...".format(total_proc_faces))
        os.makedirs(os.path.dirname(self.fn_serialized_embeddings),
                    exist_ok=True)
        data = {"guest_embeddings": guest_embeddings, "guest_ids": guest_ids}
        with open(self.fn_serialized_embeddings, "wb") as f:
            f.write(pickle.dumps(data))

    def train_model(self):
        """
        Train a SVM to classify faces based on their enodings, output a label
        encoder model.
        """
        # Load prev embedded faces
        print("[INFO] Loading face embeddings...")
        data = pickle.loads(open(self.fn_serialized_embeddings, "rb").read())

        # Encode the labels per guest_id
        print("[INFO] Encoding labels...")
        label_encoder = LabelEncoder()
        labels = label_encoder.fit_transform(data["guest_ids"])

        # Train on the 128-d embeddings of the faces
        # to produce actual face recognition
        print("[INFO] Training model...")
        params = {"C": [10**x for x in range(-3, 6)],
                  "gamma": [10**x for x in range(2, -6, -1)]}
        model = GridSearchCV(SVC(kernel="rbf",
                                 gamma="auto",
                                 probability=True),
                             params,
                             cv=4,
                             n_jobs=-1)
        model.fit(data["guest_embeddings"], labels)
        print("[INFO] Best hyperparameters: {}".format(model.best_params_))

        # Save face recognition model to disk
        with open(self.fn_recognizer_model, "wb") as f:
            f.write(pickle.dumps(model.best_estimator_))

        # Save the label encoder to disk
        with open(self.fn_label_encoder, "wb") as f:
            f.write(pickle.dumps(label_encoder))
