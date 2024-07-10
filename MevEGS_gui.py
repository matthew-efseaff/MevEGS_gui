#!/usr/bin/env python
# coding: utf-8
###############################################################################
#
#  Contributors:     David Macrillo,
#                    Matt Ronan,
#                    Nigel Vezeau,
#                    Lou Thompson,
#                    Max Orok,
#                    Jennifer Matthew,
#                    Matthew Efseaff
#

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
# import numpy as np

# --------------------------------------------------------------------------------------------

# SEE README.TXT FOR NOTES AND INSTRUCTIONS

# main class
class MevegsGui:
    directory_ini = 'Error - not initialized'
    directory_mevegs = 'Choose MevEGS Home Directory'
    directory_post_pro = 'Choose Post Processing Script Directory'
    directory_file_egsinp = 'Choose .egsinp File'
    directory_file_msh = 'Choose .msh File'
    directory_file_pegs = 'Choose .pegs File'
    directory_project = 'Choose Project Directory'
    njobs = '1'
    directory_file_project_msh = 'Choose .results.msh File'
    gmsh_views = ''
    gmsh_groups = ''
    directory_source = ''
    file_source = ''
    bar_progress = 0
    quit_progress_bar = False
    menu_data = ''
    menu_source = ''
    view_dict = {}
    appearance = ''
    color_theme = ''
    scaling = ''
    username = ''

    # IF RUN BY COMMAND LINE like >python 'mevegs_gui_program_name.py'
    # Below saves an initialization file to the location of this MevEGS app .py file
    # directory_ini    = os.path.dirname(os.path.realpath(__file__))
    # IF RUN BY INTERPRETER (PyCharm, Jupyter, etc.)
    # directory_ini    = os.getcwd()       #  This might work for both situations, but using __file__ seems Pythonic

    try:
        directory_ini = os.path.dirname(os.path.realpath(__file__))
    except:
        directory_ini = os.getcwd()

    directory_ini = directory_ini.replace(os.sep, posixpath.sep) + '/'

    # Initialize main gui window

    def __init__(self, gui):
        super().__init__()
        # ctk.deactivate_automatic_dpi_awareness()
        ctk.set_window_scaling(1.75)  # temporary until we figure out the scaling/screen view best fit
        # ctk.set_widget_scaling(1.1)
        self.gui = gui
        self.gui.title("MevEGS")
        looks_saved_info_dict = {}
        if os.path.isfile(self.directory_ini + '/mevegs_app.ini'):
            pd_dataframe = pd.read_csv(self.directory_ini + '/mevegs_app.ini', header=None)
            looks_saved_info_dict = dict(zip(pd_dataframe[0], pd_dataframe[1]))
        if 'appearance' in looks_saved_info_dict:
            self.appearance = looks_saved_info_dict[
                'appearance']  # needs to be called in part at the start to get this particular part of the config
            ctk.set_appearance_mode(self.appearance)
        if 'color_theme' in looks_saved_info_dict:
            self.color_theme = looks_saved_info_dict['color_theme']
            ctk.set_default_color_theme(self.color_theme)
            dark_only_themes = ['Greengage', 'Hades', 'Harlequin', 'NightTrain', 'TrojanBlue']
            for _theme in dark_only_themes:
                if self.color_theme == _theme:
                    ctk.set_appearance_mode('Dark')

        self.gui.geometry("-7+0")

        self.menu_bar = CTkMenuBar(self.gui)
        self.menu_bar_file = self.menu_bar.add_cascade(text="File")
        self.menu_bar_settings = self.menu_bar.add_cascade(text='Settings')
        self.menu_bar_relaunch = self.menu_bar.add_cascade(text='Relaunch app')

        self.drop_menu_file = CustomDropdownMenu(widget=self.menu_bar_file)
        self.drop_menu_file.add_option(option='Quick Save', command=lambda: self.quick_save())
        self.drop_menu_file.add_option(option='Save As', command=lambda: self.btn_save_state_clicked())
        self.drop_menu_file.add_option(option='Load', command=lambda: self.btn_load_state_clicked())
        self.drop_menu_file.add_option(option='New Project', command=lambda: [utils.save_project(self)])
        self.drop_menu_file.add_separator()
        self.drop_menu_file.add_option(option='Exit', command=lambda: self.btn_exit_program())
        self.drop_menu_file.add_separator()
        self.drop_menu_file.add_separator()
        self.drop_menu_file.add_option(option='Force Exit on Error', command=lambda: self.btn_emergency_destroy())

        self.drop_menu_settings = CustomDropdownMenu(widget=self.menu_bar_settings)
        self.drop_menu_settings.add_option(option='Full Screen (toggle)',
                                           command=lambda: utils.menu_full_screen_clicked(self))
        self.sub_drop_scaling = self.drop_menu_settings.add_submenu("GUI Scaling")
        self.sub_drop_scaling.add_option(option="75% ", command=lambda: [ctk.set_widget_scaling(0.75),
                                                                         utils.write_to_console_log(self, 
                                                                             "Widget scaling:\t\t0.75")])  # ctk.set_window_scaling(0.75),
        self.sub_drop_scaling.add_option(option="90% ", command=lambda: [ctk.set_widget_scaling(0.90),
                                                                         utils.write_to_console_log(self, 
                                                                             "Widget scaling:\t\t0.90")])  # ctk.set_window_scaling(0.90),
        self.sub_drop_scaling.add_option(option="100%", command=lambda: [ctk.set_widget_scaling(1.00),
                                                                         utils.write_to_console_log(self, 
                                                                             "Widget scaling:\t\t1.00")])  # [ctk.set_window_scaling(1.00),
        self.sub_drop_scaling.add_option(option="110%", command=lambda: [ctk.set_widget_scaling(1.10),
                                                                         utils.write_to_console_log(self, 
                                                                             "Widget scaling:\t\t1.10")])  # [ctk.set_window_scaling(1.10),
        self.sub_drop_scaling.add_option(option="125%", command=lambda: [self.scale_window(1.25),
                                                                         utils.write_to_console_log(self, 
                                                                             "Widget scaling:\t\t1.25")])  # [ctk.set_window_scaling(1.25),
        self.sub_drop_scaling.add_option(option="150%", command=lambda: [self.scale_window(1.50),
                                                                         utils.write_to_console_log(self, 
                                                                             "Widget scaling:\t\t1.50")])  # [ctk.set_window_scaling(1.50),
        self.sub_drop_appearance = self.drop_menu_settings.add_submenu("Appearance")
        self.sub_drop_appearance.add_option(option="Dark", command=lambda: [ctk.set_appearance_mode("dark"),
                                                                            utils.write_to_console_log(self, 
                                                                                "Appearance mode:\t\t" + ctk.get_appearance_mode())])
        self.sub_drop_appearance.add_option(option="Light", command=lambda: [ctk.set_appearance_mode("light"),
                                                                             utils.write_to_console_log(self, 
                                                                                 "Appearance mode:\t\t" + ctk.get_appearance_mode())])
        self.sub_drop_appearance.add_option(option="System", command=lambda: [ctk.set_appearance_mode("system"),
                                                                              utils.write_to_console_log(self, 
                                                                                  "Appearance mode:\t\t" + ctk.get_appearance_mode())])

        self.sub_drop_theme = self.drop_menu_settings.add_submenu(
            "Theme")  # Will have to write choice to .ini file and relaunch app
        self.sub_drop_theme.add_option(option="Blue", command=lambda: [ctk.set_default_color_theme("blue"),
                                                                       utils.color_theme_notice(self)])
        self.sub_drop_theme.add_option(option="Dark Blue", command=lambda: [ctk.set_default_color_theme("dark-blue"),
                                                                            utils.color_theme_notice(self)])
        self.sub_drop_theme.add_option(option="Green", command=lambda: [ctk.set_default_color_theme("green"),
                                                                        utils.color_theme_notice(self)])
        self.sub_drop_theme.add_option(option="Greengage", command=lambda: [ctk.set_default_color_theme("Greengage"),
                                                                            utils.color_theme_notice(self)])
        self.sub_drop_theme.add_option(option="Hades", command=lambda: [ctk.set_default_color_theme("Hades"),
                                                                        utils.color_theme_notice(self)])
        self.sub_drop_theme.add_option(option="Harlequin", command=lambda: [ctk.set_default_color_theme("Harlequin"),
                                                                            utils.color_theme_notice(self)])
        self.sub_drop_theme.add_option(option="NightTrain", command=lambda: [ctk.set_default_color_theme("NightTrain"),
                                                                             utils.color_theme_notice(self)])
        self.sub_drop_theme.add_option(option="TrojanBlue", command=lambda: [ctk.set_default_color_theme("TrojanBlue"),
                                                                             utils.color_theme_notice(self)])
        self.menu_bar_relaunch.configure(command=lambda: utils.restart_app_now(self))

        self.tabview = ctk.CTkTabview(master=gui, anchor='nw', command=self.btn_update_tabs)
        self.tabview.pack()
        self.tab_inputs = self.tabview.add('Source Files')
        self.tab_inputs.grid_columnconfigure(0, weight=1)
        self.tab_1 = self.tabview.add('Simulate')
        self.tab_1.grid_columnconfigure(0, weight=1)
        self.tab_1.grid_rowconfigure(0, weight=1)
        self.tab_2 = self.tabview.add('Cluster')
        self.tab_2.grid_columnconfigure(0, weight=1)
        self.tab_2.grid_rowconfigure(0, weight=1)
        self.tab_3 = self.tabview.add('Post Process')
        self.tab_3.grid_columnconfigure(0, weight=1)
        self.tab_3.grid_rowconfigure(0, weight=1)
        self.tabview.set('Source Files')

        # SCREEN SIZE CALCULATIONS

        scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
        screen_width = self.gui.winfo_screenwidth()
        screen_height = self.gui.winfo_screenheight()
        size_tuple = [screen_height, screen_width]

        # SOURCE FILES TAB INPUT
        window_height = 0.815
        window_width = 0.975
        self.frame_inputs = CTkXYFrame(self.tab_inputs, width=window_width * scale_factor * size_tuple[1],
                                       height=window_height * scale_factor * size_tuple[0], scrollbar_width=20)
        self.frame_inputs.grid(row=0, column=0, pady=4, padx=4, sticky='nesw')
        self.frame_1 = CTkXYFrame(self.tab_1, width=window_width * scale_factor * size_tuple[1],
                                  height=window_height * scale_factor * size_tuple[0],
                                  scrollbar_width=20)  # , fg_color=['white', 'black'], )  # , scrollbar_button_color='red', scrollbar_button_hover_color='blue')
        self.frame_1.grid(row=0, column=0, pady=4, padx=4, sticky='nesw')
        self.frame_2 = CTkXYFrame(self.tab_2, width=window_width * scale_factor * size_tuple[1],
                                  height=window_height * scale_factor * size_tuple[0], scrollbar_width=20)
        self.frame_2.grid(row=0, column=0, pady=4, padx=4, sticky='nesw')
        self.frame_3 = CTkXYFrame(self.tab_3, width=window_width * scale_factor * size_tuple[1],
                                  height=window_height * scale_factor * size_tuple[0], scrollbar_width=20)
        self.frame_3.grid(row=0, column=0, pady=4, padx=4, sticky='nesw')

        self.gui.protocol("WM_DELETE_WINDOW", self.btn_on_x_exit)

        self.menu_source, menu_sources_path, menu_sources = self.source_list_populate()
        # Choose project directory
        self.lbl_header_input = ctk.CTkLabel(self.frame_inputs, text="Source Item",
                                             font=('Helvetica', 16, 'bold'), fg_color=("grey90", "gray10"),
                                             text_color=['black', 'white'], corner_radius=6)
        self.lbl_header_input.grid(column=0, row=0, padx=5, pady=2, sticky='we')
        self.lbl_header_input1 = ctk.CTkLabel(self.frame_inputs, text="Action",
                                              font=('Helvetica', 16, 'bold'), fg_color=("grey90", "gray10"),
                                              text_color=['black', 'white'], corner_radius=6)
        self.lbl_header_input1.grid(column=1, row=0, padx=5, pady=2, sticky='we', columnspan=2)
        # column 3 file opener buttons header
        self.lbl_header_input_open = ctk.CTkLabel(self.frame_inputs, text="File\nLocation",
                                             font=('Helvetica', 16, 'bold'), fg_color=("grey90", "gray10"),
                                             text_color=['black', 'white'], corner_radius=6)
        self.lbl_header_input_open.grid(column=3, row=0, padx=5, pady=2, sticky='we')
        self.lbl_header_input2 = ctk.CTkLabel(self.frame_inputs, text="Notes",
                                              font=('Helvetica', 16, 'bold'), fg_color=("grey90", "gray10"),
                                              text_color=['black', 'white'], corner_radius=6)
        self.lbl_header_input2.grid(column=4, row=0, padx=5, pady=2, sticky='we')
        self.lbl_project = ctk.CTkLabel(self.frame_inputs, text="Project folder")
        self.lbl_project.grid(column=0, row=1, padx=5, pady=2, sticky='e')
        self.btn_project_explore = ctk.CTkButton(self.frame_inputs, text=self.directory_project,
                                                 command=self.btn_project_explore_clicked)
        self.btn_project_explore.grid(column=1, row=1, padx=(5, 0), pady=2, sticky='we')
        self.btn_project_explore_new = ctk.CTkButton(self.frame_inputs, text='Create New Project',
                                                     command=lambda: utils.save_project(self))
        self.btn_project_explore_new.grid(column=2, row=1, padx=(1, 5), pady=2, sticky='we')
        self.lbl_project_1 = ctk.CTkLabel(self.frame_inputs, text="Directory path")
        self.lbl_project_1.grid(column=4, row=1, padx=5, pady=2, sticky='w')
        # Choose .egsinp file
        self.lbl_egsinp = ctk.CTkLabel(self.frame_inputs, text='.egsinp file')
        self.lbl_egsinp.grid(column=0, row=2, padx=5, pady=2, sticky='e')
        self.btn_egsinp_explore = ctk.CTkButton(self.frame_inputs, text=self.directory_file_egsinp,
                                                command=self.btn_egsinp_explore_clicked)
        self.btn_egsinp_explore.grid(column=1, row=2, padx=(5, 0), pady=2, sticky='we')
        self.btn_egsinp_build = ctk.CTkButton(self.frame_inputs, text='Build New Input',
                                              command='')
        self.btn_egsinp_build.grid(column=2, row=2, padx=(1, 5), pady=2, sticky='we')
        self.lbl_egsinp_1 = ctk.CTkLabel(self.frame_inputs, text='File path (filenames must not have spaces)')
        self.lbl_egsinp_1.grid(column=4, row=2, padx=5, pady=2, sticky='w')
        # Choose .msh file
        self.lbl_mesh = ctk.CTkLabel(self.frame_inputs, text='.msh file')
        self.lbl_mesh.grid(column=0, row=3, padx=5, pady=2, sticky='e')
        self.btn_mesh_explore = ctk.CTkButton(self.frame_inputs, text=self.directory_file_msh,
                                              command=self.btn_mesh_explore_clicked)
        self.btn_mesh_explore.grid(column=1, row=3, padx=5, pady=2, sticky='we', columnspan=2)
        self.lbl_mesh_1 = ctk.CTkLabel(self.frame_inputs, text='File path (filenames must not have spaces)')
        self.lbl_mesh_1.grid(column=4, row=3, padx=5, pady=2, sticky='w')
        # Source - radiation
        self.lbl_sources_1 = ctk.CTkLabel(self.frame_inputs, text="Phase-space sources")
        self.lbl_sources_1.grid(column=0, row=4, padx=5, pady=2, sticky='e')
        self.menu_source_1 = ctk.CTkOptionMenu(self.frame_inputs, variable=self.menu_source, values=menu_sources,
                                               anchor='center')
        self.menu_source_1.grid(column=1, row=4, padx=5, pady=2, sticky='ew', columnspan=2)
        self.lbl_sources_11 = ctk.CTkLabel(self.frame_inputs, text="Optional")
        self.lbl_sources_11.grid(column=4, row=4, padx=5, pady=2, sticky='w')
        # Choose results.msh file
        self.lbl_results_mesh_1 = ctk.CTkLabel(self.frame_inputs, text='.results.msh file')
        self.lbl_results_mesh_1.grid(column=0, row=5, padx=5, pady=2, sticky='e')
        self.btn_results_mesh_explore = ctk.CTkButton(self.frame_inputs, text=self.directory_file_project_msh,
                                                      command=lambda: [cluster.modify_msh_results_msh_extension(self),
                                                                       utils.btn_results_mesh_explore_clicked(self)])
        self.btn_results_mesh_explore.grid(column=1, row=5, padx=5, pady=2, sticky='we', columnspan=2)
        self.lbl_results_mesh_11 = ctk.CTkLabel(self.frame_inputs, text='File path')
        self.lbl_results_mesh_11.grid(column=4, row=5, padx=5, pady=2, sticky='w')
        # Choose MevEGS.cpp directory
        self.lbl_mevegs = ctk.CTkLabel(self.frame_inputs, text="Mevegs.cpp folder")
        self.lbl_mevegs.grid(column=0, row=6, padx=5, pady=2, sticky='e')
        self.btn_mevegs_explore = ctk.CTkButton(self.frame_inputs, text=self.directory_mevegs,
                                                command=self.btn_mevegs_explore_clicked)
        self.btn_mevegs_explore.grid(column=1, row=6, padx=5, pady=2, sticky='we', columnspan=2)
        self.lbl_mevegs_1 = ctk.CTkLabel(self.frame_inputs, text="Directory path")
        self.lbl_mevegs_1.grid(column=4, row=6, padx=5, pady=2, sticky='w')
        # Choose PEGS file
        self.lbl_pegs = ctk.CTkLabel(self.frame_inputs, text='.pegs4dat file')
        self.lbl_pegs.grid(column=0, row=7, padx=5, pady=2, sticky='e')
        self.btn_pegs_explore = ctk.CTkButton(self.frame_inputs, text=self.directory_file_pegs,
                                              command=self.btn_pegs_explore_clicked)
        self.btn_pegs_explore.grid(column=1, row=7, padx=5, pady=2, sticky='we', columnspan=2)
        self.lbl_pegs_1 = ctk.CTkLabel(self.frame_inputs, text='File path')
        self.lbl_pegs_1.grid(column=4, row=7, padx=5, pady=2, sticky='w')
        # Choose Post-pro scripts
        self.lbl_postpro = ctk.CTkLabel(self.frame_inputs, text="Post-processing folder")
        self.lbl_postpro.grid(column=0, row=8, padx=5, pady=2, sticky='e')
        self.btn_postpro_explore = ctk.CTkButton(self.frame_inputs, text=self.directory_post_pro,
                                                 command=self.btn_postpro_explore_clicked)
        self.btn_postpro_explore.grid(column=1, row=8, padx=5, pady=2, sticky='we', columnspan=2)
        self.lbl_postpro_1 = ctk.CTkLabel(self.frame_inputs, text="Directory path")
        self.lbl_postpro_1.grid(column=4, row=8, padx=5, pady=2, sticky='w')
        # MevEGS app HOME
        self.lbl_ini = ctk.CTkLabel(self.frame_inputs, text="MevEGS*.py folder")
        self.lbl_ini.grid(column=0, row=9, padx=5, pady=2, sticky='e')
        self.btn_cluster_explore = ctk.CTkButton(self.frame_inputs, text=self.directory_ini,
                                                 command=self.btn_cluster_explore_clicked)
        self.btn_cluster_explore.grid(column=1, row=9, padx=5, pady=2, sticky='we', columnspan=2)
        self.lbl_ini_1 = ctk.CTkLabel(self.frame_inputs, text="Directory path")
        self.lbl_ini_1.grid(column=4, row=9, padx=5, pady=2, sticky='w')
        # Open file column
        self.btn_egsinp_file_open = ctk.CTkButton(self.frame_inputs, text='.egsinp', width=50,
                                                command=self.btn_egsinp_file_open_clicked)
        self.btn_egsinp_file_open.grid(column=3, row=2, padx=1, pady=2, sticky='we')
        self.btn_msh_file_open = ctk.CTkButton(self.frame_inputs, text='.msh', width=50,
                                                  command=self.btn_msh_file_open_clicked)
        self.btn_msh_file_open.grid(column=3, row=3, padx=1, pady=2, sticky='we')
        self.btn_project_msh_file_open = ctk.CTkButton(self.frame_inputs, text='.results.msh', width=50,
                                               command=self.btn_project_msh_file_open_clicked)
        self.btn_project_msh_file_open.grid(column=3, row=5, padx=1, pady=2, sticky='we')

        # Console Input
        self.lbl_header_input = ctk.CTkLabel(self.frame_inputs, text="Console Log", font=('Helvetica', 16, 'bold'),
                                             fg_color=("grey90", "gray10"), text_color=['black', 'white'],
                                             corner_radius=6)
        self.lbl_header_input.grid(column=0, row=10, padx=5, pady=1, sticky='we', columnspan=5)
        self.console_text_box_input = ctk.CTkTextbox(master=self.frame_inputs, wrap='word', width=600, height=250,
                                                     fg_color=['grey90',
                                                               'grey10'])  # , text_color=['black', 'white'], state='disabled')
        self.console_text_box_input.grid(column=0, row=11, padx=5, pady=2, sticky='nesw', columnspan=5, rowspan=18)

        # SIMULATE TAB 1, FRAME 1

        self.lbl_header_1 = ctk.CTkLabel(self.frame_1, text="Simulation Control", font=('Helvetica', 16, 'bold'),
                                         fg_color=("grey90", "gray10"), text_color=['black', 'white'], corner_radius=6)
        self.lbl_header_1.grid(column=0, row=0, padx=5, pady=2, sticky='we')
        # Visualize Sim (ptracks) and process
        self.btn_ptracks = ctk.CTkButton(self.frame_1, text="Visualize simulation geometry (ptracks)",
                                         command=self.btn_ptracks_clicked)
        self.btn_ptracks.grid(column=0, row=1, padx=5, pady=2, sticky='we')
        # Run local mevegs with nJobs
        self.lbl_njobs = ctk.CTkLabel(self.frame_1,
                                      text='Number of Jobs: Max = number of CPUs\nMin = 1')
        self.lbl_njobs.grid(column=0, row=2, padx=5, pady=2)
        self.job_number = ctk.StringVar()
        self.entry_njobs = ctk.CTkEntry(self.frame_1, textvariable=self.job_number, width=60)
        self.job_number.set(self.njobs)
        self.entry_njobs.configure("center", justify='center')
        self.entry_njobs.grid(column=0, row=3, padx=5, pady=2)
        self.entry_njobs.bind("<Return>", command=lambda event: self.btn_run_mevegs_clicked(event))  # This not working
        self.btn_run_mevegs = ctk.CTkButton(self.frame_1, text="Run local MevEGS", height=75,
                                            command=lambda: self.btn_run_mevegs_clicked(self.entry_njobs.get()))
        self.btn_run_mevegs.grid(column=0, row=4, padx=5, pady=2, rowspan=2, sticky='n')
        self.btn_show_mevegs_progressbar = ctk.CTkButton(self.frame_1, text="Track local progress",
                                                         command=lambda: self.btn_check_local_progress_clicked())
        self.btn_show_mevegs_progressbar.grid(column=0, row=6, padx=5, pady=2, sticky='we')
        self.mevegs_progress_bar = ctk.CTkProgressBar(self.frame_1)
        self.mevegs_progress_bar.grid(column=0, row=7, padx=5, pady=2, sticky='we')
        self.mevegs_progress_bar.set(self.bar_progress)
        self.percent_label = ctk.CTkLabel(self.frame_1, text='0%')
        self.percent_label.grid(column=0, row=8, padx=5, pady=2)
        self.btn_show_mevegs_jobs = ctk.CTkButton(self.frame_1, text="Show number of jobs running",
                                                  command=lambda: utils.btn_show_mevegs_jobs_clicked(self))
        self.btn_show_mevegs_jobs.grid(column=0, row=9, padx=5, pady=2, sticky='we')

        # Clean up files from MevEGS.cpp folder
        self.lbl_header_11 = ctk.CTkLabel(self.frame_1, text="Simulation Cleanup", font=('Helvetica', 16, 'bold'),
                                          fg_color=("grey90", "gray10"), text_color=['black', 'white'], corner_radius=6)
        self.lbl_header_11.grid(column=1, row=0, padx=5, pady=2, sticky='we')
        self.btn_clean_up = ctk.CTkButton(self.frame_1, text='Move results files in\nMevEGS Home to\nProject directory',
                                          command=lambda: [self.btn_clean_up_clicked(),
                                                           utils.return_running_jobs_to_null(self)])
        self.btn_clean_up.grid(column=1, row=1, padx=5, pady=2, rowspan=2, sticky='n')
        self.btn_kill_mevegs = ctk.CTkButton(self.frame_1, text="Kill all MevEGS processes",
                                             command=lambda: utils.are_you_sure_kill(self))
        self.btn_kill_mevegs.grid(column=1, row=4, padx=5, pady=2, sticky='n')
        self.btn_restore_mevegs = ctk.CTkButton(self.frame_1, text='Restore MevEGS Home to default',
                                                command=lambda: [utils.are_you_sure_cleanup(self),
                                                                 utils.return_running_jobs_to_null(self)])
        self.btn_restore_mevegs.grid(column=1, row=7, padx=5, pady=2, sticky='n')
        # Console Frame_1
        self.lbl_header_111 = ctk.CTkLabel(self.frame_1, text="Console Log", font=('Helvetica', 16, 'bold'),
                                           fg_color=("grey90", "gray10"), text_color=['black', 'white'],
                                           corner_radius=6)
        self.lbl_header_111.grid(column=2, row=0, padx=5, pady=2, sticky='we', columnspan=2)
        self.console_text_box_1 = ctk.CTkTextbox(master=self.frame_1, wrap='word', width=600, height=350,
                                                 fg_color=['grey90',
                                                           'grey10'])  # , text_color=['black', 'white'], state='disabled')
        self.console_text_box_1.grid(column=2, row=1, padx=5, pady=2, sticky='nesw', columnspan=2, rowspan=18)

        # Cluster Tab frame initialization
        # FRAME 2 COLUMN 0 Submit jobs

        self.lbl_header_2 = ctk.CTkLabel(self.frame_2, text="Simulation Control", font=('Helvetica', 16, 'bold'),
                                         fg_color=("grey90", "gray10"), text_color=['black', 'white'], corner_radius=6)
        self.lbl_header_2.grid(column=0, row=0, padx=5, pady=2, sticky='we')
        self.lbl_njobs_2 = ctk.CTkLabel(self.frame_2,
                                        text='.egsinp value \'ncase\' should\nbe a multiple of 64',
                                        corner_radius=6)  # , text_color='black', fg_color='DarkGray'
        self.lbl_njobs_2.grid(column=0, row=1, padx=5, pady=2, sticky='we')
        self.btn_submit_2 = ctk.CTkButton(self.frame_2, text='Submit job', height=75, width=150,
                                          command=lambda: cluster.btn_submit_cluster_jobs_clicked(self))
        self.btn_submit_2.grid(column=0, row=2, padx=5, pady=2, sticky='n', rowspan=2)
        self.btn_check_cluster_2 = ctk.CTkButton(self.frame_2, text='Cluster Status',
                                                 command=lambda: cluster.btn_check_cluster_status_clicked(self))
        self.btn_check_cluster_2.grid(column=0, row=4, padx=5, pady=5, sticky='we')
        self.lbl_username_2 = ctk.CTkLabel(self.frame_2,
                                                     text="Cluster Username")
        self.lbl_username_2.grid(column=0, row=5, padx=5, pady=2, sticky='we')
        self.username, usernames = self.username_list_choice()
        self.optionmenu_user_2 = ctk.CTkOptionMenu(self.frame_2, variable=self.username,
                                                   values=usernames,
                                                   anchor='center')
        self.optionmenu_user_2.grid(column=0, row=6, padx=5, pady=2, sticky='we')
        self.btn_display_job_progress_2 = ctk.CTkButton(self.frame_2, text='Display job log', anchor='center',
                                                        command=lambda: [
                                                            cluster.btn_display_cluster_log_file_clicked_2(self,
                                                                                                           self.optionmenu_user_2.get())])
        self.btn_display_job_progress_2.grid(column=0, row=7, padx=5, pady=2, sticky='we')
        self.btn_display_cluster_status_2 = ctk.CTkButton(self.frame_2, text='Display cluster queue', anchor='center',
                                                          command=lambda: [
                                                              cluster.btn_display_cluster_status_clicked_2(self,
                                                                                                           self.optionmenu_user_2.get())])
        self.btn_display_cluster_status_2.grid(column=0, row=8, padx=5, pady=2, sticky='we')

        # COLUMN 1
        # Cluster interaction

        self.lbl_header_21 = ctk.CTkLabel(self.frame_2, text="Simulation Cleanup", font=('Helvetica', 16, 'bold'),
                                          fg_color=("grey90", "gray10"), text_color=['black', 'white'], corner_radius=6)
        self.lbl_header_21.grid(column=1, row=0, padx=5, pady=2, sticky='we')
        self.btn_show_job_list_2 = ctk.CTkButton(self.frame_2, text='Jobs still on cluster', anchor='center',
                                                 command=lambda: cluster.btn_show_job_list_clicked_2(self))
        self.btn_show_job_list_2.grid(column=1, row=1, padx=5, pady=2, sticky='we')
        self.optionmenu_job_2 = ctk.CTkComboBox(self.frame_2, values=['Job number'], justify='center')
        self.optionmenu_job_2.grid(column=1, row=2, padx=5, pady=2, sticky='we')
        self.optionmenu_job_2['state'] = 'normal'
        self.btn_kill_2 = ctk.CTkButton(self.frame_2, text='Kill current job and cleanup',
                                        command=lambda: [
                                            cluster.btn_kill_cluster_jobs_clicked(self, self.optionmenu_user_2.get(),
                                                                                  self.optionmenu_job_2.get())])  # , fg_color="OrangeRed4", hover_color="OrangeRed2"
        self.btn_kill_2.grid(column=1, row=3, padx=5, pady=2)
        self.btn_retrieve_2 = ctk.CTkButton(self.frame_2, text='Retrieve all submissions', width=150, height=75,
                                            command=lambda: cluster.btn_retrieve_cluster_jobs_clicked(self))
        self.btn_retrieve_2.grid(column=1, row=4, padx=5, pady=(10, 5), rowspan=2)
        if os.path.isfile(self.directory_ini + 'mevegs_app.ini'):
            with open(self.directory_ini + 'mevegs_app.ini', "r") as _file:
                pd_dataframe = pd.read_csv(_file, header=None)
                saved_info_dict = dict(zip(pd_dataframe[0], pd_dataframe[1]))
                self.directory_project = saved_info_dict['project']
        self.btn_results_retrieve_2 = ctk.CTkButton(self.frame_2,
                                                    text='Open directory\n' +
                                                         os.path.basename(os.path.dirname(self.directory_project)),
                                                    command=lambda: self.btn_project_open_clicked())
        self.btn_results_retrieve_2.grid(column=1, row=6, padx=5, pady=2)
        self.phasespace_warning_2 = ctk.CTkLabel(self.frame_2,
                                                 text='\'Retrieve all\' downloads all available\n'
                                                      'simulations to sub-folders of your\n'
                                                      'project with four digit folder names:\n   /'
                                                      + os.path.basename(os.path.dirname(self.directory_project)) + '/####/\n'
                                                      'You must change the \"Project folder\"\n'
                                                      '(directory path) in the \n'
                                                      '\'Source Files\' tab to the\n'
                                                      'correct directory before processing\n'
                                                      'phase-space files and using the\n'
                                                      '\'Post Process\' tab', justify='left',
                                                 corner_radius=6)  # text_color='black', fg_color='DarkGray',
        self.phasespace_warning_2.grid(column=1, row=7, padx=5, pady=5, sticky='we', rowspan=4)
        self.btn_process_phasespace_2 = ctk.CTkButton(self.frame_2, text='Process phase-space files',
                                                      command=lambda: cluster.process_cluster_phase_space(self))
        self.btn_process_phasespace_2.grid(column=1, row=11, padx=5, pady=2, sticky='n')

        # TAB 2 CONSOLE LOG

        self.lbl_header_222 = ctk.CTkLabel(self.frame_2, text="Console Log", font=('Helvetica', 16, 'bold'),
                                           fg_color=("grey90", "gray10"), text_color=['black', 'white'],
                                           corner_radius=6)
        self.lbl_header_222.grid(column=2, row=0, padx=5, pady=2, sticky='we', columnspan=2)
        self.console_text_box_2 = ctk.CTkTextbox(master=self.frame_2, wrap='word', width=600, height=350,
                                                 fg_color=['grey90',
                                                           'grey10'])  # , text_color=['black', 'white'], state='disabled')
        self.console_text_box_2.grid(column=2, row=1, padx=5, pady=2, sticky='nesw', columnspan=2, rowspan=18)
        self.frame_2.update_idletasks()

        # Post Processing Tab frame initialization
        # FRAME 3.0 Headers

        self.lbl_results_header_3 = ctk.CTkLabel(self.frame_3, text=self.directory_file_project_msh,
                                         font=('Helvetica', 14, 'bold'), justify='left', fg_color=("grey90", "gray10"),
                                         text_color=['black', 'white'], corner_radius=6)
        self.lbl_results_header_3.grid(column=0, row=0, padx=5, pady=2, columnspan=4, sticky='ew')
        self.lbl_header_3 = ctk.CTkLabel(self.frame_3, text="Data",
                                         font=('Helvetica', 16, 'bold'), fg_color=("grey90", "gray10"),
                                         text_color=['black', 'white'], corner_radius=6)
        self.lbl_header_3.grid(column=0, row=1, padx=5, pady=2, sticky='we')
        self.lbl_create_figs_3 = ctk.CTkLabel(self.frame_3, text="Create Figures", font=('Helvetica', 16, 'bold'),
                                              fg_color=("grey90", "gray10"), text_color=['black', 'white'],
                                              corner_radius=6)
        self.lbl_create_figs_3.grid(column=1, row=1, padx=5, pady=2, sticky='we')
        self.lbl_header_333 = ctk.CTkLabel(self.frame_3, text="Console Log", font=('Helvetica', 16, 'bold'),
                                           fg_color=("grey90", "gray10"), text_color=['black', 'white'],
                                           corner_radius=6)
        self.lbl_header_333.grid(column=2, row=1, padx=5, pady=2, sticky='we', columnspan=2)

        # FRAME 3.1
        self.btn_generate_views_3 = ctk.CTkButton(self.frame_3, text='Generate new view(s)',
                                                  command=lambda: [utils.generate_new_views(self)])
        self.btn_generate_views_3.grid(column=0, row=3, padx=5, pady=2, sticky='ew')
        self.btn_export_views_3 = ctk.CTkButton(self.frame_3, text='Export data',
                                                command=lambda: [utils.btn_choose_export_data_clicked(self)])
        self.btn_export_views_3.grid(column=0, row=2, padx=5, pady=2, sticky='ew')
        self.view_scroll_frame_3 = utils.ViewsCheckboxFrame(self.frame_3, 'Current Project Views', list([]))
        self.view_scroll_frame_3.grid(column=0, row=4, pady=2, padx=5, sticky='w', rowspan=5)

        self.btn_load_gmshviews_3 = ctk.CTkButton(self.frame_3, text='Reload GMSH views',
                                                  command=lambda: [utils.load_gmsh_data_for_figures(self,
                                                                                                    self.directory_file_project_msh,
                                                                                                    self.directory_project,
                                                                                                    self.directory_file_egsinp)])
        self.btn_load_gmshviews_3.grid(column=0, row=9, padx=5, pady=2, sticky='ew')

        # COLUMN 2 / 3 - LOAD AND VIEW FIGURES
        self.menu_data_3 = ctk.CTkOptionMenu(self.frame_3,
                                             anchor='center')  # variable=self.menu_data, values=menu_datas,
        self.menu_data_3.grid(column=1, row=3, padx=5, pady=2, sticky='ew')
        self.btn_create_1d_ex = ctk.CTkButton(self.frame_3, text='1D line plot\n^ exported',
                                              command=lambda: [utils.one_d_generation_export(self)])
        self.btn_create_1d_ex.grid(column=1, row=4, padx=5, pady=2, sticky='sew')
        self.btn_create_2d_ex = ctk.CTkButton(self.frame_3, text='2D surface plot\n^ exported',
                                              command=lambda: [utils.two_d_generation_export(self)])
        self.btn_create_2d_ex.grid(column=1, row=5, padx=5, pady=2, sticky='new')

        self.btn_create_1d = ctk.CTkButton(self.frame_3, text='1D line plot\n<--- GMSH',
                                           command=lambda: [utils.one_d_generation_gmsh(self)])
        self.btn_create_1d.grid(column=1, row=6, padx=5, pady=2, sticky='sew')
        self.btn_create_2d = ctk.CTkButton(self.frame_3, text='2D surface plot\n<--- GMSH',
                                           command=lambda: [utils.two_d_generation_gmsh(self)])
        self.btn_create_2d.grid(column=1, row=7, padx=5, pady=2, sticky='new')

        # CONSOLE LOG

        self.console_text_box_3 = ctk.CTkTextbox(master=self.frame_3, wrap='word', width=600, height=350,
                                                 fg_color=['grey90',
                                                           'grey10'])  # , text_color=['black', 'white'], state='disabled')
        self.console_text_box_3.grid(column=2, row=2, padx=5, pady=2, sticky='nesw', columnspan=2, rowspan=18)
        self.frame_3.update_idletasks()

        # Load AutoSaved Parameters + populate things

        screen_res = 'Screen resolution:\t\t' + str(int(scale_factor * screen_width)) + ' by ' + str(
            int(scale_factor * screen_height))
        utils.write_to_console_log(self, screen_res)
        utils.write_to_console_log(self,
                                   "MevEGS:\n\tAppearance mode:\t\t" + self.appearance + '\n' + "\n\tColor-theme:\t\t" + self.color_theme)
        utils.create_hover_tooltips(self)
        if os.path.isfile(self.directory_ini + '/mevegs_app.ini'):
            self.check_config_file()
            # try:
            #     utils.load_gmsh_data_for_figures(self, self.directory_file_project_msh,
            #                                  self.directory_project, self.directory_file_egsinp)
            # except:
            #     pass
            
        # Initialization messages to Mevegs console and ToolTips
        self.menu_data, menu_data_path, menu_datas = self.data_list_populate()  # has to be initialized after check_config (for now)
        username = ctk.StringVar()
        username.set("Choose source")
        if self.directory_project != 'Choose Project Directory':
            utils.write_to_console_log(self, "MevEGS:\t\tAuto loaded last workspace - " + self.directory_project)
        
    # Button/Event control

    def scale_window(self,
                     new_scale):  # doesn't seem to stop the RecursionError: maximum recursion depth exceeded while calling a Python object on 125%
        try:
            ctk.set_widget_scaling(new_scale)
        except:
            print('Window can\'t handle this widget size')
            pass

    def btn_update_tabs(self):
        self.frame_inputs.update_idletasks()
        self.frame_1.update_idletasks()
        self.frame_2.update_idletasks()
        self.frame_3.update_idletasks()
        self.gui.update_idletasks()
        if self.directory_file_egsinp.endswith('.egsinp') and self.directory_file_msh.endswith('.msh'):
            self.quick_save()

    def btn_mevegs_explore_clicked(self):
        initial_dir = self.directory_mevegs
        directory_mevegs = filedialog.askdirectory(initialdir=initial_dir)
        self.directory_mevegs = directory_mevegs + '/'
        self.btn_mevegs_explore.configure(text=os.path.basename(os.path.dirname(self.directory_mevegs)))
        utils.write_to_console_log(self, 'MevEGS:\t\tDirectory set - ' + self.directory_mevegs)
        self.btn_mevegs_explore_tip.configure(message=self.directory_mevegs)
        self.frame_1.update_idletasks()
        return self.directory_mevegs

    def btn_postpro_explore_clicked(self):
        initial_dir = self.directory_post_pro
        directory_post_pro = filedialog.askdirectory(initialdir=initial_dir)
        self.directory_post_pro = directory_post_pro + '/'
        self.btn_postpro_explore.configure(text=os.path.basename(os.path.dirname(self.directory_post_pro)))
        utils.write_to_console_log(self, 'MevEGS:\t\tDirectory set - ' + self.directory_post_pro)
        self.btn_postpro_explore_tip.configure(message=self.directory_post_pro)
        self.frame_1.update_idletasks()
        return self.directory_post_pro

    def btn_project_explore_clicked(self):
        initial_dir = self.directory_project
        directory_project = filedialog.askdirectory(initialdir=initial_dir)
        self.directory_project = directory_project + '/'
        self.btn_project_explore.configure(text=os.path.basename(os.path.dirname(self.directory_project)))
        utils.update_phasespace_warning_label(self)
        utils.write_to_console_log(self, 'MevEGS:\t\tProject loaded - ' + self.directory_project)
        # project_save_files = glob.glob(self.directory_project + '*.save', recursive=False)
        # if len(project_save_files) == 1:
        #     self.load_dict_from_file(project_save_files[0])
        # elif not project_save_files:
        project_egsinp_files = glob.glob(self.directory_project + '*.egsinp', recursive=False)
        if len(project_egsinp_files) == 1:
            self.directory_file_egsinp = project_egsinp_files[0]
            self.load_proper_filenames_from_dict(self.btn_egsinp_explore, self.directory_file_egsinp)
        project_msh_files = glob.glob(self.directory_project + '*.msh', recursive=False)
        for item in project_msh_files:
            if item.endswith('.results.msh'.lower()):
                project_msh_files.remove(item)
        for item in project_msh_files:
            if item.endswith('.ptracks.msh'.lower()):
                project_msh_files.remove(item)
        if len(project_msh_files) == 1:
            self.directory_file_msh = project_msh_files[0]
            self.load_proper_filenames_from_dict(self.btn_mesh_explore, self.directory_file_msh)
        project_results_msh_files = glob.glob(self.directory_project + '*results.msh'.lower(), recursive=False)
        if len(project_results_msh_files) == 1:
            self.directory_file_project_msh = project_results_msh_files[0]
            self.btn_results_mesh_explore.configure(
                text='.'.join(os.path.basename(self.directory_file_project_msh).split('.')[:-2]))
            path_res_mesh = '  /  '.join(os.path.dirname(self.directory_file_project_msh).split('/')[-2:])
            name_res_mesh = os.path.basename('.'.join(os.path.basename(self.directory_file_project_msh).split('.')[:-2]))
            self.lbl_results_header_3.configure(text=path_res_mesh + '  /  ' + name_res_mesh)
        utils.update_hover_tooltips(self)
        if self.directory_file_project_msh.startswith("Choose"):
            pass
        else:
            utils.load_gmsh_data_for_figures(self, self.directory_file_project_msh,
                                             self.directory_project, self.directory_file_egsinp)
        # try:
        #     utils.load_gmsh_data_for_figures(self, self.directory_file_project_msh,
        #                                  self.directory_project, self.directory_file_egsinp)
        # except:
        #     pass
        self.frame_inputs.update_idletasks()
        self.gui.update_idletasks()
        return self.directory_project

    def btn_egsinp_explore_clicked(self):
        initial_file = self.directory_file_egsinp
        directory_file_egsinp = filedialog.askopenfilename(initialfile=initial_file,
                                                           filetypes=[('egsinp files', '*.egsinp')])
        self.directory_file_egsinp = directory_file_egsinp
        self.btn_egsinp_explore.configure(text='.'.join(os.path.basename(self.directory_file_egsinp).split('.')[:-1]))
        utils.write_to_console_log(self, 'MevEGS:\t\tFile loaded - ' + self.directory_file_egsinp)
        self.btn_egsinp_explore_tip.configure(message=self.directory_file_egsinp)
        self.frame_inputs.update_idletasks()
        return self.directory_file_egsinp

    def btn_mesh_explore_clicked(self):
        initial_file = self.directory_file_msh
        directory_file_msh = filedialog.askopenfilename(initialfile=initial_file, filetypes=[('mesh files', '*.msh')])
        self.directory_file_msh = directory_file_msh
        self.btn_mesh_explore.configure(text='.'.join(os.path.basename(self.directory_file_msh).split('.')[:-1]))
        utils.write_to_console_log(self, 'MevEGS:\t\tFile loaded - ' + self.directory_file_msh)
        self.btn_mesh_explore_tip.configure(message=self.directory_file_msh)
        self.frame_1.update_idletasks()
        return self.directory_file_msh

    def btn_pegs_explore_clicked(self):
        directory_file_pegs = filedialog.askopenfilename(initialfile=os.path.basename(self.directory_file_pegs),
                                                         filetypes=[('pegs files', '*.pegs4dat')])
        self.directory_file_pegs = directory_file_pegs
        self.btn_pegs_explore.configure(text='.'.join(os.path.basename(self.directory_file_pegs).split('.')[:-1]))
        utils.write_to_console_log(self, 'MevEGS:\t\tFile loaded - ' + self.directory_file_pegs)
        self.btn_pegs_explore_tip.configure(message=self.directory_file_pegs)
        self.frame_1.update_idletasks()
        return self.directory_file_pegs

    def btn_cluster_explore_clicked(self):
        directory_ini = filedialog.askdirectory(initialdir=self.directory_ini)
        self.directory_ini = directory_ini + '/'
        self.btn_cluster_explore.configure(text=os.path.basename(os.path.dirname(self.directory_ini)))
        utils.write_to_console_log(self, 'MevEGS:\t\tDirectory set - ' + self.directory_ini)
        self.btn_cluster_explore_tip.configure(message=self.directory_ini)
        self.frame_inputs.update_idletasks()
        return self.directory_ini

    def btn_egsinp_file_open_clicked(self):  # for a non-Windows solution, try webbrowser.open()
        path = os.path.dirname(self.directory_file_egsinp)
        os.startfile(path)

    def btn_msh_file_open_clicked(self):
        path = os.path.dirname(self.directory_file_msh)
        os.startfile(path)

    def btn_project_msh_file_open_clicked(self):
        path = os.path.dirname(self.directory_file_project_msh)
        os.startfile(path)

    def btn_project_open_clicked(self):
        path = self.directory_project
        os.startfile(path)

    def source_list_populate(self):
        menu_sources = ['None']
        menu_sources_path = glob.glob(self.directory_ini + 'Source_Phasespace_Files/*', recursive=False)
        for item_ in menu_sources_path:
            menu_sources.append(os.path.basename(item_))
        menu_source = ctk.StringVar()
        menu_source.set("Choose source")
        self.frame_1.update_idletasks()
        return menu_source, menu_sources_path, menu_sources

    def username_list_choice(self):
        usernames = ['Choose cluster username', 'bwz', 'dmm', 'las', 'MDE', 'mjr', 'wjl']
        if os.path.isfile(self.directory_ini + 'mevegs_app.ini'):
            with open(self.directory_ini + 'mevegs_app.ini', "r") as _file:
                pd_dataframe = pd.read_csv(_file, header=None)
                saved_info_dict = dict(zip(pd_dataframe[0], pd_dataframe[1]))
                username = ctk.StringVar()
                username.set(saved_info_dict['username'])
        else:
            username = ctk.StringVar()
            username.set("Choose cluster username")
        self.frame_2.update_idletasks()
        return username, usernames

    def data_list_populate(self):
        menu_datas = ['None']
        menu_datas_path = glob.glob(self.directory_project + 'exports/*', recursive=False)
        for item_ in menu_datas_path:
            if not os.path.basename(item_).startswith('line_gmsh'):
                if not os.path.basename(item_).startswith('plane_gmsh'):
                    menu_datas.append(os.path.basename(item_))
        menu_data = ctk.StringVar()
        self.menu_data_3.configure(values=menu_datas)
        self.menu_data_3.set("Choose exported data")
        self.frame_3.update_idletasks()
        return menu_data, menu_datas_path, menu_datas

    def btn_ptracks_clicked(self):
        directory_egsinp, file_egsinp = os.path.split(self.directory_file_egsinp)
        if os.path.isfile(self.directory_mevegs + file_egsinp):
            self.overwrite_defender_ptracks()
        else:
            self.visualize_geometry()

    def btn_run_mevegs_clicked(self, entry):
        directory_egsinp, file_egsinp = os.path.split(self.directory_file_egsinp)
        _, file_msh = os.path.split(self.directory_file_msh)
        results_msh = os.path.splitext(file_egsinp)[0] + '_' + os.path.splitext(file_msh)[0] + '.results.msh'
        msh_results_msh = results_msh.split('.results.msh')[0] + '.msh.results.msh'
        if os.path.isfile(self.directory_mevegs + results_msh) or os.path.isfile(
                self.directory_mevegs + msh_results_msh):
            self.overwrite_defender_mevegs()  # file overwrite check
        else:
            self.run_mevegs()  # run

    def btn_clean_up_clicked(self):
        _, file_egsinp = os.path.split(self.directory_file_egsinp)
        _, file_msh = os.path.split(self.directory_file_msh)
        results_msh = file_egsinp.split('.egsinp')[0] + '_' + file_msh.split('.msh')[0] + '.results.msh'
        msh_results_msh = results_msh.split('.results.msh')[0] + '.msh.results.msh'
        if os.path.isfile(self.directory_mevegs + msh_results_msh):  # lose first .msh in filename
            os.replace(self.directory_mevegs + msh_results_msh, self.directory_mevegs + results_msh)
        items_egsinfo = glob.glob(self.directory_mevegs + '/*.egsinfo', recursive=False)
        for object_ in items_egsinfo:  # renaming egsinfo files
            if os.path.isfile(object_):
                os.replace(object_,
                           self.directory_mevegs + file_egsinp.split('.egsinp')[0] + '_' + file_msh.split('.msh')[
                               0] + '.results.msh.egsinfo')
        if os.path.isfile(self.directory_mevegs + results_msh):
            if os.path.isdir(self.directory_project) and os.path.isfile(self.directory_project + results_msh):
                self.topframe = ctk.CTkToplevel(self.gui)  # , fg_color="steel blue"
                self.topframe.grab_set()
                self.topframe.geometry("700x300")
                self.topframe.attributes('-topmost', True)
                self.topframe.update()
                self.topframe.focus()
                self.topframe.title('File already exists')
                self.topframe.grid_columnconfigure(0, weight=1)
                self.topframe.grid_columnconfigure(1, weight=1)
                self.topframe.grid_columnconfigure(2, weight=1)
                self.topframe.grid_rowconfigure(0, weight=1)
                self.topframe.grid_rowconfigure(1, weight=1)
                self.warning = ctk.CTkLabel(self.topframe, font=("Arial", 20),
                                            text='Do you want to overwrite:\n\n' + results_msh.split('.results.msh')[
                                                0] + '\n\n and associated simulation files in\n\n' + self.directory_project + '?')
                self.warning.grid(column=0, row=0, pady=10, padx=10, columnspan=3, sticky='nsew')
                self.yes_button = ctk.CTkButton(self.topframe, text='Yes, proceed',
                                                command=lambda: [self.btn_exit_popup(), self.copy_mevegs_sumulation()])
                self.yes_button.grid(column=0, row=1, pady=10, padx=10, sticky='nesw')
                self.exit_button = ctk.CTkButton(master=self.topframe, text='No, cancel', command=self.btn_exit_popup)
                self.exit_button.grid(column=1, row=1, pady=10, padx=10, sticky='nesw')
                self.rename_button = ctk.CTkButton(master=self.topframe,
                                                   text='No, make or choose\nnew project directory',
                                                   command=lambda: [self.btn_exit_popup(),
                                                                    self.set_project_directory_mevegs()])
                self.rename_button.grid(column=2, row=1, pady=10, padx=10, sticky='nesw')
            else:
                self.copy_mevegs_sumulation()

    def btn_restore_mevegs_clicked(self):
        os.chdir(self.directory_mevegs)
        items_lock = glob.glob(self.directory_mevegs + '*.lock', recursive=False)
        for object_ in items_lock:
            if os.path.isfile(object_):
                os.remove(object_)
        items_egsinp = glob.glob(self.directory_mevegs + '*.egsinp', recursive=False)
        for object_ in items_egsinp:
            if os.path.isfile(object_):
                os.remove(object_)
        items_msh = glob.glob(self.directory_mevegs + '*.msh', recursive=False)
        for object_ in items_msh:
            if os.path.isfile(object_):
                os.remove(object_)
        items_egslog = glob.glob(self.directory_mevegs + '*.egslog', recursive=False)
        for object_ in items_egslog:
            if os.path.isfile(object_):
                os.remove(object_)
        items_mevegs_job_logs = glob.glob(self.directory_mevegs + 'mevegs_job_thread_*.mvgs', recursive=False)
        for object_ in items_mevegs_job_logs:
            if os.path.isfile(object_):
                os.remove(object_)
        items_egsinfo = glob.glob(self.directory_mevegs + '/*.egsinfo', recursive=False)
        for object_ in items_egsinfo:
            if os.path.isfile(object_):
                os.remove(object_)
        items_egsrun = glob.glob(self.directory_mevegs + '/egsrun_*', recursive=False)
        for object_ in items_egsrun:
            if os.path.isdir(object_):
                shutil.rmtree(object_)  # junk directories
            else:
                os.remove(object_)  # junk files
        items_egsdat = glob.glob(self.directory_mevegs + '/*.egsdat', recursive=False)
        for object_ in items_egsdat:
            if os.path.isfile(object_):
                os.remove(object_)  # junk files
        items_egsphsp1 = glob.glob(self.directory_mevegs + '/*.egsphsp1', recursive=False)
        for object_ in items_egsphsp1:
            if os.path.isfile(object_):
                os.remove(object_)
        if os.path.isfile(self.directory_mevegs + 'mevegs_visualize_console_output_1.mvgs'):
            os.remove(self.directory_mevegs + 'mevegs_visualize_console_output_1.mvgs')
        items_ptracks = glob.glob(self.directory_mevegs + '/*.ptracks', recursive=False)
        for object_ in items_ptracks:
            if os.path.isfile(object_):
                os.remove(object_)
        items_ptracks_opt = glob.glob(self.directory_mevegs + '/*.ptracks.msh.opt', recursive=False)
        for object_ in items_ptracks_opt:
            if os.path.isfile(object_):
                os.remove(object_)
        if os.path.isfile(self.directory_mevegs + str(self.menu_source_1.get())):
            os.remove(self.directory_mevegs + str(self.menu_source_1.get()))
        os.chdir(self.directory_ini)
        # if os.path.isfile('mevegs_cluster_console_output_1.mvgs'):
        #     os.remove('mevegs_cluster_console_output_1.mvgs')

    def btn_save_state_clicked(self):
        save_dict = self.mevegs_save_dictionary()
        self.file_save(save_dict)

    def btn_load_state_clicked(self):
        file_ = filedialog.askopenfile(filetypes=[('save files', '*.save')])
        if file_ is None:  # asksaveasfile return `None` if dialog closed with "cancel".
            return
        self.load_dict_from_file(file_)
        utils.write_to_console_log(self, "MevEGS:\t\tLoaded project - " + self.directory_project)
        self.gui.update_idletasks()

    def mevegs_save_dictionary(self):
        save_dict = {
            'mevegs': self.directory_mevegs,
            'pegs': self.directory_file_pegs,
            'post_pro': self.directory_post_pro,
            'egsinp': self.directory_file_egsinp,
            'msh': self.directory_file_msh,
            'project': self.directory_project,
            'results': self.directory_file_project_msh,
            'source': self.menu_source_1.get(),
            'data': self.menu_data_3.get(),
            'numjobs': self.entry_njobs.get(),
            'username': self.optionmenu_user_2.get(),
            'appearance': ctk.get_appearance_mode(),
            'color_theme': ctk.ThemeManager._currently_loaded_theme
        }
        return save_dict

    def btn_exit_program(self):
        save_dict = self.mevegs_save_dictionary()
        with open(self.directory_ini + '/mevegs_app.ini', 'w', newline='') as myfile:
            w = csv.writer(myfile)
            w.writerows(save_dict.items())
        self.gui.update_idletasks()
        self.gui.quit()
        self.gui.destroy()
        for after_id in self.gui.tk.eval('after info').split():  # Allows program to end by catching many of the 'after'
            self.gui.after_cancel(after_id)  # commands that CTk runs behind scenes
        # """Properly terminates the gui."""
        # # stop all .after callbacks to avoid error message "Invalid command ..." after destruction
        # # self.stop_after_callbacks() shouldn't be needed
        # if not self.terminated:
        #     self.terminated = True
        #     self.gui.destroy()

    def btn_emergency_destroy(self):
        if gmsh.isInitialized():
            gmsh.clear()
            gmsh.finalize()
        self.gui.destroy()

    def btn_on_x_exit(self):
        self.btn_exit_program()

    def btn_exit_popup(self):
        self.topframe.destroy()

    # called functions

    def check_config_file(self):
        self.load_dict_from_file(self.directory_ini + '/mevegs_app.ini')

    def load_dict_from_file(self, _file):
        pd_dataframe = pd.read_csv(_file, header=None)
        saved_info_dict = dict(zip(pd_dataframe[0], pd_dataframe[1]))
        self.directory_mevegs = saved_info_dict['mevegs']
        self.directory_post_pro = saved_info_dict['post_pro']
        self.directory_file_egsinp = saved_info_dict['egsinp']
        self.directory_file_msh = saved_info_dict['msh']
        self.directory_file_pegs = saved_info_dict['pegs']
        self.directory_project = saved_info_dict['project']
        self.njobs = saved_info_dict['numjobs']
        self.directory_file_project_msh = saved_info_dict['results']
        self.username = saved_info_dict['username']
        self.menu_source = str(saved_info_dict['source'])
        self.gmsh_views = ''
        self.gmsh_groups = ''
        path_res_mesh = ' / '.join(os.path.dirname(self.directory_file_project_msh).split('/')[-2:])
        name_res_mesh = os.path.basename('.'.join(os.path.basename(self.directory_file_project_msh).split('.')[:-2]))
        self.lbl_results_header_3.configure(text=path_res_mesh + ' / ' + name_res_mesh)
        self.load_proper_dirnames_from_dict(self.btn_mevegs_explore, self.directory_mevegs)
        self.load_proper_dirnames_from_dict(self.btn_postpro_explore, self.directory_post_pro)
        self.load_proper_dirnames_from_dict(self.btn_project_explore, self.directory_project)
        self.load_proper_dirnames_from_dict(self.btn_cluster_explore, self.directory_ini)
        self.load_proper_filenames_from_dict(self.btn_egsinp_explore, self.directory_file_egsinp)
        self.load_proper_filenames_from_dict(self.btn_mesh_explore, self.directory_file_msh)
        self.load_proper_filenames_from_dict(self.btn_pegs_explore, self.directory_file_pegs)
        if self.directory_file_project_msh.startswith("Choose"):
            self.btn_results_mesh_explore.configure(text=self.directory_file_project_msh)
        else:
            self.btn_results_mesh_explore.configure(text='.'.join(os.path.basename(self.directory_file_project_msh).split('.')[:-2]))
        self.job_number.set(self.njobs)
        if self.directory_file_egsinp.startswith("Choose") or self.directory_file_msh.startswith("Choose"):
            self.gui.title('MevEGS')
        else:
            self.gui.title('MevEGS - ' + (self.directory_file_egsinp.split('/')[-1]).split('.egsinp')[0] + '_' +
                       (self.directory_file_msh.split('/')[-1]).split('.msh')[0])
        self.optionmenu_user_2.set(self.username)
        if os.path.isfile(self.directory_file_project_msh):
            utils.load_gmsh_data_for_figures(self, self.directory_file_project_msh,
                                             self.directory_project, self.directory_file_egsinp)
        self.btn_results_retrieve_2.configure(text='Open directory\n' +
                                                         os.path.basename(os.path.dirname(self.directory_project)))
        self.menu_source_1.set(self.menu_source)
        utils.update_hover_tooltips(self)
        utils.update_phasespace_warning_label(self)
        self.gui.update_idletasks()

    def load_proper_filenames_from_dict(self, _object, name):
        if name.startswith("Choose"):
            _object.configure(text=name)
        else:
            _object.configure(text='.'.join(os.path.basename(name).split('.')[:-1]))

    def load_proper_dirnames_from_dict(self, _object, name):
        if name.startswith("Choose"):
            _object.configure(text=name)
        else:
            _object.configure(text=os.path.basename(os.path.dirname(name)))

    def replace_ncase(self, file_name):
        f1 = open(file_name, 'r')
        f2 = open('temp.egsinp', 'w')
        # Below code writes temp file without most of ausgab objects (if present) which interfere with particle track definition
        writing = True
        for line in f1:
            if re.search('ncase', line):
                f2.write('\tncase = 1000' + '\n')
            elif re.search(':start geometry definition:', line):
                writing = False
            elif re.search(':stop geometry definition:', line):
                writing = True
            elif re.search(':start ausgab object definition:', line):
                writing = False
            elif re.search(':stop ausgab object definition:', line):
                writing = True
            if writing:
                f2.write(line)
        f1.close()
        f2.close()
        # below code overwrites (previously copied) .egsinp, removing straggling lines and inserts ausgab object at end of file to capture ptracks
        f1 = open(file_name, 'w')
        f2 = open('temp.egsinp', 'r')
        for line in f2:
            if re.search(':stop geometry definition:', line):
                pass
            elif re.search(':stop ausgab object definition:', line):
                pass
            else:
                f1.write(line)
        f1.write(
            "\n:start ausgab object definition:\n\t:start ausgab object:\n\t\tName = name1\n\t\tlibrary = egs_track_scoring\n\t\tscore photons = yes\n\t\tscore electrons = yes\n\t\tscore positrons = yes\n\t\tstop scoring = 1024\n\t\tbuffer Size = 1024\n\t:stop ausgab object:\n:stop ausgab object definition:\n")
        f1.close()
        f2.close()
        os.remove('temp.egsinp')

    def file_save(self, workspace_dict):
        _, file_egsinp = os.path.split(self.directory_file_egsinp)
        _, file_msh = os.path.split(self.directory_file_msh)
        default_filename = file_egsinp.split('.egsinp')[0] + '_' + file_msh.split('.msh')[0]
        file_ = filedialog.asksaveasfile(title='Save current workspace fields', initialfile=default_filename,
                                         initialdir=self.directory_project, mode='w', defaultextension=".save",
                                         filetypes=(('MevEGS Project Save File', '.save'),))
        if file_ is None:  # asksaveasfile return `None` if dialog closed with "cancel".
            return
        with open(file_.name, 'w', newline='') as myfile:
            w = csv.writer(myfile)
            w.writerows(workspace_dict.items())
        self.gui.title('MevEGS - ' + (file_.name.split('/')[-1]).split('.save')[0])
        utils.write_to_console_log(self, 'MevEGS:\t\tProject saved as: ' + file_.name + '\nin ' +
                                   self.directory_project)
        self.gui.update_idletasks()

    def quick_save(self):
        save_dict = self.mevegs_save_dictionary()
        _, file_egsinp = os.path.split(self.directory_file_egsinp)
        _, file_msh = os.path.split(self.directory_file_msh)
        file_ = file_egsinp.split('.egsinp')[0] + '_' + file_msh.split('.msh')[0]
        with open(self.directory_project + file_ + '.save', 'w', newline='') as myfile:
            w = csv.writer(myfile)
            w.writerows(save_dict.items())
        self.gui.title('MevEGS - ' + file_)
        textbox_text = self.console_text_box_input.get('2.20', '2.33')  # grabs most recent quick_save output
        if textbox_text == 'Project saved':  # doesn't print save note every time a tab is changed unless work ...
            pass  # ...has happened in between
        else:
            utils.write_to_console_log(self, 'MevEGS:\t\tProject saved as: ' + file_ + '.save\nin ' +
                                   self.directory_project)
        self.gui.update_idletasks()

    def visualize_geometry(self):
        shutil.copy2(self.directory_file_msh, self.directory_mevegs)
        shutil.copy2(self.directory_file_egsinp, self.directory_mevegs)
        if os.path.isfile(self.directory_ini + 'Source_Phasespace_Files/' + str(self.menu_source_1.get())):
            shutil.copy2(self.directory_ini + 'Source_Phasespace_Files/' + str(self.menu_source_1.get()),
                         self.directory_mevegs)
        time.sleep(2)
        _, file_egsinp = os.path.split(self.directory_file_egsinp)
        os.chdir(self.directory_mevegs)
        self.replace_ncase(file_egsinp)
        _, file_msh = os.path.split(self.directory_file_msh)
        _, file_pegs = os.path.split(self.directory_file_pegs)
        numjobs = 1
        # bar_progress = -1
        total_progress = [0] * int(numjobs)
        command = 'mevegs -i ' + file_egsinp + ' -p ' + file_pegs + ' ' + file_msh
        job_file_name = 'mevegs_visualize_console_output_1.mvgs'
        with open(job_file_name, "w") as f:
            process = subprocess.Popen(['cmd', '/c', command], stdout=f, stderr=subprocess.STDOUT, bufsize=0)

        self.topframe = ctk.CTkToplevel(self.gui)  # , fg_color="DarkSlateGray4"
        self.topframe.after(500, self.topframe.grab_set())
        self.topframe.geometry("500x200")
        self.topframe.attributes('-topmost', True)
        self.topframe.geometry("+0+0")
        self.topframe.update()
        self.topframe.focus()
        self.topframe.title('Mevegs Job Progress - Visualize')
        self.mevegs_progress_bar = ctk.CTkProgressBar(self.topframe)
        self.mevegs_progress_bar.pack(pady=2, padx=10, side='top', fill='both', expand=True)
        self.mevegs_progress_bar.set(self.bar_progress)
        self.percent_label = ctk.CTkLabel(self.topframe, text='0%')
        self.percent_label.pack(pady=2, padx=10, )
        self.exit_button = ctk.CTkButton(master=self.topframe, text='Close on completion', command=self.btn_exit_popup)
        self.exit_button.pack(pady=2, padx=10, side='top', fill='both', expand=True)
        self.gui.update_idletasks()
        self.topframe.update()
        time.sleep(3)
        # Update progress of simulation
        while self.bar_progress < 1:
            total_progress = self.parse_progress_data(numjobs, total_progress, 'mevegs_visualize_console_output_')
            self.bar_progress = self.return_progress(total_progress, numjobs)
            time.sleep(.5)
            if self.bar_progress > 11:
                break
        else:
            utils.write_to_console_log(self, "MevEGS:\t\tSimulation Complete")

        self.topframe.destroy()
        file_e = file_egsinp.split('.egsinp')[0]
        file_ptracks = str(file_e + '.ptracks')
        file_m = file_msh.split('.msh')[0]
        ptracks_output_file = str(file_e + '_' + file_m + '.ptracks.msh')
        # Limit is a "Hard cutoff number of tracks (limit) beyond which no more tracks will be loaded and converted.
        # Setting a cutoff can be useful when there are many tracks, and you wish to lower the memory load of viewing the output in gmsh."
        # limit=10000  # This is an optional arg... may wish to make this a gui option
        # units='mm'  # This is an optional arg... may wish to make this a gui option
        pt.process_ptracks(file_ptracks, ptracks_output_file, limit=10000,
                           units='mm')  # Post_processing.py function added
        if os.path.isfile(self.directory_mevegs + ptracks_output_file):
            if os.path.isdir(self.directory_project) and os.path.isfile(self.directory_project + ptracks_output_file):
                self.topframe = ctk.CTkToplevel(self.gui)  # , fg_color="steel blue"
                self.topframe.grab_set()
                self.topframe.geometry("700x300")
                self.topframe.attributes('-topmost', True)
                self.topframe.update()
                self.topframe.focus()
                self.topframe.title('File already exists')
                self.topframe.grid_columnconfigure(0, weight=1)
                self.topframe.grid_columnconfigure(1, weight=1)
                self.topframe.grid_columnconfigure(2, weight=1)
                self.topframe.grid_rowconfigure(0, weight=1)
                self.topframe.grid_rowconfigure(1, weight=1)
                self.warning = ctk.CTkLabel(self.topframe, font=("Arial", 20),
                                            text='Do you want to overwrite:\n' + ptracks_output_file +
                                                 '\n and associated visualization files in\n' + self.directory_project + '?')
                self.warning.grid(column=0, row=0, pady=10, padx=10, columnspan=3, sticky='nsew')
                self.yes_button = ctk.CTkButton(self.topframe, text='Yes, proceed',
                                                command=lambda: [self.btn_exit_popup(),
                                                                 self.copy_ptracks_visualization(file_ptracks,
                                                                                                 ptracks_output_file),
                                                                 self.gmsh_visuals()])
                self.yes_button.grid(column=0, row=1, pady=10, padx=10, sticky='nesw')
                self.exit_button = ctk.CTkButton(master=self.topframe, text='No, cancel',
                                                 command=lambda: [self.btn_exit_popup(),
                                                                  self.cleanup_ptracks(file_ptracks,
                                                                                       ptracks_output_file)])
                self.exit_button.grid(column=1, row=1, pady=10, padx=10, sticky='nesw')
                self.choose_button = ctk.CTkButton(master=self.topframe, text='No, make/choose\nnew project directory',
                                                   command=lambda: [self.btn_exit_popup(),
                                                                    self.set_project_directory_ptracks(file_ptracks,
                                                                                                       ptracks_output_file)])
                self.choose_button.grid(column=2, row=1, pady=10, padx=10, sticky='nesw')
            else:
                self.copy_ptracks_visualization(file_ptracks, ptracks_output_file)
                self.gmsh_visuals()
        if os.path.isfile(self.directory_mevegs + str(self.menu_source_1.get())):
            os.remove(self.directory_mevegs + str(self.menu_source_1.get()))
        os.chdir(self.directory_ini)

    def set_project_directory_ptracks(self, egsinp_ptracks_file, ptracks_output_file):
        directory_project = filedialog.askdirectory()
        if directory_project == "":
            self.cleanup_ptracks(egsinp_ptracks_file, ptracks_output_file)
        else:
            self.directory_project = directory_project + '/'
            self.btn_project_explore.configure(text=self.directory_project)
            self.copy_ptracks_visualization(egsinp_ptracks_file, ptracks_output_file)
            self.gmsh_visuals()

    def cleanup_ptracks(self, egsinp_ptracks_file, ptracks_output_file):
        _, file_egsinp = os.path.split(self.directory_file_egsinp)
        _, file_msh = os.path.split(self.directory_file_msh)
        file_e = file_egsinp.split('.egsinp')[0]
        os.replace(self.directory_mevegs + 'mevegs_visualize_console_output_1.mvgs',
                   self.directory_project + 'mevegs_visualize_console_output_1.mvgs')
        os.remove(self.directory_mevegs + file_egsinp)
        os.remove(self.directory_mevegs + file_msh)
        os.remove(self.directory_mevegs + ptracks_output_file.split('.ptracks.msh')[
            0] + '.msh.results.msh')  # ptracks output file is name.egsinp+_+ name.msh without extensions
        os.remove(self.directory_mevegs + file_e + '.egsdat')
        os.remove(self.directory_mevegs + egsinp_ptracks_file)
        os.remove(self.directory_mevegs + ptracks_output_file.split('.ptracks.msh')[0] + '.msh.results.msh.egsinfo')
        os.remove(self.directory_mevegs + ptracks_output_file)
        os.remove(self.directory_mevegs + ptracks_output_file.split('.ptracks.msh')[0] + '.ptracks.msh.opt')
        if os.path.isfile(self.directory_mevegs + str(self.menu_source_1.get())):
            os.remove(self.directory_mevegs + str(self.menu_source_1.get()))

    def copy_ptracks_visualization(self, egsinp_ptracks_file, ptracks_output_file):
        os.makedirs(self.directory_project, exist_ok=True)
        os.replace(self.directory_mevegs + egsinp_ptracks_file, self.directory_project + egsinp_ptracks_file)
        os.replace(self.directory_mevegs + ptracks_output_file.split('.ptracks.msh')[0] + '.msh.results.msh.egsinfo',
                   self.directory_project + ptracks_output_file.split('.ptracks.msh')[0] + '.results.msh.egsinfo')
        os.replace(self.directory_mevegs + ptracks_output_file, self.directory_project + ptracks_output_file)
        os.replace(self.directory_mevegs + ptracks_output_file.split('.ptracks.msh')[0] + '.ptracks.msh.opt',
                   self.directory_project + ptracks_output_file.split('.ptracks.msh')[0] + '.ptracks.msh.opt')
        os.replace(self.directory_mevegs + 'mevegs_visualize_console_output_1.mvgs',
                   self.directory_project + 'mevegs_visualize_console_output_1.mvgs')
        _, file_egsinp = os.path.split(self.directory_file_egsinp)
        _, file_msh = os.path.split(self.directory_file_msh)
        file_e = file_egsinp.split('.egsinp')[0]
        os.remove(self.directory_mevegs + file_egsinp)
        os.remove(self.directory_mevegs + file_msh)
        os.remove(self.directory_mevegs + ptracks_output_file.split('.ptracks.msh')[0] + '.msh.results.msh')
        os.remove(self.directory_mevegs + file_e + '.egsdat')

    def overwrite_defender_ptracks(self):
        self.topframe = ctk.CTkToplevel(self.gui)  # , fg_color="firebrick4"
        self.topframe.grab_set()
        self.topframe.geometry("700x300")
        self.topframe.attributes('-topmost', True)
        self.topframe.update()
        self.topframe.focus()
        self.topframe.title('File Overwrite Warning')
        self.topframe.grid_columnconfigure(0, weight=1)
        self.topframe.grid_columnconfigure(1, weight=1)
        self.topframe.grid_rowconfigure(0, weight=1)
        self.topframe.grid_rowconfigure(1, weight=1)
        _, file_egsinp = os.path.split(self.directory_file_egsinp)
        self.warning = ctk.CTkLabel(self.topframe, font=("Arial", 20),
                                    text='Do you want to overwrite:\n' + file_egsinp + '\nin\n' + self.directory_mevegs + '?')
        self.warning.grid(column=0, row=0, pady=10, padx=10, columnspan=2, sticky='nsew')
        self.yes_button = ctk.CTkButton(self.topframe, text='Yes, proceed',
                                        command=lambda: [self.btn_exit_popup(), self.visualize_geometry()])
        self.yes_button.grid(column=0, row=1, pady=10, padx=10, sticky='nesw')
        self.exit_button = ctk.CTkButton(master=self.topframe, text='No, cancel', command=self.btn_exit_popup)
        self.exit_button.grid(column=1, row=1, pady=10, padx=10, sticky='nesw')

    def gmsh_visuals(self):
        _, file_egsinp = os.path.split(self.directory_file_egsinp)
        _, file_msh = os.path.split(self.directory_file_msh)
        default_filename = file_egsinp.split('.egsinp')[0] + '_' + file_msh.split('.msh')[0]
        gmsh.initialize()
        gmsh.open(self.directory_file_msh)
        gmsh.merge(self.directory_project + default_filename + '.ptracks.msh')
        gmsh.fltk.run()
        gmsh.finalize()
        # gmsh takes focus from MevEGS gui and won't give it back until gmsh is closed

    def overwrite_defender_mevegs(self):  # file_name here is .msh.results.msh
        _, file_egsinp = os.path.split(self.directory_file_egsinp)
        _, file_msh = os.path.split(self.directory_file_msh)
        msh_results_msh = file_egsinp.split('.egsinp')[0] + '_' + file_msh.split('.msh')[0] + '.msh.results.msh'
        self.topframe = ctk.CTkToplevel(self.gui)  # , fg_color="firebrick4"
        self.topframe.grab_set()
        self.topframe.geometry("700x300")
        self.topframe.attributes('-topmost', True)
        self.topframe.update()
        self.topframe.focus()
        self.topframe.title('File Overwrite Warning')
        self.topframe.grid_columnconfigure(0, weight=1)
        self.topframe.grid_columnconfigure(1, weight=1)
        self.topframe.grid_rowconfigure(0, weight=1)
        self.topframe.grid_rowconfigure(1, weight=1)
        self.warning = ctk.CTkLabel(self.topframe, font=("Arial", 20),
                                    text='Do you want to overwrite your simulation:\n\n' +
                                         msh_results_msh.split('.msh.results.msh')[
                                             0] + '\n\nin\n\n' + self.directory_mevegs + '?')
        self.warning.grid(column=0, row=0, pady=10, padx=10, columnspan=2, sticky='nsew')
        self.yes_button = ctk.CTkButton(self.topframe, text='Yes, proceed',
                                        command=lambda: [self.btn_exit_popup(), self.run_mevegs()])
        self.yes_button.grid(column=0, row=1, pady=2, padx=5, sticky='nesw')
        self.exit_button = ctk.CTkButton(master=self.topframe, text='No, cancel', command=self.btn_exit_popup)
        self.exit_button.grid(column=1, row=1, pady=2, padx=5, sticky='nesw')

    def overwrite_defender_project(self):  # file_name is .results.msh
        _, file_egsinp = os.path.split(self.directory_file_egsinp)
        _, file_msh = os.path.split(self.directory_file_msh)
        results_msh = file_egsinp.split('.egsinp')[0] + '_' + file_msh.split('.msh')[0] + '.results.msh'
        self.topframe = ctk.CTkToplevel(self.gui)  # , fg_color="firebrick4"
        self.topframe.grab_set()
        self.topframe.geometry("700x300")
        self.topframe.attributes('-topmost', True)
        self.topframe.update()
        self.topframe.focus()
        self.topframe.title('File Overwrite Warning')
        self.topframe.grid_columnconfigure(0, weight=1)
        self.topframe.grid_columnconfigure(1, weight=1)
        self.topframe.grid_columnconfigure(2, weight=1)
        self.topframe.grid_rowconfigure(0, weight=1)
        self.topframe.grid_rowconfigure(1, weight=1)
        self.warning = ctk.CTkLabel(self.topframe, font=("Arial", 18),
                                    text='Project \"' + results_msh.split('.results.msh')[
                                        0] + '\"\nis located in\n' + self.directory_project + '\n\n\nDo you want to?')
        self.warning.grid(column=0, row=0, pady=10, padx=10, columnspan=3, sticky='nsew')
        self.yes_button = ctk.CTkButton(self.topframe, text='Proceed,\nOverwrite',
                                        command=lambda: [self.btn_exit_popup(), self.copy_mevegs_sumulation()])
        self.yes_button.grid(column=0, row=1, pady=10, padx=10, sticky='nesw')
        self.rename_button = ctk.CTkButton(self.topframe, text='Choose/make new project directory,\nProceed',
                                           command=lambda: [self.btn_exit_popup(), self.set_project_directory_mevegs()])
        self.rename_button.grid(column=1, row=1, pady=10, padx=10, sticky='nesw')
        self.exit_button = ctk.CTkButton(master=self.topframe, text='Abort', command=self.btn_exit_popup)
        self.exit_button.grid(column=2, row=1, pady=10, padx=10, sticky='nesw')

    def run_mevegs(self):
        if os.path.isfile(self.directory_ini + 'Source_Phasespace_Files/' + str(self.menu_source_1.get())):
            shutil.copy2(self.directory_ini + 'Source_Phasespace_Files/' + str(self.menu_source_1.get()),
                         self.directory_mevegs)
            utils.write_to_console_log(self, "MevEGS:\t\tPhase-space file included: " + str(self.menu_source_1.get()))
            # print('Phase-space file included: ' + str(self.menu_source_1.get()))
        shutil.copy2(self.directory_file_msh, self.directory_mevegs)
        shutil.copy2(self.directory_file_egsinp, self.directory_mevegs)
        _, file_egsinp = os.path.split(self.directory_file_egsinp)
        _, file_msh = os.path.split(self.directory_file_msh)
        _, file_pegs = os.path.split(self.directory_file_pegs)
        utils.write_to_console_log(self, "MevEGS:\t\tPreparing files")
        numjobs = self.entry_njobs.get()
        os.chdir(self.directory_mevegs)
        # if os.path.isfile(self.directory_mevegs + str(self.menu_source_1.get())):
        #     print(self.directory_mevegs + str(self.menu_source_1.get()))
        if os.path.isfile(self.directory_mevegs + str(self.menu_source_1.get())):
            utils.write_to_console_log(self, "MevEGS:\t\t Phase-space source - " + str(self.menu_source_1.get()))
        for ijob in range(1, int(numjobs) + 1):
            command = 'mevegs -i ' + file_egsinp + ' -p ' + file_pegs + '  ' + file_msh + ' -b -P ' + str(
                numjobs) + ' -j ' + str(ijob) + ' -f 1'
            # command1 = 'echo %PATH%'
            job_file_name = 'mevegs_job_thread_' + str(ijob) + '.mvgs'
            with open(job_file_name, "w") as f:
                process = subprocess.Popen(['cmd', '/c', command], stdout=f, stderr=subprocess.STDOUT, bufsize=0)
        utils.write_to_console_log(self, "MevEGS:\t\tSimulation started")
        os.chdir(self.directory_ini)

    def btn_check_local_progress_clicked(self):
        _, file_egsinp = os.path.split(self.directory_file_egsinp)
        _, file_msh = os.path.split(self.directory_file_msh)
        _, file_pegs = os.path.split(self.directory_file_pegs)
        numjobs = self.entry_njobs.get()
        total_progress = [0] * int(numjobs)
        # Update progress of simulation
        self.gui.update_idletasks()
        self.frame_1.update()
        while self.bar_progress < 1:
            if self.bar_progress > 11:
                break
            if self.quit_progress_bar:
                self.quit_progress_bar = False
                self.mevegs_progress_bar.set(0)
                self.percent_label.configure(text=str('0%'))
                self.bar_progress = 0
                self.frame_1.update_idletasks()
                self.gui.update_idletasks()
                break
            if os.path.isfile(self.directory_mevegs + 'mevegs_job_thread_1.mvgs'):
                total_progress = self.parse_progress_data(numjobs, total_progress, 'mevegs_job_thread_')
                self.bar_progress = self.return_progress(total_progress, numjobs)
                time.sleep(.5)
            else:
                self.quit_progress_bar = False
                self.mevegs_progress_bar.set(0)
                self.percent_label.configure(text=str('No jobs running'))
                self.bar_progress = 0
                self.frame_1.update_idletasks()
                self.gui.update_idletasks()
                break
        else:
            utils.write_to_console_log(self, "MevEGS:\t\tSimulation Complete")

    def return_progress(self, total_progress, numjobs):
        error = 99
        for loc, item in enumerate(total_progress):
            if item == error:
                self.topframe = ctk.CTkToplevel(self.gui)  # , fg_color="firebrick4"
                self.topframe.grab_set()
                self.topframe.geometry("700x300")
                self.topframe.attributes('-topmost', True)
                self.topframe.geometry("+0+0")
                self.topframe.update()
                self.topframe.focus()
                self.topframe.title('MevEGS error')
                self.topframe.grid_columnconfigure(0, weight=1)
                self.topframe.grid_columnconfigure(1, weight=1)
                self.topframe.grid_rowconfigure(0, weight=1)
                self.topframe.grid_rowconfigure(1, weight=1)
                self.warning = ctk.CTkLabel(self.topframe, font=("Arial", 20),
                                            text='An error occurred\n\nRefer to mevegs_job_thread_' + str(
                                                loc + 1) + '.mvgs\' in\n\n' + self.directory_mevegs + '\n\nfor details')
                self.warning.grid(column=0, row=0, pady=10, padx=10, columnspan=2, sticky='nsew')
                self.exit_button = ctk.CTkButton(master=self.topframe, text='Exit', command=self.btn_exit_popup)
                self.exit_button.grid(column=0, row=1, pady=2, padx=5, columnspan=2, sticky='nesw')
                self.bar_progress = 99
                return self.bar_progress
            else:
                progress_so_far = sum(total_progress)
                self.bar_progress = float(progress_so_far / (int(numjobs) * 10))
                self.mevegs_progress_bar.set(float(self.bar_progress))
                self.percent_label.configure(text=str(float(self.bar_progress) * 100) + '%')
                self.frame_1.update()
        return self.bar_progress

    def parse_progress_data(self, numjobs, total_progress, file_name):
        cycles = 0
        for job_number in range(int(numjobs)):
            status = self.read_mevegs_job_threads(job_number, file_name)
            if 'Batch 2' in status[-1]:
                total_progress[job_number] = 2
            elif 'Batch 3' in status[-1]:
                total_progress[job_number] = 3
            elif 'Batch 4' in status[-1]:
                total_progress[job_number] = 4
            elif 'Batch 5' in status[-1]:
                total_progress[job_number] = 4.5
            elif 'Batch 6' in status[-1]:
                total_progress[job_number] = 5
            elif 'Batch 7' in status[-1]:
                total_progress[job_number] = 6
            elif 'Batch 8' in status[-1]:
                total_progress[job_number] = 7
            elif 'Batch 9' in status[-1]:
                total_progress[job_number] = 8
            elif 'Batch 10' in status[-1]:
                total_progress[job_number] = 9
            elif 'Batch 1' in status[-1]:
                total_progress[job_number] = 1
            elif 'finishSimulation(mevegs)' in status[-1]:
                total_progress[job_number] = 10
            elif '********** I\'m last job! **********\n' in status[-2]:
                total_progress[job_number] = 10
                utils.write_to_console_log(self, "MevEGS:\t\tLast job completed")
            elif 'Quiting now.\n' in status[-1]:
                total_progress[job_number] = 99
                utils.write_to_console_log(self, "MevEGS:\t\tError has occurred")
            elif 'operable program or batch file' in status[-1]:
                total_progress[job_number] = 99
                utils.write_to_console_log(self, "MevEGS:\t\tError has occurred")
            else:
                cycles += 1
                if cycles > 60:  # If job process files return something odd for 30 seconds then the bar will be set to 0
                    total_progress[job_number] = 0
                pass
        return total_progress

    def read_mevegs_job_threads(self, ijob, file_name):
        f_ = open(self.directory_mevegs + file_name + str(ijob + 1) + '.mvgs', 'r')
        last_lines = f_.readlines()[-2:]
        f_.close()
        return last_lines

    def set_project_directory_mevegs(self):
        directory_project = filedialog.askdirectory(
            title='Select new folder to save results, right click to create new folder (Windows)')
        if directory_project == "":
            return
        else:
            self.directory_project = directory_project + '/'
            self.btn_project_explore.configure(text=self.directory_project)
            self.copy_mevegs_sumulation()

    def copy_mevegs_sumulation(self):
        os.chdir(self.directory_mevegs)
        os.makedirs(self.directory_project, exist_ok=True)
        _, file_egsinp = os.path.split(self.directory_file_egsinp)
        _, file_msh = os.path.split(self.directory_file_msh)
        results_msh = file_egsinp.split('.egsinp')[0] + '_' + file_msh.split('.msh')[0] + '.results.msh'
        if os.path.isfile(self.directory_mevegs + results_msh):
            os.replace(self.directory_mevegs + results_msh, self.directory_project + results_msh)
        if os.path.isfile(self.directory_mevegs + file_egsinp.split('.egsinp')[0] + '.egslog'):
            os.replace(self.directory_mevegs + file_egsinp.split('.egsinp')[0] + '.egslog',
                       self.directory_project + file_egsinp.split('.egsinp')[0] + '_' + file_msh.split('.msh')[
                           0] + '.egslog')
        if os.path.isfile(self.directory_mevegs + file_egsinp):
            os.replace(self.directory_mevegs + file_egsinp, self.directory_project + file_egsinp)
        if os.path.isfile(self.directory_mevegs + file_msh):
            os.replace(self.directory_mevegs + file_msh, self.directory_project + file_msh)
        items_mevegs_job_logs = glob.glob(self.directory_mevegs + 'mevegs_job_thread_*.mvgs', recursive=False)
        for object_ in items_mevegs_job_logs:
            if os.path.isfile(object_):
                shutil.copy2(object_, self.directory_project)
                os.remove(object_)
        items_egsinfo = glob.glob(self.directory_mevegs + '/*.egsinfo', recursive=False)
        for object_ in items_egsinfo:
            if os.path.isfile(object_):
                os.replace(object_,
                           self.directory_project + file_egsinp.split('.egsinp')[0] + '_' + file_msh.split('.msh')[
                               0] + '.results.msh.egsinfo')
        items_egsrun = glob.glob(self.directory_mevegs + '/egsrun_*', recursive=False)
        for object_ in items_egsrun:
            if os.path.isdir(object_):
                shutil.rmtree(object_)  # junk directories
            else:
                os.remove(object_)  # junk files
        items_egsdat = glob.glob(self.directory_mevegs + '/*.egsdat', recursive=False)
        for object_ in items_egsdat:
            if os.path.isfile(object_):
                os.remove(object_)  # junk files
        if os.path.isfile(self.directory_mevegs + str(self.menu_source_1.get())):
            os.remove(self.directory_mevegs + str(self.menu_source_1.get()))
        # Move phase space files
        items_phasespace = glob.glob(self.directory_mevegs + '/*.egsphsp1', recursive=False)
        if items_phasespace:
            os.makedirs(self.directory_project + 'phase_space_files/', exist_ok=True)
            for object_ in items_phasespace:
                if os.path.isfile(object_):
                    shutil.copy2(object_, self.directory_project + 'phase_space_files/')
                    os.remove(object_)
        utils.write_to_console_log(self, 'MevEGS:\t\tFiles moved from MevEGS HOME to Project Directory\n'
                                         '\t\t\t' + self.directory_project)
        if os.path.isfile(self.directory_mevegs + str(self.menu_source_1.get())):
            os.remove(str(self.menu_source_1.get()))
        # Process phase space files  //  only matches to parallel runs with at least 2 _w files
        phase_space = False
        items_phase_space = glob.glob(self.directory_project + 'phase_space_files/' + '*_w[1-9]*egsphsp1',
                                      recursive=False)
        for i in items_phase_space:
            if re.search('_w[1-9].egsphsp1', i):
                phase_space = True
                break
        if phase_space:
            utils.process_phase_space_files(self)
        # Update GUI with directory_file path for .results.msh file
        self.directory_file_project_msh = self.directory_project + results_msh
        self.btn_results_mesh_explore.configure(text='.'.join(os.path.basename(self.directory_file_project_msh).split('.')[:-2]))
        self.directory_file_egsinp = self.directory_project + file_egsinp
        self.btn_egsinp_explore.configure(text='.'.join(os.path.basename(self.directory_file_egsinp).split('.')[:-1]))
        self.directory_file_msh = self.directory_project + file_msh
        self.btn_mesh_explore.configure(text='.'.join(os.path.basename(self.directory_file_msh).split('.')[:-1]))
        # QUICKSAVE
        os.chdir(self.directory_project)
        self.quick_save()
        utils.update_hover_tooltips(self)
        self.gui.update_idletasks()
        os.chdir(self.directory_ini)


if __name__ == "__main__":
    gui = ctk.CTk()
    gui_run = MevegsGui(gui)
    gui.attributes('-topmost', True)
    gui.update()
    gui.attributes('-topmost', False)
    gui.mainloop()
