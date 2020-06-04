# Work with encrypted 7zip archives

from subprocess import TimeoutExpired
import subprocess
import io

from PIL import Image
from PIL import UnidentifiedImageError
import numpy as np


class p7zip:
    def __init__(self, fn_archive):
        self.fn_archive = fn_archive
        self.pw = None
        self.zipfile = None

    def list_files(self):
        """
        List contents of an archive.
        Parses 7zip output.
        """
        cmd_lst = ['7z', 'l']
        if self.pw:
            cmd_lst += ['-p' + self.pw]
        cmd_lst += [self.fn_archive]
        out = subprocess.run(cmd_lst,
                             capture_output=True)
        srch_str = b'------------------- ----- ------------ ------------  ------------------------'
        start_ind = out.stdout.splitlines().index(srch_str) + 1
        end_ind = out.stdout.splitlines()[start_ind+1:].index(srch_str) + 1
        file_lines = out.stdout.splitlines()[start_ind:start_ind+end_ind]
        files = [x.split()[-1].decode('utf-8') for x in file_lines]
        return files

    def read_image(self, pn_img):
        """
        Read an image file within encrypted archive into a numpy array
        compatible with OpenCV.
        Uses 7z directly as it's faster than zipfile and more reliable.
        """
        cmd_lst = ['7z', 'x']
        if self.pw:
            cmd_lst += ['-p' + self.pw]
        cmd_lst += [self.fn_archive, '-so', pn_img]
        try:
            out = subprocess.run(cmd_lst,
                                 timeout=10,
                                 capture_output=True)
        except TimeoutExpired:
            print("[ERROR] Archive read timeout met. Is a password set?")
            return None

        try:
            image = Image.open(io.BytesIO(out.stdout))
        except UnidentifiedImageError:
            print("[ERROR] Can't read image from archive. "
                  "Is the correct archive password set?")
            return None

        return np.array(image)

    def add_image(self, path, image_array):
        """
        Stream OpenCV compatible numpy array image directly to archive.

        7z archives are preferred - streaming input for 7z 16.02 is currently
        only for xz, lzma, tar, gzip and bzip2 archives.
        tar, xz, gzip, bzip2, lzma don't directly support compression.
        """
        image = Image.fromarray(image_array)
        image_byte = io.BytesIO()
        image.save(image_byte, format='PNG')
        image_byte = image_byte.getvalue()

        cmd_lst = ['7z', 'a']
        if self.pw:
            cmd_lst += ['-p' + self.pw]
        cmd_lst += ['-si'+path, self.fn_archive]

        out = subprocess.run(cmd_lst,
                             input=image_byte,
                             capture_output=True)
        return out.stdout, out.stderr

    def add_file(self, fn_file):
        """
        Add a file to an encrypted archive.
        Requries 7z.
        """
        if not isinstance(fn_file, list):
            fn_file = [fn_file]

        cmd_lst = ['7z', 'a', self.fn_archive]
        if self.pw:
            cmd_lst += ['-p' + self.pw]
        cmd_lst += fn_file
        out = subprocess.run(cmd_lst,
                             capture_output=True)
        return out.stdout, out.stderr

    def remove_folder(self, pn_folder):
        """
        Remove a folder from an encrypted archive.
        Requres 7z.
        """
        if not isinstance(pn_folder, list):
            pn_folder = [pn_folder]

        cmd_lst = ['7z', 'd', self.fn_archive]
        if self.pw:
            cmd_lst += ['-p' + self.pw]
        cmd_lst += ['-r'] + pn_folder
        out = subprocess.run(cmd_lst,
                             capture_output=True)
        return out.stdout, out.stderr
