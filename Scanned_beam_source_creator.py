#!/usr/bin/env python
# coding: utf-8

import csv
import glob
import os
import re
import shutil
import subprocess
import time
import gmsh
import pandas as pd
import ctypes
from tkinter import filedialog
import customtkinter as ctk
import MevEGS_gui_utils as utils
import MevEGS_gui_utils_cluster as cluster
from Post_Processing import ptracks as pt
import posixpath
from CTkMenuBar import *  # import CTkMenuBar
from CTkXYFrame import *
# import matplotlib.pyplot as plt
# import tkinter as tk
import numpy as np

# --------------------------------------------------------------------------------------------


def btn_cst_file_explore_clicked(self):
    initial_file = self.directory_file_cst_source
    directory_file_cst_source = filedialog.askopenfilename(initialfile=initial_file,
                                                       filetypes=[('CST source files', '*.txt')])
    self.directory_file_cst_source = directory_file_cst_source
    self.btn_cst_file_explore.configure(text='.'.join(os.path.basename(self.directory_file_cst_source).split('.')[:-1]))
    utils.write_to_console_log(self, 'MevEGS:\t\tFile loaded - ' + self.directory_file_cst_source)
    self.btn_cst_file_explore_tip.configure(message=self.directory_file_cst_source)

    self.headerframe = pd.read_csv(self.directory_file_cst_source, sep='=', nrows=8, names=['quantity', 'value'])
    self.dataframe = pd.read_csv(self.directory_file_cst_source, sep=',', skiprows=11, names=['x(cm)', 'y(cm)', 'u(xcosine)', 'v(ycosine)', 'w(zcosine)', 'ke(mev)', 'weight', 'iq'])
    filled_table = []
    separate_list = str(self.headerframe['quantity']).split()
    filled_table.append(['', 'File Header', ''])
    for i in range(1, 25, 3):
        filled_table.append([separate_list[i], self.headerframe['value'][(i - 1) / 3], separate_list[i + 1]])
    self.table_cst_source.update_values(filled_table)
    self.frame_inputs.update_idletasks()

def btn_cst_data_preview_clicked(self):
    if self.directory_file_cst_source == 'Choose CST Source File':
        ...
        # print message to console
    else:
        ...
        # max_ke = np.max(SOMETHING)
