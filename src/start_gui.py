#! /usr/bin/env python

from pathlib import Path
from tkinter import filedialog
from tkinter import simpledialog
import configparser
import copy
import datetime
import glob
import json
import os
import pickle
import re
import shutil
import textwrap
import time
import tkinter as tk
import uuid

from PIL import ImageTk
from tkcalendar import DateEntry
import pandas as pd

from camera import FacialCamera as FC
from database import SignLog
from database import SignSS
from embeddings_train import ModelTrain as mt
import database

# Basic variables
fn_config = 'biometric.cfg'

gst_capture_off_txt = 'Import Guest\nVia Camera'
gst_capture_on_txt = 'Importing...'

gst_identify_off_txt = 'Identify Guest'
gst_identify_on_txt = 'Identifying...'

gst_embed_train_off_txt = 'Embed &\nTrain'
gst_embed_train_on_txt = 'Embedding &\nTraining...'
fc = FC()


class Application:
    def __init__(self, pn_output="./"):
        """
        Initialize application which uses OpenCV + Tkinter. It displays
        a video stream in a Tkinter window and stores current snapshot on
        disk.
        """

        self.pic_num = 0
        self.pn_gstcap_out = None

        # Load config
        config = configparser.ConfigParser()
        config.read(fn_config)
        self.pn_guest_images = config['DEFAULT']['pn_guest_images_archive']
        self.image_width = int(config['DEFAULT']['image_width'])
        self.display_name = config['DEFAULT']['display_name']
        self.fn_label_encoder = config['DEFAULT']['fn_label_encoder']
        self.fn_recognizer_model = config['DEFAULT']['fn_recognizer_model']
        self.fn_meal_log_default = config['DEFAULT']['fn_meal_log_default']
        os.makedirs(os.path.dirname(self.fn_meal_log_default), exist_ok=True)
        self.unknown_guest_id = '00000000-0000-0000-0000-000000000000'

        # Read in data dict:
        fn_datadict = config['DEFAULT']['fn_datadict']
        with open(fn_datadict) as f:
            self.datadict = json.load(f)
        self.datadict_menu = dict_dropdown(self.datadict)

        # Create reverse dict for db creation:
        self.datadict_rev = flip_dict(self.datadict)
        self.datadict_menu_rev = flip_dict(self.datadict_menu)

        # Sign In
        self.init_sign_in()
        self.guest_ids = {}
        self.signin_startstop = {'start_time': None, 'stop_time': None}

        # GUI Window initialization
        self.root = tk.Tk()  # initialize root window
        self.root.withdraw()

        # Collect password if not specified in config
        clear_db_history()
        fn_guestdb = config['DEFAULT']['fn_guestdb']
        if 'pw_guestdb' in config['DEFAULT']:
            pw_guestdb = config['DEFAULT']['pw_guestdb']
        else:
            if os.path.isfile(fn_guestdb):
                for pw_attempt in range(1, 8):
                    pw_guestdb = tk.simpledialog.askstring("Biometric Sign In Password",
                                                           "Please enter the Biometric Sign In password "
                                                           "(attempt {}/8):".format(pw_attempt),
                                                           show='*')

                    self.guestdb = database.db(password=pw_guestdb,
                                               dbname=fn_guestdb)

                    if self.guestdb.test_db_connection():
                        break
                    pw_attempt += 1
            else:  # No db exists, just need two successive PW entries
                pw_guestdb = ""
                pw_guestdb_prev = " "
                while (pw_guestdb != pw_guestdb_prev) or len(pw_guestdb) < 8:
                    pw_guestdb_prev = tk.simpledialog.askstring("Biometric Sign In Password",
                                                                "Creating a new database for Biometric Sign In.\n"
                                                                "Please enter a new password "
                                                                "(at least 8 characters):",
                                                                show='*')

                    pw_guestdb = tk.simpledialog.askstring("Biometric Sign In Password",
                                                           "Please re-enter the same password:",
                                                           show='*')
                    if pw_guestdb != pw_guestdb_prev:
                        tk.messagebox.showinfo(title="Biometric Sign In passwords don't match",
                                               message="Passwords don't match.\nPlease retry.")
                    if len(pw_guestdb) < 8:
                        tk.messagebox.showinfo(title="Biometric Sign In password too short",
                                               message="Password is less than 8 characters.\nPlease retry.")
                self.guestdb = database.db(password=pw_guestdb,
                                           dbname=fn_guestdb)

        # Guestdb password is used for guest images archive as well
        self.pw_guestdb = pw_guestdb
        fc.guest_archive.pw = self.pw_guestdb

        # Create db if it doesn't exist:
        if not os.path.isfile(fn_guestdb):
            print('[INFO] No prior {} database found, re-initializing.'
                  .format(fn_guestdb))
            self.guestdb.create_db_tables()

            unknown_guest = {'first_name': 'Unknown',
                             'middle_name': 'Unknown',
                             'last_name': 'Unknown',
                             'dob': '01/01/1900',
                             'race': 'Guest refused',
                             'ethnicity': 'Guest refused',
                             'gender': 'Guest refused',
                             'fr_id': self.unknown_guest_id}
            guest_meta = database.hmisv17_newguestdiag(unknown_guest,
                                                       self.datadict_menu_rev)
            self.guestdb.add_guest(guest_meta)
        else:  # Check db pw is correct before proceeding
            if not self.guestdb.test_db_connection():
                tk.messagebox.showinfo(title="Incorrect Biometric Sign In Password", message="Incorrect Biometric Sign In password, closing.")
                self.destructor
                exit(1)

        # Create guest_images archive if it doesn't exist:
        if not os.path.isfile(fc.guest_archive.fn_archive):
            unknown_guest_img_path = tk.filedialog.askdirectory(parent=self.root,
                                                                initialdir=os.getcwd(),
                                                                title='Please select a directory for unknown guest images.')
            pns_unknown_guest_img = glob.glob(os.path.join(unknown_guest_img_path,
                                                           '*'))
            # Create a temp directory for unknown guest images so the
            # archive is structured correctly:
            print('[INFO] Creating {} and storing unknown guest faces...'
                  .format(fc.guest_archive.fn_archive))
            os.makedirs(self.unknown_guest_id,
                        exist_ok=True)
            [shutil.copy(x, os.path.join(self.unknown_guest_id,
                                         os.path.basename(x))) for x in pns_unknown_guest_img]
            pns_unknown_guest_img_copy = glob.glob(os.path.join(self.unknown_guest_id,
                                                                '*'))
            fc.guest_archive.add_file(pns_unknown_guest_img_copy)
            shutil.rmtree(os.path.join(unknown_guest_img_path,
                                       self.unknown_guest_id),
                          ignore_errors=True)

        # Refocus on main window
        self.root.deiconify()
        self.root.title("Biometric Sign In")  # set window title

        # self.destructor function gets fired when the window is closed
        self.root.protocol('WM_DELETE_WINDOW', self.destructor)

        # Check for faces in unknown folder
        fns_unknown_guest = fc.guest_archive.list_files()
        fns_unknown_guest = [x for x in fns_unknown_guest
                             if os.path.dirname(x) == self.unknown_guest_id]
        if not fns_unknown_guest:
            tk.messagebox.showwarning(
                "No Unknown Images",
                "No images of unknown faces.\n"
                "Please restart and select a folder of unknown guest faces.",
                parent=self.root)

        # Set up GUI canvas and panel
        self.panel = tk.Label(self.root)  # initialize image panel
        self.panel.grid(row=0, column=0, columnspan=4)

        self.index = ['True']
        self.b_capture_text = [gst_capture_off_txt]
        self.b_identify_text = [gst_identify_off_txt]
        self.b_encode_text = [gst_embed_train_off_txt]

        # Buttons
        self.b_capture = tk.Button(self.root,
                                   width=10,
                                   height=2,
                                   text=gst_capture_off_txt,
                                   command=self.guest_capture_init,
                                   padx=10,
                                   pady=10)
        self.b_capture.grid(row=1, column=0)

        self.b_identify = tk.Button(self.root,
                                    width=10,
                                    height=2,
                                    text=gst_identify_off_txt,
                                    command=self.guest_identify_init,
                                    padx=10,
                                    pady=10)
        self.b_identify.grid(row=1, column=1)

        self.b_encode = tk.Button(self.root,
                                  width=10,
                                  height=2,
                                  text=gst_embed_train_off_txt,
                                  command=self.embed_train_init,
                                  padx=10,
                                  pady=10)
        self.b_encode.grid(row=1, column=2)

        self.b_save = tk.Button(self.root,
                                width=10,
                                height=2,
                                text='Meal Log\nExport',
                                command=self.init_meal_log,
                                padx=10,
                                pady=10)
        self.b_save.grid(row=1, column=3)

        # Start a self.video_loop that constantly polls the video sensor
        # for the most recently read frame
        self.video_loop()

    def video_loop(self):
        """
        Get frame from the video stream and show it in Tkinter.
        """
        curr_pic, orig_pic = fc.query_camera()

        if curr_pic is not None:
            if fc.gst_capture:  # Capture images for training
                curr_pic = fc.guest_capture_func(orig_pic, curr_pic)
            elif fc.gst_identify:  # Identify individuals
                curr_pic = fc.guest_identify_func(curr_pic)

                # Append new guest ids:
                self.guest_ids = fc.guest_ids
                # Drop 'unknown' guest id:
                self.guest_ids.pop(self.unknown_guest_id, None)
                # Drop users already signed in:
                if not self.sign_in.empty:
                    for curr_id in self.sign_in['fr_id']:
                        self.guest_ids.pop(curr_id, None)

                if self.guest_ids:
                    self.sign_in = self.sign_in.append(pd.DataFrame({'fr_id': list(self.guest_ids.keys()),
                                                                     'class_prob': list(self.guest_ids.values()),
                                                                     'time': datetime.datetime.now(),
                                                                     'first_time': 0}))
            else:  # Not doing anything crazy or cool, just showing webcam
                pass

            # Reset buttons
            if not fc.gst_capture:
                self.b_capture['text'] = gst_capture_off_txt
            if not fc.gst_identify:
                self.b_identify['text'] = gst_identify_off_txt

            # Record ids in image:
            self.curr_pic = fc.convert_imgpil(curr_pic)
            imgtk = ImageTk.PhotoImage(image=self.curr_pic)  # convert image for tkinter
            self.panel.imgtk = imgtk  # anchor imgtk so it does not be deleted by garbage-collector
            self.panel.config(image=imgtk)  # show the image

            # Poll every 10 seconds to write to db:
            elap_seconds = time.time() - fc.save_time
            if elap_seconds > 10 and fc.gst_identify:
                self.update_signin()
                #    #self.fps.update()
                #    #print("[INFO] approx. FPS: {:.2f}".format(self.fps.fps()))

        self.root.after(30, self.video_loop)  # call the same function after 30 milliseconds

    def guest_capture_init(self):
        """
        Initialize guest_capture function, which is called in the main loop.
        """
        b_capture_idx_dict = {gst_capture_off_txt: gst_capture_on_txt,
                              gst_capture_on_txt: gst_capture_off_txt}
        self.b_capture_text[0] = b_capture_idx_dict[self.b_capture_text[0]]
        self.b_capture['text'] = self.b_capture_text[0]
        if self.b_capture['text'] == gst_capture_off_txt:
            print('[INFO] Stopped repetitive image capture.')
            fc.gst_capture = False

        elif self.b_capture['text'] == gst_capture_on_txt:
            # Determine new guest ID for internal biometric purpose only
            gst_id = str(uuid.uuid4())
            print('[INFO] Starting new guest intake and repetitive image capture...')
            fc.gst_capture = True

            # Reset FacialCamera variables:
            fc.start_time = time.time()
            fc.pic_num = 0
            fc.capture_time_prev = time.time()

            fc.pn_gstcap_out = gst_id

            # Reset Sign In Dataframe Initialization:
            self.init_sign_in()

            # Capture new guest information
            guest_meta = NewGuestDialog(self.root,
                                        title='New Guest Information',
                                        datadict=self.datadict_menu_rev).result

            if not guest_meta:
                print('[INFO] Canceled new guest intake.')
                self.guest_capture_init()
                return

            guest_meta = database.hmisv17_newguestdiag(guest_meta,
                                                       self.datadict_menu_rev)
            guest_meta['fr_id'] = gst_id
            first_time = guest_meta.pop('first_time')  # Record new_guest and drop from guest_meta
            self.guestdb.add_guest(guest_meta)
            print('[INFO] User {} added to db.'.format(guest_meta['fr_id']))
            # Update SignLog
            self.init_sign_in()
            self.sign_in = self.sign_in.append(pd.DataFrame({'fr_id': [gst_id],
                                                             'class_prob': [1.0],
                                                             'time': [datetime.datetime.now()],
                                                             'first_time': [first_time]}))
            self.update_signin()

    def init_sign_in(self):
        """
        Initialize the sign in dataframe using columns from the SignLog
        table.
        """
        self.sign_in = pd.DataFrame(columns=SignLog.__table__.columns.keys()[1:])
        self.sign_in_saved = self.sign_in.copy()

        self.signin_startstop = dict(zip(SignSS.__table__.columns.keys(),
                                         [None for x in SignSS.__table__.columns.keys()]))

    def update_signin(self):
        """
        Update database with those who have signed in.
        """
        new_fr_id = (set(self.sign_in['fr_id'])
                     - set(self.sign_in_saved['fr_id']))
        sign_in_tosave = self.sign_in[self.sign_in['fr_id'].isin(new_fr_id)]

        if not sign_in_tosave.empty:
            print("[INFO] Updating db with signed in guests...", end='')
            self.guestdb.record_guest(sign_in_tosave)
            self.sign_in_saved = self.sign_in
            print('done.')

        fc.save_time = time.time()

    def guest_identify_init(self):
        """
        Identify guests previously captured.
        """
        b_identify_idx_dict = {gst_identify_off_txt: gst_identify_on_txt,
                               gst_identify_on_txt: gst_identify_off_txt}
        self.b_identify_text[0] = b_identify_idx_dict[self.b_identify_text[0]]
        self.b_identify['text'] = self.b_identify_text[0]
        if self.b_identify['text'] == gst_identify_off_txt:
            print('[INFO] Stopped identification.')
            fc.gst_identify = False
            self.update_signin()
            if self.signin_startstop['start_time']:
                self.signin_startstop['stop_time'] = datetime.datetime.now()
                self.guestdb.record_startstop(self.signin_startstop)
        elif self.b_identify['text'] == gst_identify_on_txt:
            # Check for trained models first
            if (not os.path.exists(self.fn_label_encoder)
                    or not os.path.exists(self.fn_recognizer_model)):
                tk.messagebox.showwarning(
                    "Embed & Train Needed",
                    "No guests specific models present.\n"
                    "Please run \"Embed & Train\" on precaptured guests.",
                    parent=self.root
                )
                print('[INFO] No guest specific models present.')
                self.guest_identify_init()
                return

            # Load prev captured guest metadata:
            known_guest_meta = self.guestdb.query_allguestmeta()
            if self.display_name in known_guest_meta.columns:
                fc.known_guest_meta = known_guest_meta[self.display_name]
            else:
                print('[ERROR]: No user information corresponding to {}. '
                      'Valid options are:\n{}'
                      .format(self.display_name, known_guest_meta.columns))
                fc.known_guest_meta = None

            print('[INFO] Starting identification...')
            fc.gst_identify = True
            print('[INFO] Loading guests previously captured')
            # load the actual face recognition model along with the label encoder
            fc.recognizer = pickle.loads(open(self.fn_recognizer_model, "rb").read())
            fc.label_encoder = pickle.loads(open(self.fn_label_encoder, "rb").read())

            fc.save_time = time.time()
            self.init_sign_in()
            self.guest_ids = {}
            self.signin_startstop['start_time'] = datetime.datetime.now()
            self.guestdb.record_startstop(self.signin_startstop)

    def remove_guestcapture_notindb(self):
        """
        Remove folders for users that don't have entries in the db.
        Users are effectively anonymous.
        """
        db_guest_ids = self.guestdb.query_allguestmeta().index
        id_folders = {os.path.basename(pn): pn for pn
                      in glob.glob(self.pn_guest_images + os.sep + '*') if os.path.isdir(pn)}

        ids_notguests = set(id_folders.keys()) - set(db_guest_ids)
        del_folders = [id_folders[id] for id in ids_notguests]
        if del_folders:
            print('[INFO] removing {} capture folder(s) that don\'t correspond '
                  'to guests captured in the "clients" db table.'
                  .format(len(del_folders)))
            [shutil.rmtree(pn) for pn in del_folders]

    def remove_guestcapture_notindb_archive(self):
        """
        Remove folders for users that don't have entries in the db.
        Users are effectively anonymous.
        """
        db_guest_ids = self.guestdb.query_allguestmeta().index
        id_folders = [os.path.dirname(x) for x in
                      fc.guest_archive.list_files()]
        id_folders = [x for x in id_folders if x not in ['']]

        del_folders = set(id_folders) - set(db_guest_ids)
        if del_folders:
            print('[INFO] removing {} capture folder(s) that don\'t correspond '
                  'to guests captured in the "clients" db table.'
                  .format(len(del_folders)))
            [fc.guest_archive.remove_folder(pn) for pn in del_folders]

    def embed_train_init(self):
        """
        Obtain image embeddings and train model.
        """
        print('[INFO] Checking for guests not in db...')
        self.remove_guestcapture_notindb_archive()
        print('[INFO] Running image embeddings...')
        embed_train = mt()
        embed_train.guest_archive.pw = self.pw_guestdb
        embed_train.extract_embeddings()
        print('[INFO] Training SVM model over embeddings...')
        embed_train.train_model()
        print('[INFO] Image embeddings and SVM model training complete.')
        self.b_encode['text'] = gst_embed_train_off_txt

    def init_meal_log(self):
        """
        Output meal log.
        """
        ExportMealLogDialog(self.root,
                            title='Export Meal Log',
                            fn_meal_log_default=self.fn_meal_log_default,
                            guestdb=self.guestdb)

    def destructor(self):
        """
        Destroy the root object and release all resources.
        """
        print("[INFO] closing...")
        clear_db_history()
        self.root.destroy()
        fc.destructor()


def flip_dict(data_dict):
    """
    Return a dictionary with the keys and values exchanged.
    """
    data_dict_out = copy.deepcopy(data_dict)
    for key in data_dict_out.keys():
        if 'data' in data_dict_out[key]:
            data_dict_out[key]['data'] = {v: k for k, v in data_dict_out[key]['data'].items()}
    return data_dict_out


def dict_dropdown(data_dict):
    """
    Update dictionary keys to be more guest readable for dropdown menus.
    """
    data_dict_out = copy.deepcopy(data_dict)
    for key in data_dict_out.keys():
        if 'data' in data_dict_out[key]:
            data_dict_out[key]['data'] = {k: re.sub(r" \(.*\)", "", v) for k, v in data_dict_out[key]['data'].items()}
            data_dict_out[key]['data'] = {k: re.sub(r"client", "Guest", v, flags=re.I) for k, v in data_dict_out[key]['data'].items()}
    return data_dict_out


def simplify_dropdown(datadict_item):
    """
    Pair items from the data dictionary to be appropriate values for gui drop
    down lists.
    """
    opt_list = list(datadict_item['data'].keys())
    opt_list = [re.sub(r" \(.*\)", "", x) for x in opt_list]
    opt_list = [re.sub(r"client", "Guest", x, flags=re.I) for x in opt_list]
    if 'Data not collected' in opt_list:
        opt_list.remove('Data not collected')
    opt_list = ['Select'] + opt_list  # Add a default value
    return opt_list


class NewGuestDialog(simpledialog.Dialog):
    """
    Define a pop up window that collects new guest information.
    """
    def __init__(self, *args, datadict, **kwargs):
        self.datadict = datadict
        super().__init__(*args, **kwargs)

    def body(self, master):
        # Labels
        tk.Label(master, text="First Name:").grid(row=0, column=0)
        tk.Label(master, text="Middle Name").grid(row=0, column=1)
        tk.Label(master, text="Last Name:").grid(row=0, column=2)
        tk.Label(master, text="Date of Birth (mm/dd/yyyy):").grid(row=2, column=0)
        tk.Label(master, text="Race:").grid(row=4, column=0)
        tk.Label(master, text="Ethnicity:").grid(row=4, column=1)
        tk.Label(master, text="Gender:").grid(row=4, column=2)
        tk.Label(master, text="First Time?").grid(row=7, column=0)

        # Element selection items
        opt_race = ['Select',
                    'American Indian or Alaskan Native',
                    'Asian',
                    'Black',
                    'Native HI or Other Pacific Islander',
                    'White',
                    "Guest doesn't know",
                    'Guest refused']
        opt_gender = simplify_dropdown(self.datadict['3.06.1'])
        opt_first_time = ['Select',
                          'Yes',
                          'No']
        opt_ethnicity = simplify_dropdown(self.datadict['3.05.1'])

        # Elements
        self.e1 = tk.Entry(master)
        self.e2 = tk.Entry(master)
        self.e3 = tk.Entry(master)
        self.e4 = DateEntry(master,
                            bg='darkblue',
                            date_pattern='mm/dd/y',
                            fg='white',
                            year=1970)
        self.e5 = tk.StringVar(master)
        self.e5.set(opt_race[0])
        self.e6 = tk.StringVar(master)
        self.e6.set(opt_ethnicity[0])
        self.e7 = tk.StringVar(master)
        self.e7.set(opt_gender[0])
        self.e8 = tk.StringVar(master)
        self.e8.set(opt_first_time[0])
        self.m1 = tk.OptionMenu(master,
                                self.e5,
                                *['\n'.join(textwrap.wrap(x, 18)) for x in opt_race])
        self.m2 = tk.OptionMenu(master, self.e6, *opt_ethnicity)
        self.m3 = tk.OptionMenu(master, self.e7, *opt_gender)
        self.m4 = tk.OptionMenu(master, self.e8, *opt_first_time)

        # Layout
        self.e1.grid(row=1, column=0)
        self.e2.grid(row=1, column=1)
        self.e3.grid(row=1, column=2)
        self.e4.grid(row=3, column=0)
        self.m1.grid(row=5,
                     column=0,
                     rowspan=2)
        self.m1.configure(width=20,
                          height=2)
        self.m2.grid(row=5,
                     column=1,
                     rowspan=2)
        self.m2.configure(width=20,
                          height=2)
        self.m3.grid(row=5,
                     column=2,
                     rowspan=2)
        self.m3.configure(width=20,
                          height=2)
        self.m4.grid(row=8, column=0)
        self.m4.configure(width=20)

        return self.e1  # initial focus

    def getresult(self):
        return {'first_name': self.e1.get(),
                'middle_name': self.e2.get(),
                'last_name': self.e3.get(),
                'dob': self.e4.get(),
                'race': self.e5.get(),
                'ethnicity': self.e6.get(),
                'gender': self.e7.get(),
                'first_time': self.e8.get()}

    def cleanresult(self):
        result = self.getresult()
        result['first_name'] = result['first_name'].title()
        result['middle_name'] = result['middle_name'].title()
        result['last_name'] = result['last_name'].title()
        return result

    def validate(self):
        try:
            result = self.cleanresult()
        except ValueError:
            tk.messagebox.showwarning(
                "Illegal value",
                self.errormessage + "\nPlease try again.",
                parent=self
            ),
            return 0

        if result['first_name'] == '':
            tk.messagebox.showwarning(
                "First Name Needed",
                "First Name is mandatory. Please enter a first name.",
                parent=self
            )
            return 0

        if result['race'] == 'Select':
            tk.messagebox.showwarning(
                "Invalid Race",
                "Please select race.",
                parent=self
            )
            return 0

        if result['ethnicity'] == 'Select':
            tk.messagebox.showwarning(
                "Invalid Ethnicity",
                "Please select ethnicity.",
                parent=self
            )
            return 0

        if result['gender'] == 'Select':
            tk.messagebox.showwarning(
                "Invalid Gender",
                "Please select gender.",
                parent=self
            )
            return 0

        if result['first_time'] == 'Select':
            tk.messagebox.showwarning(
                "Invalid First Time",
                "Please select a value for first time field.",
                parent=self
            )
            return 0

        self.result = result
        return 1


class ExportMealLogDialog(simpledialog.Dialog):
    """
    Define a pop up window that collects new guest information.
    """
    def __init__(self, *args, guestdb, fn_meal_log_default, **kwargs):
        self.guestdb = guestdb
        self.df_startstop = guestdb.query_startstop()
        self.df_startstop['start_time_opt'] = self.df_startstop['start_time'].apply(lambda x: x.strftime('%m/%d/%Y %I:%M %p')
                                                                                    if not isinstance(x, type(pd.NaT)) else '')
        # Add one minute to stop times to capture last minute recording
        self.df_startstop['stop_time_opt'] = (self.df_startstop['stop_time']
                                              + pd.Timedelta(minutes=1)).apply(lambda x: x.strftime('%m/%d/%Y %I:%M %p')
                                                                               if not isinstance(x, type(pd.NaT)) else '')
        self.fn_meal_log = fn_meal_log_default
        super().__init__(*args, **kwargs)

    def browse_folder(self):
        self.fn_meal_log = filedialog.asksaveasfilename(title='Save As',
                                                        initialdir=os.path.dirname(self.fn_meal_log),
                                                        filetypes=(('.csv', '*.csv'),
                                                                   ('all files', '*.*')))
        self.e5.delete(0, tk.END)
        self.e5.insert(0, self.fn_meal_log)

    def body(self, master):
        # Labels
        tk.Label(master, text="Start Date\n(mm/dd/yyyy HH:MM AM/PM):").grid(row=0, column=0)
        tk.Label(master, text="Start Date\n(Optional):").grid(row=0, column=1)
        tk.Label(master, text="Stop Date\n(mm/dd/yyyy HH:MM AM/PM):").grid(row=0, column=2)
        tk.Label(master, text="Stop Date\n(Optional):").grid(row=0, column=3)
        tk.Label(master, text="Save Path:").grid(row=2, column=0)
        tk.Label(master, text="").grid(row=2, column=1)
        tk.Label(master, text="").grid(row=2, column=2)
        tk.Label(master, text="").grid(row=2, column=3)

        # Element selection items
        opt_startdate = ['Select'] + self.df_startstop['start_time_opt'].tolist()
        opt_startdate = list(filter(lambda x: x != '', opt_startdate))[-16:]
        opt_stopdate = ['Select'] + self.df_startstop['stop_time_opt'].tolist()
        opt_stopdate = list(filter(lambda x: x != '', opt_stopdate))[-16:]

        # Elements
        self.e1 = tk.Entry(master)
        self.e2 = tk.StringVar(master)
        self.e2.set(opt_startdate[0])
        self.e3 = tk.Entry(master)
        self.e4 = tk.StringVar(master)
        self.e4.set(opt_stopdate[0])
        self.b1 = tk.Button(master,
                            text='Browse',
                            command=self.browse_folder)
        self.e5 = tk.Entry(master)
        self.e5.insert(0, self.fn_meal_log)
        self.m1 = tk.OptionMenu(master, self.e2, *opt_startdate)
        self.m2 = tk.OptionMenu(master, self.e4, *opt_stopdate)

        # Layout
        self.e1.grid(row=1, column=0)
        self.m1.grid(row=1, column=1)
        self.m1.configure(width=18)
        self.e3.grid(row=1, column=2)
        self.m2.grid(row=1, column=3)
        self.m2.configure(width=18)
        self.b1.grid(row=3, column=0)
        self.e5.grid(row=3, column=1, sticky='we', columnspan=3)

        return self.e1  # initial focus

    def getresult(self):
        return {'start_date_txt': self.e1.get(),
                'start_date_drp': self.e2.get(),
                'stop_date_txt': self.e3.get(),
                'stop_date_drp': self.e4.get(),
                'file_path': self.e5.get()}

    def cleanresult(self):
        result = self.getresult()
        if result['start_date_drp'] == 'Select':
            start_date = result['start_date_txt']
        else:
            start_date = result['start_date_drp']

        if result['stop_date_drp'] == 'Select':
            stop_date = result['stop_date_txt']
        else:
            stop_date = result['stop_date_drp']

        try:
            start_date = datetime.datetime.strptime(start_date, '%m/%d/%Y %I:%M %p')
        except Exception:
            start_date = 'malformed'

        try:
            stop_date = datetime.datetime.strptime(stop_date, '%m/%d/%Y %I:%M %p')
        except Exception:
            stop_date = 'malformed'

        return {'start_date': start_date,
                'stop_date': stop_date,
                'file_path': result['file_path']}

    def validate(self):
        try:
            result = self.cleanresult()
        except ValueError:
            tk.messagebox.showwarning(
                "Illegal value",
                self.errormessage + "\nPlease try again.",
                parent=self
            ),
            return 0

        if result['start_date'] == 'malformed':
            tk.messagebox.showwarning(
                "Start Date Needed",
                "Start date is mandatory. Please enter a start date"
                "in the form of (mm/dd/yyyy HH:MM AM/PM)",
                parent=self
            )
            return 0

        if result['stop_date'] == 'malformed':
            tk.messagebox.showwarning(
                "Stop Date Needed",
                "Stop date is mandatory. Please enter a stop date"
                "in the form of (mm/dd/yyyy HH:MM AM/PM)",
                parent=self
            )
            return 0

        if (result['start_date'] > result['stop_date']):
            tk.messagebox.showwarning(
                "Start Date Less Than Stop Date",
                "Stop date must be greater than start date.",
                parent=self
            )
            return 0

        df_meal_log = self.guestdb.query_mealsignin(result['start_date'],
                                                    result['stop_date'])

        if df_meal_log.empty:
            tk.messagebox.showwarning(
                "No Data",
                "No guests recognized between \n"
                "{} and {}\n"
                "Maybe try diffrent date range?".format(result['start_date'],
                                                        result['stop_date']),
                parent=self
            )
            return 0

        print('[INFO] Exporting meal log to {}.'.format(result['file_path']))
        df_meal_log.to_csv(result['file_path'], index=False)
        return 1


def clear_db_history():
    """
    Clear database history (secure pw and user info).
    """
    filename = str(Path.joinpath(Path.home(), '.sqlite_history'))
    try:
        os.remove(filename)
    except OSError:
        pass


if __name__ == "__main__":
    # Run script
    print("[INFO] starting...")
    app = Application()
    app.root.mainloop()
