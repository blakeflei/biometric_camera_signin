# Work with encrypted 7zip archives

import subprocess
import io
import zipfile

from PIL import Image
import numpy as np


class p7zip:
    def __init__(self, fn_archive):
        self.fn_archive = fn_archive
        self.pw = None
        self.zipfile = None

    def list_files(self):
        self.zipfile = zipfile.ZipFile(self.fn_archive, 'r')
        return self.zipfile.namelist()

    def read_image(self, pn_img):
        """
        Read an image file within encrypted archive into a numpy array
        compatible with OpenCV.
        Uses 7z directly as it's faster than zipfile and more reliable.
        """
        print(self.fn_archive)
        cmd_lst = ['7z', 'x']
        if self.pw:
            cmd_lst += ['-p' + self.pw]
        cmd_lst += [self.fn_archive, '-so', pn_img]
        print(cmd_lst)
        out = subprocess.run(cmd_lst,
                             capture_output=True)
        image = Image.open(io.BytesIO(out.stdout))
        return np.array(image)

    def add_file(self, pn_file):
        """
        Add a file to an encrypted archive.
        Requries 7z.
        """
        if not isinstance(pn_file, list):
            pn_file = [pn_file]

        cmd_lst = ['7z', 'a']
        if self.pw:
            cmd_lst += ['-p' + self.pw]
        cmd_lst += [self.fn_archive]
        cmd_lst += pn_file
        out = subprocess.run(cmd_lst,
                             capture_output=True)
        return out.stdout, out.stderr


#    def read_file(self, pn_file):
#        self.zipfile = zipfile.ZipFile(self.fn_archive, 'r')
#        if not self.pw:
#            zip_file = self.zipfile.open(pn_file)
#        else:
#            zip_file = self.zipfile.open(pn_file, pwd=self.pw.encode('utf-8'))
#        return zip_file


#    def list_files(self):
#        cmd_lst = ['7z', 'l']
#        if self.pw:
#            cmd_lst += ['-mem=AES256', '-p' + self.pw]
#        cmd_lst += [self.fn_archive]
#
#        subp = subprocess.Popen(cmd_lst,
#                                 stdin=PIPE,
#                                 stdout=PIPE,
#                                 stderr=PIPE)
#        stdout, stderr = subp.communicate()
#        srch_str = b'------------------- ----- ------------ ------------  ------------------------'
#        start_ind = stdout.splitlines().index(srch_str) + 1
#        end_ind = stdout.splitlines()[start_ind+1:].index(srch_str) + 1
#        file_lines = stdout.splitlines()[start_ind:start_ind+end_ind]
#        files = [x.split()[-1] for x in file_lines]
#        return files


#    def add_file(self,pn_archive):
#        pass
#
