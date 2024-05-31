#!/usr/bin/env python
# coding: utf-8

import csv
import os
import re
import shutil
import time
import gmsh
import sys
import subprocess
import glob
import wmi
import datetime
import pandas as pd
import numpy as np
import customtkinter as ctk
import matplotlib
import matplotlib.pyplot as plt
from tkinter import filedialog
from CTkToolTip import *
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk
)


# some parts reproduced/re-written from Jennifer Matthew's GUI via DMM
# print to stderr
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


# print error and exit
def abort(*args, **kwargs):
    eprint("\nin " + __file__ + ":")
    eprint(*args, **kwargs)
    eprint("Aborting\n")
    sys.exit(1)

def write_to_console_log(self, _text):
    dt = datetime.datetime.now().replace(microsecond=0)
    self.console_text_box_input.insert("0.0", text='\n' + str(dt.time()) + ' - ' + _text + '\n')
    self.console_text_box_1.insert("0.0", text='\n' + str(dt.time()) + ' - ' + _text + '\n')
    self.console_text_box_2.insert("0.0", text='\n' + str(dt.time()) + ' - ' + _text + '\n')
    self.console_text_box_3.insert("0.0", text='\n' + str(dt.time()) + ' - ' + _text + '\n')

def getElementData(viewTag):
    datatype, tags, data, _, _ = gmsh.view.getHomogeneousModelData(viewTag, step=0)
    return data


def addElementData(viewTag, tags, data):
    models = gmsh.model.list()
    len(models) == 1 or abort("More than one model loaded")
    gmsh.view.addModelData(viewTag, 0, models[0], "ElementData", tags, data)


def getViewNames(view_tags):
    return [gmsh.option.getString(f'View[{gmsh.view.getIndex(tag)}].Name')
            for tag in view_tags]


def getPhysicalGroups():
    return [x for x in gmsh.model.getPhysicalGroups()]


def getPhysicalNames():
    pairs = getPhysicalGroups()
    return [gmsh.model.getPhysicalName(x[0], x[1]) for x in pairs]


def tetsInPhysicalGroup(dim, tag, export_choice, volumes_list_i, volumes_chosen_list):
    if export_choice == 0:
        # returns tags of all entities in physical group
        # should add a check in case there's an exception like "curve doesn't exit" (JM's comment)
        entity_tags = list(gmsh.model.getEntitiesForPhysicalGroup(dim, tag))  # returns an ndarray instead of a list
    elif export_choice == 1:
        # returns tags of chosen volume entities in physical group
        entity_tags = list(volumes_list_i.get())  # must be a list
        volumes_chosen_list.append(entity_tags)
    tets = []
    nodes = []
    # since there may be multiple entity tags, must append to list
    for entity_tag in entity_tags:
        dim_, [tets_in_entity], [nodes_in_entity] = gmsh.model.mesh.getElements(dim, entity_tag)
        tets = tets + list(tets_in_entity)  # append tet numbers
        nodes = nodes + list(
            nodes_in_entity)  # append node numbers -> note that this is returned flattened len(dim(tets)*4)
    return tets, reshape_2d(nodes, 4), volumes_chosen_list


def calc_tet_centroid(tet_tags, node_tags, node_coordinates):
    num_elements = len(tet_tags)
    xmean = [0 for x in range(num_elements)]
    ymean = [0 for x in range(num_elements)]
    zmean = [0 for x in range(num_elements)]
    for i in range(num_elements):
        node1 = int(node_tags[i][0] - 1)  # -1 because gmsh indexes from 1, we index from 0
        node2 = int(node_tags[i][1] - 1)
        node3 = int(node_tags[i][2] - 1)
        node4 = int(node_tags[i][3] - 1)
        for j in [node1, node2, node3, node4]:
            node_x = node_coordinates[j][0]
            node_y = node_coordinates[j][1]
            node_z = node_coordinates[j][2]
            xmean[i] = xmean[i] + node_x / 4
            ymean[i] = ymean[i] + node_y / 4
            zmean[i] = zmean[i] + node_z / 4
    return [xmean, ymean, zmean]


def reshape_2d(data, n_cols):
    # Takes a flat array as an input, and returns it as a reshaped 2-d array with n_cols number of columns
    n_rows = int(len(data) / n_cols)
    reshaped = [[] for x in range(n_rows)]
    j = 0
    count = 0
    for i in range(len(data)):
        if count > n_cols - 1:
            count = 0
            j += 1
        reshaped[j].append(data[i])
        count += 1
    return reshaped


def save_file():  # MDE - unused, I don't think we need this
    ...


class MshResults_io:
    def __init__(self, msh_file, project_directory, egsinp_file, console_text_box_list):
        self.file = msh_file
        self.file_inp = os.path.basename(egsinp_file)  # .split('/')[-1]
        self.directory = project_directory
        self.console_text_box_input = console_text_box_list[0]
        self.console_text_box_1 = console_text_box_list[1]
        self.console_text_box_2 = console_text_box_list[2]
        self.console_text_box_3 = console_text_box_list[3]
        self.views_to_save = []
        self.groups_to_save = []
        if gmsh.isInitialized():
            pass
        else:
            gmsh.initialize()
        gmsh.open(self.file)

    def add_view_to_save(self, view: int):
        self.views_to_save.append(view + 1)  # gmsh indexes from 1

    def add_group_to_save(self, group: int):
        self.groups_to_save.append(group + 1)  # gmsh indexes from 1

    def clear_save(self):  # MDE - unused, I don't think we need this
        self.views_to_save = []
        self.groups_to_save = []

    def load_model_information(self):
        # loads in information about the gmsh model without loading in any of the view data
        # get volumes (3-dimensional)
        volumes = gmsh.model.getEntities(3)
        if len(volumes) == 0:
            abort("No volumes in the result file: " + self.file)
            write_to_console_log(self, "GMSH:\t\tNo volumes in the result file: " + self.file)

        # get physical group tags and their names
        self.group_numbers = getPhysicalGroups()
        self.group_names = getPhysicalNames()

        # Get view tags and their names
        self.view_numbers = gmsh.view.getTags()
        self.view_names = getViewNames(self.view_numbers)

        # get node data and reshape
        # maybe doesn't need to be in this function
        write_to_console_log(self, "GMSH:\t\tImporting node data")
        node_tags, node_coordinates, _ = gmsh.model.mesh.getNodes()
        self.node_coordinates = reshape_2d(node_coordinates, 3)

    def output_views_2(self, avg_beam_current, length_units, export_choice, volumes_to_include_list):
        write_to_console_log(self, "GMSH:\t\tCalculating tet centroids")
        physical_group_name_to_save = [self.group_names[i - 1] for i in self.groups_to_save]
        view_names_to_save = [self.view_names[i - 1] for i in self.views_to_save]
        tets_to_save = []
        nodes_to_save = []
        lines = []
        volumes_chosen_list = []
        for i, group in enumerate(self.groups_to_save):
            new_tets, new_nodes, vols_chosen_list = tetsInPhysicalGroup(3, group, export_choice,
                                                                        volumes_to_include_list[i], volumes_chosen_list)
            tets_to_save += new_tets
            nodes_to_save += new_nodes
        [self.xmean, self.ymean, self.zmean] = calc_tet_centroid(tets_to_save, nodes_to_save, self.node_coordinates)

        sub = []
        for i in self.views_to_save:
            data = list(getElementData(i - 1))
            sub.append(data)

        # generate lines for csv file, list of strings
        for i, tet in enumerate(tets_to_save):
            line = "{}, {}, {}, {}".format(tet, self.xmean[i], self.ymean[i], self.zmean[i])
            # add selected data fields
            write_to_console_log(self, "GMSH:\t\tGenerating lines for csv")
            for j in range(len(sub)):
                line += ", {}".format(sub[j][int(tet - 1)])
            lines.append(line + '\n')
        write_to_console_log(self, "GMSH:\t\tWriting export csv")
        # Make new directory for exports / parse values for allowed filename content
        directory_exports = self.directory + 'exports/'
        os.makedirs(directory_exports, exist_ok=True)
        result_file = 'TET_values_exported-temp.csv'
        with open(directory_exports + result_file, 'w') as writer:
            # create header string, with x,y,z followed by selected view names
            header = 'tet, x-coordinate, y-coordinate, z-coordinate'
            for name in view_names_to_save:
                header += ', {}'.format(name)

            writer.write(header + '\n')
            for line in lines:
                writer.write(line)

        # Get Scaling Factor from .egsinp file for unit export
        scaling_factor = 1
        with open(self.directory + self.file_inp, 'r') as f1:
            for line in f1:
                line = ''.join(line.split())  # removes *all* whitespace chars
                if not line.startswith('#'):  # ignore commented out lines
                    if re.search('scaling=', line, re.IGNORECASE):  # find scaling factor
                        scaling_factor = float((line.split('='))[-1])

        # Sort user selected gmsh length units for output
        if length_units == 'mm':
            length_unit_value = 10
        elif length_units == 'cm':
            length_unit_value = 1
        elif length_units == 'm':
            length_unit_value = 0.01
        else:
            write_to_console_log(self, "GMSH:\t\tError with MevEGS to GMSH unit conversion")
        # Save individual views and group exports
        vols_chosen_list_a = [x for xs in vols_chosen_list for x in xs]  # appends volumes to export file
        vols_chosen_list_b = ''.join(str(vols_chosen_list_a))
        group_list = []
        for name in view_names_to_save:
            df = pd.read_csv(directory_exports + result_file,
                             usecols=[' x-coordinate', ' y-coordinate', ' z-coordinate', ' ' + name], sep=',')
            df[' x-coordinate'] *= length_unit_value / scaling_factor
            df[' y-coordinate'] *= length_unit_value / scaling_factor
            df[' z-coordinate'] *= length_unit_value / scaling_factor
            if '[MeV]' in name:
                name = name.replace(' [MeV]', '')
            elif '[%]' in name:
                name = name.replace(' [%]', '')
            elif '[cm^3]' in name:
                name = name.replace(' [cm^3]', '')
            elif '[W/cm^3/A]' in name:  # transform PD/A to PD below
                name = name.replace(' per Amp [W/cm^3/A]', '')
            elif '[g/cm^3]' in name:
                name = 'Density'
            elif '[kg]' in name:
                name = name.replace(' [kg]', '')
            elif '[Gy/C]' in name:
                name = name.replace(' [Gy/C]', '')
            elif '[Gy]' in name:
                name = name.replace(' [Gy]', '')
            for group in physical_group_name_to_save:
                group = ''.join(i for i in group if not i.isdigit())
                group_list.append(group[:4])
            group_string = '-'.join(group_list)
            if name == 'Power Density':
                df[
                    ' Power Density per Amp [W/cm^3/A]'] *= avg_beam_current / 1000  # avg_beam_current in mA, /1000 converts to Amps
                name = 'PD_Wcm3_avg-beam_' + str(avg_beam_current) + 'mA'
            name = name.replace(" ", "_")
            name_units = '_units-' + length_units
            # if os.path.isfile(directory_exports + name + name_units + '_' + group_string + vols_chosen_list_b + '.csv'):
            #     write_to_console_log(self,
            #      "GMSH:\t\tThis data selection has been exported before\nSee Python console for instructions -->")
            #     appendage = input('Enter specific file identifier (e.g. volume numbers chosen) and Enter, or hit Enter to overwrite: ')
            #     df.to_csv(
            #         directory_exports + name + name_units + '_' + group_string + vols_chosen_list_b + appendage + '.csv',
            #         index=False, header=False)
            # else:
            df.to_csv(directory_exports + name + name_units + '_' + group_string + vols_chosen_list_b + '.csv',
                      index=False, header=False)
            group_list = []
        os.remove(directory_exports + result_file)
        write_to_console_log(self, "GMSH:\t\tFiles saved in " + directory_exports)

    def return_1D(self, view=0, x0=0, y0=0, z0=0, x1=0, y1=0, z1=0, NumPointsU=0):
        new_view = self.create_straight_line(view, x0, y0, z0, x1, y1, z1, NumPointsU)
        os.makedirs(self.directory + 'exports/', exist_ok=True)
        gmsh.view.write(tag=new_view, fileName=self.directory + 'exports/' + 'gmsh_line.csv')

    def return_2D(self, view=0, x0=0, y0=0, z0=0, x1=0, y1=0, z1=0, x2=0, y2=0, z2=0, NumPointsU=0, NumPointsV=0):
        new_view = self.create_plane(view, x0, y0, z0, x1, y1, z1, x2, y2, z2, NumPointsU, NumPointsV)
        os.makedirs(self.directory + 'exports/', exist_ok=True)
        gmsh.view.write(tag=new_view, fileName=self.directory + 'exports/' + 'gmsh_plane.csv')

    def return_3D(self, view):  # to be implemented
        ...

    def get_all_views(self):
        views = getViewNames(gmsh.view.getTags())
        return views

    def get_physical_groups(self):
        return getPhysicalGroups()

    def get_physical_names(self):
        return getPhysicalNames()

    def create_volume(self, ):
        # CutBox
        ...

    def create_plane(self, view=0, x0=0, y0=0, z0=0, x1=0, y1=0, z1=0, x2=0, y2=0, z2=0, NumPointsU=0, NumPointsV=0):
        gmsh.plugin.setNumber("CutGrid", "X0", x0)
        gmsh.plugin.setNumber("CutGrid", "Y0", y0)
        gmsh.plugin.setNumber("CutGrid", "Z0", z0)
        gmsh.plugin.setNumber("CutGrid", "X1", x1)
        gmsh.plugin.setNumber("CutGrid", "Y1", y1)
        gmsh.plugin.setNumber("CutGrid", "Z1", z1)
        gmsh.plugin.setNumber("CutGrid", "X2", x2)
        gmsh.plugin.setNumber("CutGrid", "Y2", y2)
        gmsh.plugin.setNumber("CutGrid", "Z2", z2)
        gmsh.plugin.setNumber("CutGrid", "NumPointsU", NumPointsU)
        gmsh.plugin.setNumber("CutGrid", "NumPointsV", NumPointsV)
        gmsh.plugin.setNumber("CutGrid", "ConnectPoints", 0)
        gmsh.plugin.setNumber("CutGrid", "View", view)
        view_number = gmsh.plugin.run('CutGrid')
        return view_number

    def create_straight_line(self, view=0, x0=0, y0=0, z0=0, x1=0, y1=0, z1=0, NumPointsU=0):
        gmsh.plugin.setNumber("CutGrid", "X0", x0)
        gmsh.plugin.setNumber("CutGrid", "Y0", y0)
        gmsh.plugin.setNumber("CutGrid", "Z0", z0)
        gmsh.plugin.setNumber("CutGrid", "X1", x1)
        gmsh.plugin.setNumber("CutGrid", "Y1", y1)
        gmsh.plugin.setNumber("CutGrid", "Z1", z1)
        gmsh.plugin.setNumber("CutGrid", "X2", 0)
        gmsh.plugin.setNumber("CutGrid", "Y2", 0)
        gmsh.plugin.setNumber("CutGrid", "Z2", 0)
        gmsh.plugin.setNumber("CutGrid", "NumPointsU", NumPointsU)
        gmsh.plugin.setNumber("CutGrid", "NumPointsV", 1)
        gmsh.plugin.setNumber("CutGrid", "ConnectPoints", 0)
        gmsh.plugin.setNumber("CutGrid", "View", view)
        view_number = gmsh.plugin.run('CutGrid')
        return view_number


# END OF MshResults_io() CLASS

def btn_results_mesh_explore_clicked(self):
    directory_file_project_msh = filedialog.askopenfilename(
        filetypes=[('results mesh files', ['*.results.msh', '*.Results.msh'])])
    if not directory_file_project_msh:
        directory_file_project_msh = 'Choose .results.msh File'
    self.directory_file_project_msh = directory_file_project_msh
    if self.directory_file_project_msh.startswith("Choose"):
        self.btn_results_mesh_explore.configure(text=self.directory_file_project_msh)
    else:
        self.btn_results_mesh_explore.configure(
            text='.'.join(os.path.basename(self.directory_file_project_msh).split('.')[:-2]))
    # if directory_file_project_msh == 'Choose .results.msh File':
    #     pass
    # else:
    #     load_available_gmsh_views(self)
    return self.directory_file_project_msh


# def load_available_gmsh_views(self):
#     if gmsh.isInitialized():
#         pass
#     else:
#         gmsh.initialize()
#     gmsh.logger.start()
#     gmsh.open(self.directory_file_project_msh)
#     views_tags = gmsh.view.getTags()
#     views_names = [gmsh.option.getString(f'View[{gmsh.view.getIndex(tag)}].Name') for tag in views_tags]
#     self.gmsh_views = '\n'.join(views_names)
#     gmsh_views_log = gmsh.logger.get()
#     str_gmsh_views_log = ' '.join(gmsh_views_log)
#     gmsh.logger.stop()
#     write_to_console_log(self, 'GMSH:\t\t' + str_gmsh_views_log)


def generate_new_views(self):
    self.topframe = ctk.CTkToplevel(self.gui)
    self.topframe.grab_set()
    # self.topframe.geometry("600x700")
    self.topframe.attributes('-topmost', True)
    self.topframe.geometry("+0+0")
    self.topframe.update()
    self.topframe.focus()
    self.topframe.title('Generate new views')
    self.topframe.grid_rowconfigure(11, weight=2)
    self.topframe.grid_rowconfigure(13, weight=1)

    check_var_1 = ctk.IntVar()
    check_var_2 = ctk.IntVar()
    check_var_3 = ctk.IntVar()
    check_var_4 = ctk.IntVar()
    check_var_5 = ctk.IntVar()
    check_var_6 = ctk.IntVar()
    check_var_7 = ctk.IntVar()
    check_var_8 = ctk.IntVar()
    check_var_9 = ctk.IntVar()
    check_var_10 = ctk.IntVar()
    self.checkbox_1 = ctk.CTkCheckBox(self.topframe, text="Energy fraction per particle", command=lambda: [],
                                      variable=check_var_1, onvalue="1", offvalue="0")
    self.checkbox_1.grid(column=1, row=1, pady=10, padx=10, sticky='w')
    self.checkbox_2 = ctk.CTkCheckBox(self.topframe, text="Energy deposition per particle [MeV]", command=lambda: [],
                                      variable=check_var_2, onvalue="1", offvalue="0")
    self.checkbox_2.grid(column=1, row=2, pady=10, padx=10, sticky='w')
    self.checkbox_3 = ctk.CTkCheckBox(self.topframe, text="Energy uncertainty [%]", command=lambda: [],
                                      variable=check_var_3, onvalue="1", offvalue="0")
    self.checkbox_3.grid(column=1, row=3, pady=10, padx=10, sticky='w')
    self.checkbox_4 = ctk.CTkCheckBox(self.topframe, text="Volume [cm^3]", command=lambda: [], variable=check_var_4,
                                      onvalue="1", offvalue="0")
    self.checkbox_4.grid(column=1, row=4, pady=10, padx=10, sticky='w')
    self.checkbox_5 = ctk.CTkCheckBox(self.topframe, text="Density [g/cm^3]", command=lambda: [], variable=check_var_5,
                                      onvalue="1", offvalue="0")
    self.checkbox_5.grid(column=1, row=5, pady=10, padx=10, sticky='w')
    self.checkbox_6 = ctk.CTkCheckBox(self.topframe, text="Element mass [kg]", command=lambda: [], variable=check_var_6,
                                      onvalue="1", offvalue="0")
    self.checkbox_6.grid(column=1, row=6, pady=10, padx=10, sticky='w')
    self.checkbox_7 = ctk.CTkCheckBox(self.topframe, text="Element dose [Gy]", command=lambda: [], variable=check_var_7,
                                      onvalue="1", offvalue="0")
    self.checkbox_7.grid(column=1, row=7, pady=10, padx=10, sticky='w')
    self.checkbox_8 = ctk.CTkCheckBox(self.topframe, text="Element dose per Coulomb [Gy/C]", command=lambda: [],
                                      variable=check_var_8, onvalue="1", offvalue="0")
    self.checkbox_8.grid(column=1, row=8, pady=10, padx=10, sticky='w')
    self.checkbox_9 = ctk.CTkCheckBox(self.topframe, text="Total volume energy [MeV]", command=lambda: [],
                                      variable=check_var_9, onvalue="1", offvalue="0")
    self.checkbox_9.grid(column=1, row=9, pady=10, padx=10, sticky='w')
    self.checkbox_10 = ctk.CTkCheckBox(self.topframe, text="Power Density per Amp [W/cm^3/A]", command=lambda: [],
                                       variable=check_var_10, onvalue="1", offvalue="0")
    self.checkbox_10.grid(column=1, row=10, pady=10, padx=10, sticky='w')

    current_views = self.gmsh_views
    if self.checkbox_1.cget('text') in current_views:
        self.lbl_1 = ctk.CTkLabel(self.topframe, text_color=('forest green', 'LawnGreen'), text='Complete')
        self.lbl_1.grid(column=0, row=1, pady=10, padx=(20, 0), sticky='e')
        self.checkbox_1.configure(text_color=('medium blue', 'SteelBlue1'))
    if self.checkbox_2.cget('text') in current_views:
        self.lbl_2 = ctk.CTkLabel(self.topframe, text_color=('forest green', 'LawnGreen'), text='Complete')
        self.lbl_2.grid(column=0, row=2, pady=10, padx=(20, 0), sticky='e')
        self.checkbox_2.configure(text_color=('medium blue', 'SteelBlue1'))
    if self.checkbox_3.cget('text') in current_views:
        self.lbl_3 = ctk.CTkLabel(self.topframe, text_color=('forest green', 'LawnGreen'), text='Complete')
        self.lbl_3.grid(column=0, row=3, pady=10, padx=(20, 0), sticky='e')
        self.checkbox_3.configure(text_color=('medium blue', 'SteelBlue1'))
    if self.checkbox_4.cget('text') in current_views:
        self.lbl_4 = ctk.CTkLabel(self.topframe, text_color=('forest green', 'LawnGreen'), text='Complete')
        self.lbl_4.grid(column=0, row=4, pady=10, padx=(20, 0), sticky='e')
        self.checkbox_4.configure(text_color=('medium blue', 'SteelBlue1'))
    if self.checkbox_5.cget('text') in current_views:
        self.lbl_5 = ctk.CTkLabel(self.topframe, text_color=('forest green', 'LawnGreen'), text='Complete')
        self.lbl_5.grid(column=0, row=5, pady=10, padx=(20, 0), sticky='e')
        self.checkbox_5.configure(text_color=('medium blue', 'SteelBlue1'))
    if self.checkbox_6.cget('text') in current_views:
        self.lbl_6 = ctk.CTkLabel(self.topframe, text_color=('forest green', 'LawnGreen'), text='Complete')
        self.lbl_6.grid(column=0, row=6, pady=10, padx=(20, 0), sticky='e')
        self.checkbox_6.configure(text_color=('medium blue', 'SteelBlue1'))
    if self.checkbox_7.cget('text') in current_views:
        self.lbl_7 = ctk.CTkLabel(self.topframe, text_color=('forest green', 'LawnGreen'), text='Complete')
        self.lbl_7.grid(column=0, row=7, pady=10, padx=(20, 0), sticky='e')
        self.checkbox_7.configure(text_color=('medium blue', 'SteelBlue1'))
    if self.checkbox_8.cget('text') in current_views:
        self.lbl_8 = ctk.CTkLabel(self.topframe, text_color=('forest green', 'LawnGreen'), text='Complete')
        self.lbl_8.grid(column=0, row=8, pady=10, padx=(20, 0), sticky='e')
        self.checkbox_8.configure(text_color=('medium blue', 'SteelBlue1'))
    if self.checkbox_9.cget('text') in current_views:
        self.lbl_9 = ctk.CTkLabel(self.topframe, text_color=('forest green', 'LawnGreen'), text='Complete')
        self.lbl_9.grid(column=0, row=9, pady=10, padx=(20, 0), sticky='e')
        self.checkbox_9.configure(text_color=('medium blue', 'SteelBlue1'))
    if self.checkbox_10.cget('text') in current_views:
        self.lbl_10 = ctk.CTkLabel(self.topframe, text_color=('forest green', 'LawnGreen'), text='Complete')
        self.lbl_10.grid(column=0, row=10, pady=10, padx=(20, 0), sticky='e')
        self.checkbox_10.configure(text_color=('medium blue', 'SteelBlue1'))

    btn_list = [self.checkbox_1, self.checkbox_2, self.checkbox_3, self.checkbox_4, self.checkbox_5, self.checkbox_6,
                self.checkbox_7, self.checkbox_8, self.checkbox_9, self.checkbox_10]
    chk_list = [check_var_1, check_var_2, check_var_3, check_var_4, check_var_5, check_var_6, check_var_7, check_var_8,
                check_var_9, check_var_10]

    self.add_button = ctk.CTkButton(self.topframe, text='Create selected view(s)', height=40,
                                    command=lambda: [btn_generate_new_views(self, btn_list, chk_list), self.btn_exit_popup()])
    self.add_button.grid(column=1, row=12, pady=10, padx=10, sticky='nesw')
    self.exit_button = ctk.CTkButton(master=self.topframe, text='Close', command=lambda: [self.btn_exit_popup()])
    self.exit_button.grid(column=1, row=13, pady=10, padx=10, sticky='nesw')
    return btn_list, chk_list


def btn_generate_new_views(self, btn_list, chk_list):
    view_list = []
    if gmsh.isInitialized():
        pass
    else:
        gmsh.initialize()
    gmsh.open(self.directory_file_project_msh)
    for count, var in enumerate(chk_list):
        if var.get():
            view_list.append(btn_list[count].cget('text'))
    # Call generating functions here
    joules_per_mev = 1.602e-13
    electrons_per_coulomb = 6.24150e18
    masses = []
    doses = []
    energies = []
    elements = []
    volumes = []
    for view in view_list:
        if view in self.gmsh_views:
            pass
        else:
            if view == 'Element mass [kg]':
                elements, volumes = get_scalar_data(3)  # Volume [cm^3] = 3
                _, densities = get_scalar_data(4)  # Density [g/cm^3] = 4
                masses = [vol * dens / 1000.0 for (vol, dens) in zip(volumes, densities)]  # Element masses in kg
                append_to_file("Element mass [kg]", self.directory_file_project_msh, elements, masses)
            if view == 'Element dose [Gy]':
                elements, energies = get_scalar_data(1)  # Energy deposition per particle [MeV] = 1
                if not masses:
                    elements, volumes = get_scalar_data(3)  # Volume [cm^3] = 3
                    _, densities = get_scalar_data(4)  # Density [g/cm^3] = 4
                    masses = [vol * dens / 1000.0 for (vol, dens) in zip(volumes, densities)]  # Element masses in kg
                else:
                    pass
                doses = [energy * joules_per_mev / mass for (energy, mass) in
                         zip(energies, masses)]  # Element doses in gray [Gy]
                append_to_file("Element dose [Gy]", self.directory_file_project_msh, elements, doses)
            if view == 'Element dose per Coulomb [Gy/C]':
                if not doses:
                    elements, energies = get_scalar_data(1)
                if not masses:
                    elements, volumes = get_scalar_data(3)  # Volume [cm^3] = 3
                    _, densities = get_scalar_data(4)  # Density [g/cm^3] = 4
                    masses = [vol * dens / 1000.0 for (vol, dens) in zip(volumes, densities)]
                doses = [energy * joules_per_mev / mass for (energy, mass) in zip(energies, masses)]
                edpc = [dose * electrons_per_coulomb for dose in doses]
                append_to_file("Element dose per Coulomb [Gy/C]", self.directory_file_project_msh, elements, edpc)
            if view == 'Total volume energy [MeV]':
                append_to_file("Total volume energy [MeV]", self.directory_file_project_msh,
                               *get_volume_totals(1))  # Energy deposition per particle [MeV] = 1
            if view == 'Power Density per Amp [W/cm^3/A]':
                if not doses:
                    elements, energies = get_scalar_data(1)
                if not masses:
                    elements, volumes = get_scalar_data(3)  # Volume [cm^3] = 3
                    _, densities = get_scalar_data(4)  # Density [g/cm^3] = 4
                    masses = [vol * dens / 1000.0 for (vol, dens) in zip(volumes, densities)]
                doses = [energy * joules_per_mev / mass for (energy, mass) in zip(energies, masses)]
                edpc = [dose * electrons_per_coulomb for dose in doses]
                j_p_c = [edpc * mass for (edpc, mass) in zip(edpc, masses)]
                if not volumes:
                    elements, volumes = get_scalar_data(3)  # Volume [cm^3] = 3
                power = [j_p_c / vol for (j_p_c, vol) in zip(j_p_c, volumes)]
                append_to_file("Power Density per Amp [W/cm^3/A]", self.directory_file_project_msh, elements, power)
    gmsh.finalize()
    if os.path.isfile(self.directory_file_project_msh) and os.path.isdir(self.directory_project) and os.path.isfile(
            self.directory_file_egsinp):
        load_gmsh_data_for_figures(self, self.directory_file_project_msh, self.directory_project,
                                         self.directory_file_egsinp)


def get_scalar_data(viewTag):  # viewTag is integer
    _, tags, data, _, _ = gmsh.view.getModelData(viewTag, step=0)
    # returns a list of lists, extract here
    data = [x for [x] in data]
    return tags, data


def append_to_file(title, filename, elts, data):
    view_tag = gmsh.view.add(title)
    add_scalar_data(view_tag, elts, data)
    append_view(view_tag, filename)


def add_scalar_data(viewTag, tags, data):
    models = gmsh.model.list()
    len(models) == 1 or abort("More than one model loaded")
    gmsh.view.addModelData(viewTag, 0, models[0], "ElementData", tags, [[dat] for dat in data])


def append_view(viewTag, filename):
    # don't save duplicate mesh data
    gmsh.option.setNumber("PostProcessing.SaveMesh", 0)
    gmsh.view.write(viewTag, filename, append=True)


# sum a quantity over all the volume elements for a given view
def get_volume_totals(viewTag):
    # get all the data for a view
    data_map = dict(zip(*get_scalar_data(viewTag)))
    volumes = gmsh.model.getEntities(3)
    len(volumes) > 0 or abort("No volumes in data file")
    # build list of all elements
    elts = []
    volume_sum = []
    for dim, volume in volumes:
        _, vol_elts, _ = gmsh.model.mesh.getElements(dim, volume)
        len(vol_elts) == 1 or abort("Mixed element types data file")
        [vol_elts] = vol_elts  # take first entry of vector of vectors
        elts.extend(vol_elts)
        vol_total = sum([data_map.get(elt, 0.0) for elt in vol_elts])
        volume_sum.extend([vol_total for _ in vol_elts])
    return elts, volume_sum


# def btn_display_views_clicked(self):
# ...
#     # if self.gmsh_views == '':
#     #     load_available_gmsh_views(self)
#     # gmsh.initialize()
#     # gmsh.open(self.directory_file_project_msh)
#     #
#     # self.topframe = ctk.CTkToplevel(self.gui)
#     # self.topframe.grab_set()
#     # # self.topframe.geometry("600x700")
#     # self.topframe.attributes('-topmost', True)
#     # self.topframe.geometry("+0+0")
#     # self.topframe.update()
#     # self.topframe.focus()
#     # self.topframe.title('Show checked views')
#     # self.topframe.grid_rowconfigure(11, weight=2)
#     # self.topframe.grid_rowconfigure(13, weight=1)
#     #
#     # check_var_1 = ctk.IntVar()
#     # check_var_2 = ctk.IntVar()
#     # check_var_3 = ctk.IntVar()
#     # check_var_4 = ctk.IntVar()
#     # check_var_5 = ctk.IntVar()
#     # check_var_6 = ctk.IntVar()
#     # check_var_7 = ctk.IntVar()
#     # check_var_8 = ctk.IntVar()
#     # check_var_9 = ctk.IntVar()
#     # check_var_10 = ctk.IntVar()
#     # self.checkbox_1 = ctk.CTkCheckBox(self.topframe, text="Energy fraction per particle", command=lambda: [],
#     #                                   variable=check_var_1, onvalue="1", offvalue="0")
#     # self.checkbox_1.grid(column=1, row=1, pady=10, padx=10, sticky='w')
#     # self.checkbox_2 = ctk.CTkCheckBox(self.topframe, text="Energy deposition per particle [MeV]", command=lambda: [],
#     #                                   variable=check_var_2, onvalue="1", offvalue="0")
#     # self.checkbox_2.grid(column=1, row=2, pady=10, padx=10, sticky='w')
#     # self.checkbox_3 = ctk.CTkCheckBox(self.topframe, text="Energy uncertainty [%]", command=lambda: [],
#     #                                   variable=check_var_3, onvalue="1", offvalue="0")
#     # self.checkbox_3.grid(column=1, row=3, pady=10, padx=10, sticky='w')
#     # self.checkbox_4 = ctk.CTkCheckBox(self.topframe, text="Volume [cm^3]", command=lambda: [], variable=check_var_4,
#     #                                   onvalue="1", offvalue="0")
#     # self.checkbox_4.grid(column=1, row=4, pady=10, padx=10, sticky='w')
#     # self.checkbox_5 = ctk.CTkCheckBox(self.topframe, text="Density [g/cm^3]", command=lambda: [], variable=check_var_5,
#     #                                   onvalue="1", offvalue="0")
#     # self.checkbox_5.grid(column=1, row=5, pady=10, padx=10, sticky='w')
#     # self.checkbox_6 = ctk.CTkCheckBox(self.topframe, text="Element mass [kg]", command=lambda: [], variable=check_var_6,
#     #                                   onvalue="1", offvalue="0")
#     # self.checkbox_6.grid(column=1, row=6, pady=10, padx=10, sticky='w')
#     # self.checkbox_7 = ctk.CTkCheckBox(self.topframe, text="Element dose [Gy]", command=lambda: [], variable=check_var_7,
#     #                                   onvalue="1", offvalue="0")
#     # self.checkbox_7.grid(column=1, row=7, pady=10, padx=10, sticky='w')
#     # self.checkbox_8 = ctk.CTkCheckBox(self.topframe, text="Element dose per Coulomb [Gy/C]", command=lambda: [],
#     #                                   variable=check_var_8, onvalue="1", offvalue="0")
#     # self.checkbox_8.grid(column=1, row=8, pady=10, padx=10, sticky='w')
#     # self.checkbox_9 = ctk.CTkCheckBox(self.topframe, text="Total volume energy [MeV]", command=lambda: [],
#     #                                   variable=check_var_9, onvalue="1", offvalue="0")
#     # self.checkbox_9.grid(column=1, row=9, pady=10, padx=10, sticky='w')
#     # self.checkbox_10 = ctk.CTkCheckBox(self.topframe, text="Power Density per Amp [W/cm^3/A]", command=lambda: [],
#     #                                    variable=check_var_10, onvalue="1", offvalue="0")
#     # self.checkbox_10.grid(column=1, row=10, pady=10, padx=10, sticky='w')
#     #
#     # current_views = self.gmsh_views
#     # if self.checkbox_1.cget('text') in current_views:
#     #     self.lbl_1 = ctk.CTkLabel(self.topframe, text_color=''LawnGreen', text='Ready')
#     #     self.lbl_1.grid(column=0, row=1, pady=10, padx=(20, 0), sticky='e')
#     #     self.checkbox_1.configure(text_color='SteelBlue1')
#     # if self.checkbox_2.cget('text') in current_views:
#     #     self.lbl_2 = ctk.CTkLabel(self.topframe, text_color=''LawnGreen', text='Ready')
#     #     self.lbl_2.grid(column=0, row=2, pady=10, padx=(20, 0), sticky='e')
#     #     self.checkbox_2.configure(text_color='SteelBlue1')
#     # if self.checkbox_3.cget('text') in current_views:
#     #     self.lbl_3 = ctk.CTkLabel(self.topframe, text_color=''LawnGreen', text='Ready')
#     #     self.lbl_3.grid(column=0, row=3, pady=10, padx=(20, 0), sticky='e')
#     #     self.checkbox_3.configure(text_color='SteelBlue1')
#     # if self.checkbox_4.cget('text') in current_views:
#     #     self.lbl_4 = ctk.CTkLabel(self.topframe, text_color=''LawnGreen', text='Ready')
#     #     self.lbl_4.grid(column=0, row=4, pady=10, padx=(20, 0), sticky='e')
#     #     self.checkbox_4.configure(text_color='SteelBlue1')
#     # if self.checkbox_5.cget('text') in current_views:
#     #     self.lbl_5 = ctk.CTkLabel(self.topframe, text_color=''LawnGreen', text='Ready')
#     #     self.lbl_5.grid(column=0, row=5, pady=10, padx=(20, 0), sticky='e')
#     #     self.checkbox_5.configure(text_color='SteelBlue1')
#     # if self.checkbox_6.cget('text') in current_views:
#     #     self.lbl_6 = ctk.CTkLabel(self.topframe, text_color=''LawnGreen', text='Ready')
#     #     self.lbl_6.grid(column=0, row=6, pady=10, padx=(20, 0), sticky='e')
#     #     self.checkbox_6.configure(text_color='SteelBlue1')
#     # if self.checkbox_7.cget('text') in current_views:
#     #     self.lbl_7 = ctk.CTkLabel(self.topframe, text_color=''LawnGreen', text='Ready')
#     #     self.lbl_7.grid(column=0, row=7, pady=10, padx=(20, 0), sticky='e')
#     #     self.checkbox_7.configure(text_color='SteelBlue1')
#     # if self.checkbox_8.cget('text') in current_views:
#     #     self.lbl_8 = ctk.CTkLabel(self.topframe, text_color=''LawnGreen', text='Ready')
#     #     self.lbl_8.grid(column=0, row=8, pady=10, padx=(20, 0), sticky='e')
#     #     self.checkbox_8.configure(text_color='SteelBlue1')
#     # if self.checkbox_9.cget('text') in current_views:
#     #     self.lbl_9 = ctk.CTkLabel(self.topframe, text_color=''LawnGreen', text='Ready')
#     #     self.lbl_9.grid(column=0, row=9, pady=10, padx=(20, 0), sticky='e')
#     #     self.checkbox_9.configure(text_color='SteelBlue1')
#     # if self.checkbox_10.cget('text') in current_views:
#     #     self.lbl_10 = ctk.CTkLabel(self.topframe, text_color=''LawnGreen', text='Ready')
#     #     self.lbl_10.grid(column=0, row=10, pady=10, padx=(20, 0), sticky='e')
#     #     self.checkbox_10.configure(text_color='SteelBlue1')
#     #
#     # btn_list = [self.checkbox_1, self.checkbox_2, self.checkbox_3, self.checkbox_4, self.checkbox_5, self.checkbox_6,
#     #             self.checkbox_7, self.checkbox_8, self.checkbox_9, self.checkbox_10]
#     # chk_list = [check_var_1, check_var_2, check_var_3, check_var_4, check_var_5, check_var_6, check_var_7, check_var_8,
#     #             check_var_9, check_var_10]
#     #
#     # self.add_button = ctk.CTkButton(self.topframe, text='Show checked view(s) in GMSH', height=40,
#     #                                 command=lambda: [btn_show_views_clicked(self, btn_list, chk_list), self.btn_exit_popup()])
#     # self.add_button.grid(column=1, row=11, pady=10, padx=10, sticky='nesw')
#     # self.exit_button = ctk.CTkButton(master=self.topframe, text='Close',
#     #                                  command=lambda: [self.btn_exit_popup()])
#     # self.exit_button.grid(column=1, row=12, pady=10, padx=10, sticky='nesw')


# def btn_show_views_clicked(self, btn_list, chk_list):
#     ...
#     # # gmsh.initialize()
#     # views_list = []
#     # for count, var in enumerate(chk_list):
#     #     if var.get():
#     #         views_list.append(btn_list[count].cget('text'))
#     #         print(count, btn_list[count].cget('text'), var.get())
#     # # Call generating functions here
#     # f1 = open(self.directory_file_project_msh, 'r')
#     # f2 = open(self.directory_project+'current_views.results.msh', 'w')
#     # for line in f1:
#     #     f2.write(line)
#     #     if re.search('EndElements', line):
#     #         return
#     # f1.close()
#     # f2.close()
#     # print(views_list)
#     # for view in views_list:
#     #     if view == 'Energy fraction per particle':
#     #         with open(self.directory_file_project_msh, 'r') as f1, open(self.directory_project + 'current_views.results.msh', 'a') as f2:
#     #             for line in f1:
#     #                 print(line)
#     #                 if re.search('Energy fraction per particle', line):
#     #                     f2.write('$ElementData\n1\n\"Energy fraction per particle\"\n')
#     #                 elif re.search('EndElementData', line):
#     #                     f2.write('$EndElementData\n')
#     #                     return
#     #                 else:
#     #                     f2.write(line)
#     #     elif view == 'Energy deposition per particle [MeV]':
#     #         writing = False
#     #         with open(self.directory_file_project_msh, 'r') as f1, open(self.directory_project + 'current_views.results.msh', 'a') as f2:
#     #             for line in f1:
#     #                 if re.search('Energy deposition per particle [MeV]', line):
#     #                     f2.write('$ElementData\n1\n')
#     #                     writing = True
#     #                 elif re.search('EndElementData', line):
#     #                     f2.write('$EndElementData\n')
#     #                     writing = False
#     #
#     #                 if writing:
#     #                     f2.write(line)
#     #     elif view == 'Energy uncertainty [%]':
#     #         writing = False
#     #         with open(self.directory_file_project_msh, 'r') as f1, open(self.directory_project + 'current_views.results.msh', 'a') as f2:
#     #             for line in f1:
#     #                 if re.search('Energy uncertainty [%]', line):
#     #                     f2.write('$ElementData\n1\n')
#     #                     writing = True
#     #                 elif re.search('EndElementData', line):
#     #                     f2.write('$EndElementData\n')
#     #                     writing = False
#     #
#     #                 if writing:
#     #                     f2.write(line)
#     #     elif view == 'Volume [cm^3]':
#     #         writing = False
#     #         with open(self.directory_file_project_msh, 'r') as f1, open(self.directory_project + 'current_views.results.msh', 'a') as f2:
#     #             for line in f1:
#     #                 if re.search('Volume [cm^3]', line):
#     #                     f2.write('$ElementData\n1\n')
#     #                     writing = True
#     #                 elif re.search('EndElementData', line):
#     #                     f2.write('$EndElementData\n')
#     #                     writing = False
#     #
#     #                 if writing:
#     #                     f2.write(line)
#     #     elif view == 'Density [g/cm^3]':
#     #         writing = False
#     #         with open(self.directory_file_project_msh, 'r') as f1, open(self.directory_project + 'current_views.results.msh', 'a') as f2:
#     #             for line in f1:
#     #                 if re.search('Density [g/cm^3]', line):
#     #                     f2.write('$ElementData\n1\n')
#     #                     writing = True
#     #                 elif re.search('EndElementData', line):
#     #                     f2.write('$EndElementData\n')
#     #                     writing = False
#     #
#     #                 if writing:
#     #                     f2.write(line)
#     #     elif view == ['Power Density per Amp [W/cm^3/A]']:
#     #         ...
#
#     # gmsh.fltk.run()
#     gmsh.finalize(


def btn_choose_export_data_clicked(self):
    self.topframe = ctk.CTkToplevel(self.gui)
    self.topframe.grab_set()
    # self.topframe.geometry("600x700")
    self.topframe.attributes('-topmost', True)
    self.topframe.geometry("+0+0")
    self.topframe.update()
    self.topframe.focus()
    self.topframe.title('Export views - groups - volumes')
    self.topframe.grid_rowconfigure(11, weight=2)
    self.topframe.grid_rowconfigure(13, weight=1)
    # COLUMN 1 - Views
    if gmsh.isInitialized():
        pass
    else:
        gmsh.initialize()
    gmsh.open(self.directory_file_project_msh)
    views_list = []
    checkvar_views_list = []
    views_names = getViewNames(gmsh.view.getTags())
    for views_rows in range(len(views_names)):
        checkvar_views_list.append(ctk.IntVar())
        views_list.append(
            ctk.CTkCheckBox(self.topframe, text_color=('medium blue', 'SteelBlue1'), text=views_names[views_rows],
                            variable=checkvar_views_list[views_rows], onvalue="1", offvalue="0"))
        views_list[views_rows].grid(column=1, row=views_rows + 1, pady=10, padx=(20, 10), sticky='w')
    self.lbl_view = ctk.CTkLabel(self.topframe, text_color=('grey1', 'white'), text='VIEWS')
    self.lbl_view.grid(column=1, row=0, pady=10, padx=10)
    self.lbl_group = ctk.CTkLabel(self.topframe, text_color=('grey1', 'white'), text='MATERIALS')
    self.lbl_group.grid(column=2, row=0, pady=10, padx=10)
    self.lbl_volume = ctk.CTkLabel(self.topframe, text_color=('grey1', 'white'), text='VOLUMES')
    self.lbl_volume.grid(column=3, row=0, pady=10, padx=10)
    # if 'Power Density per Amp [W/cm^3/A]' in views_names:
    avg_beam_current = ctk.StringVar()
    self.lbl_milliamps = ctk.CTkLabel(self.topframe, text='Avg Beam\nCurrent (mA)')
    self.lbl_milliamps.grid(column=0, row=views_rows + 2, pady=(0, 10), padx=10, sticky='e')
    self.entry_milliamps = ctk.CTkEntry(self.topframe, width=200, textvariable=avg_beam_current, justify='center')
    self.entry_milliamps.grid(column=1, row=views_rows + 2, pady=(0, 10), padx=10, sticky='w')
    avg_beam_current.set('1')

    self.lbl_lengths = ctk.CTkLabel(self.topframe, text='Tet centroid\nlength units')
    self.lbl_lengths.grid(column=0, row=views_rows + 3, pady=(0, 10), padx=10, sticky='e')
    self.btn_lengths = ctk.CTkSegmentedButton(self.topframe, width=200, values=['mm', 'cm', 'm'],
                                              dynamic_resizing=False)
    self.btn_lengths.grid(column=1, row=views_rows + 3, pady=(0, 10), padx=10, sticky='w')
    self.btn_lengths.set('mm')

    # COLUMN 2 - Groups
    physical_groups_list = []
    checkvar_groups_list = []
    phys_names = getPhysicalNames()
    for group_rows in range(len(getPhysicalNames())):
        checkvar_groups_list.append(ctk.IntVar())
        physical_groups_list.append(
            ctk.CTkCheckBox(self.topframe, text_color=('medium blue', 'SteelBlue1'), text=phys_names[group_rows],
                            variable=checkvar_groups_list[group_rows], onvalue="1", offvalue="0"))
        physical_groups_list[group_rows].grid(column=2, row=group_rows + 1, pady=10, padx=(20, 10), sticky='w')
    # COLUMN 3 - Volumes
    volume_list = []
    for i, tag in enumerate(phys_names):
        if i < 5:
            vol_entity = gmsh.model.getEntitiesForPhysicalGroup(3, i + 1)  # gmsh counts from 1
            self.vol_scroll_frame = VolumeCheckboxFrame(self.topframe, phys_names[i], vol_entity)
            volume_list.append(self.vol_scroll_frame)
            self.vol_scroll_frame.grid(column=3 + i, row=1, pady=(5, 0), padx=(5, 5), sticky='w', rowspan=5)
        elif 10 > i > 4:
            vol_entity = gmsh.model.getEntitiesForPhysicalGroup(3, i + 1)  # gmsh counts from 1
            self.vol_scroll_frame = VolumeCheckboxFrame(self.topframe, phys_names[i], vol_entity)
            volume_list.append(self.vol_scroll_frame)
            self.vol_scroll_frame.grid(column=-2 + i, row=6, pady=(5, 0), padx=(5, 5), sticky='w', rowspan=5)
        else:
            vol_entity = gmsh.model.getEntitiesForPhysicalGroup(3, i + 1)  # gmsh counts from 1
            self.vol_scroll_frame = VolumeCheckboxFrame(self.topframe, phys_names[i], vol_entity)
            volume_list.append(self.vol_scroll_frame)
            self.vol_scroll_frame.grid(column=-7 + i, row=11, pady=(5, 0), padx=(5, 5), sticky='w', rowspan=5)
    gmsh.finalize()  # This may need to be enabled, and gmsh.initialize enabled again in check_ functions

    labels_list = []
    current_views = self.gmsh_views
    for i, checkbox in enumerate(views_list):
        if checkbox.cget('text') in current_views:
            labels_list.append(ctk.CTkLabel(self.topframe, text_color=('forest green', 'LawnGreen'), text='Ready'))
            labels_list[i].grid(column=0, row=i + 1, pady=10, padx=(20, 0), sticky='e')
        elif checkbox.cget('text') not in current_views:
            labels_list.append(ctk.CTkLabel(self.topframe, text_color='white', text='Generate'))
            labels_list[i].grid(column=0, row=i + 1, pady=10, padx=(20, 0), sticky='e')

    # check to see if there are more groups than views for gui display continuity
    if group_rows < 12:
        group_rows = 12
    # BUTTONS
    self.add_view_button = ctk.CTkButton(self.topframe, text='Export selected view(s) of selected material(s)',
                                         height=40, command=lambda: [
            check_btn_export_view(self, checkvar_views_list, checkvar_groups_list, volume_list,
                                  float(self.entry_milliamps.get()), str(self.btn_lengths.get())), self.data_list_populate()])
    self.add_view_button.grid(column=1, row=group_rows + 1, pady=10, padx=(10, 5), sticky='nesw', columnspan=2)
    self.add_group_button = ctk.CTkButton(self.topframe, text='Export selected view(s) of material(s) and volume(s)',
                                          height=40, command=lambda: [
            check_btn_export_group(self, checkvar_views_list, checkvar_groups_list, volume_list,
                                   float(self.entry_milliamps.get()), str(self.btn_lengths.get())), self.data_list_populate()])
    self.add_group_button.grid(column=3, row=group_rows + 1, pady=10, padx=(5, 10), sticky='nesw', columnspan=5)
    self.exit_button = ctk.CTkButton(master=self.topframe, text='Close',
                                     command=lambda: [self.btn_exit_popup(), check_gmsh_initialized(self)])
    self.exit_button.grid(column=1, row=group_rows + 2, pady=(10, 25), padx=10, sticky='nesw', columnspan=10)

def check_gmsh_initialized(self):
    if gmsh.isInitialized():
        gmsh.finalize()
    else:
        pass

class VolumeCheckboxFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, title, values):
        super().__init__(master, label_text=title[:15])
        self.grid_columnconfigure(0, weight=1)
        self.values = values
        self.checkboxes = []
        self.configure(width=105, height=200, label_text_color=('medium blue', 'SteelBlue1'))
        self.selectall = ctk.CTkCheckBox(self, text='Select All',
                                         command=lambda: [self.select_all(), self.deselectall.deselect(),
                                                          self.selectall.deselect()])
        self.selectall.grid(column=0, row=0, padx=5, pady=(5, 0), sticky="w")
        self.deselectall = ctk.CTkCheckBox(self, text='Deselect All',
                                           command=lambda: [self.unselect_all(), self.selectall.deselect(),
                                                            self.deselectall.deselect()])
        self.deselectall.grid(column=0, row=1, padx=5, pady=(5, 0), sticky="w")
        for i, value in enumerate(self.values):
            checkbox = ctk.CTkCheckBox(self, text=value)
            checkbox.grid(row=i + 2, column=0, padx=5, pady=(5, 0), sticky="w")
            self.checkboxes.append(checkbox)

    def select_all(self):
        for checkbox in self.checkboxes:
            checkbox.select()

    def unselect_all(self):
        for checkbox in self.checkboxes:
            checkbox.deselect()

    def get(self):
        checked_checkboxes = []
        for checkbox in self.checkboxes:
            if checkbox.get() == 1:
                checked_checkboxes.append(checkbox.cget("text"))
        return checked_checkboxes


class ViewsCheckboxFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, title, values):
        super().__init__(master, label_text=title[:15])
        self.grid_columnconfigure(0, weight=1)
        self.values = values
        self.checkboxes = []
        for i, value in enumerate(self.values):
            checkbox = ctk.CTkCheckBox(self, text=value)
            checkbox.grid(row=i, column=0, padx=5, pady=(5, 0), sticky="w")
            self.checkboxes.append(checkbox)

    def get(self):
        checked_checkboxes = []
        for checkbox in self.checkboxes:
            if checkbox.get() == 1:
                checked_checkboxes.append(checkbox.cget("text"))
        return checked_checkboxes


def check_btn_export_view(self, checkvar_views_list, checkvar_groups_list, volume_list, avg_beam_mA, length_units):
    export_choice = 0
    if gmsh.isInitialized():
        pass
    else:
        gmsh.initialize()
    msh_data = MshResults_io(self.directory_file_project_msh, self.directory_project, self.directory_file_egsinp,
                             [self.console_text_box_input, self.console_text_box_1, self.console_text_box_2, self.console_text_box_3])
    msh_data.load_model_information()
    groups = msh_data.get_physical_groups()
    views = msh_data.get_all_views()
    for i, group in enumerate(groups):
        if checkvar_groups_list[i].get():
            msh_data.add_group_to_save(i)
    for i, view in enumerate(views):
        if checkvar_views_list[i].get():
            msh_data.add_view_to_save(i)
    msh_data.output_views_2(avg_beam_mA, length_units, export_choice, volume_list)
    gmsh.finalize()


def check_btn_export_group(self, checkvar_views_list, checkvar_groups_list, volume_list, avg_beam_mA,
                           length_units):  # change volume list to only include groups... see i
    export_choice = 1
    if gmsh.isInitialized():
        pass
    else:
        gmsh.initialize()
    msh_data = MshResults_io(self.directory_file_project_msh, self.directory_project, self.directory_file_egsinp,
                             [self.console_text_box_input, self.console_text_box_1, self.console_text_box_2, self.console_text_box_3])
    msh_data.load_model_information()
    groups = msh_data.get_physical_groups()
    views = msh_data.get_all_views()
    volumes_to_include_list = []
    for i, group in enumerate(groups):
        if checkvar_groups_list[i].get():
            msh_data.add_group_to_save(i)
            volumes_to_include_list.append(volume_list[i])
    for i, view in enumerate(views):
        if checkvar_views_list[i].get():
            msh_data.add_view_to_save(i)
    msh_data.output_views_2(avg_beam_mA, length_units, export_choice, volumes_to_include_list)
    gmsh.finalize()


def process_phase_space_files(self):
    os.makedirs(self.directory_project + 'phase_space_files/', exist_ok=True)
    directory_project = self.directory_project + 'phase_space_files/'
    phsp_filenames = []
    for fname in os.listdir(directory_project):
        if '_w1.egsphsp1' in fname:
            phsp_filenames.append(os.path.basename(fname).split('_w1.egsphsp1')[0])

    items_phase_space = glob.glob(directory_project + '*_w[1-9].egsphsp1', recursive=False)
    items_phase_space_2 = glob.glob(directory_project + '*_w[1-9][0-9].egsphsp1', recursive=False)
    items_phase_space = items_phase_space + items_phase_space_2
    # determining number of _w files, w_max
    x = []
    for i in items_phase_space:
        if re.search('_w[1-9][0-9].egsphsp1', i):
            x.append(int(os.path.basename(i).split('.egsphsp1')[0].split('_w')[-1]))
    if not x:
        for i in items_phase_space:
            if re.search('_w[1-9].egsphsp1', i):
                x.append(int(os.path.basename(i).split('.egsphsp1')[0].split('_w')[-1]))
    w_max = np.max(x)

    os.chdir(directory_project)
    progress_phase = []
    # combine _w files
    for j in range(len(phsp_filenames)):
        command = 'addphsp ' + phsp_filenames[j] + ' ' + phsp_filenames[j] + ' ' + str(w_max) + ' 1 1 0'
        error_file_name = phsp_filenames[j] + '_console_log.mvgs'
        with open(error_file_name, 'w') as f:  # directory has been changed to local file, no full path needed here
            progress_phase.append(
                subprocess.Popen(['cmd', '/c', command], stdout=f, stderr=subprocess.STDOUT, bufsize=0))
    time.sleep(5)
    for i in range(len(phsp_filenames)):
        while progress_phase[i].poll() is None:
            write_to_console_log(self, "MevEGS:\t\tWorking on combining phase-space files...")
            time.sleep(15)
    else:
        write_to_console_log(self, "MevEGS:\t\tCombining jobs complete")
    time.sleep(1)
    write_to_console_log(self, "MevEGS:\t\tPreparing human readable phase space files...")

    # Convert to human-readable, hardcoded beamdp option 11
    # move beamdp.bat to working dir
    shutil.copy2(self.directory_post_pro + 'beamdp.bat', directory_project)
    progress_read = []
    for j in range(len(phsp_filenames)):
        command = 'beamdp.bat ' + phsp_filenames[j] + '.egsphsp1'
        progress_read.append(subprocess.Popen(['cmd', '/c', command]))
    time.sleep(5)
    for i in range(len(phsp_filenames)):
        while progress_read[i].poll() is None:
            write_to_console_log(self, "MevEGS:\t\tPreparing human readable phase space files " + str(i + 1) + '...')
            time.sleep(10)
    write_to_console_log(self, "MevEGS:\t\tReadable particle phase space files saved in: " + directory_project)
    # delete beamdp.bat
    os.remove(directory_project + 'beamdp.bat')
    items_egsphsp1 = glob.glob(directory_project + '*.egsphsp1', recursive=False)
    for object_ in items_egsphsp1:
        if os.path.isfile(object_):
            os.remove(object_)  # junk files
    os.chdir(self.directory_mevegs)  # back to mevegs home


def btn_kill_mevegs_clicked(self):
    # os.system("taskkill /f /im  mevegs.exe")
    command = "taskkill /f /im mevegs.exe"
    job_file_name = 'mevegs_jobkill_console_output.mvgs'
    with open(job_file_name, "w") as f:
        process = subprocess.Popen(['cmd', '/c', command], stdout=f, stderr=subprocess.STDOUT, bufsize=0)
    while process.poll() is None:
        time.sleep(1)
    with open(job_file_name, "r") as f:
        contents = f.read()
        write_to_console_log(self, "MevEGS:\t\t" + contents)
    os.remove(job_file_name)
    self.quit_progress_bar = True


def are_you_sure_kill(self):
    self.topframe = ctk.CTkToplevel(self.gui)  # , fg_color="indian red")
    self.topframe.grab_set()
    self.topframe.geometry("700x300")
    self.topframe.attributes('-topmost', True)
    self.topframe.update()
    self.topframe.focus()
    self.topframe.title('Confirm')
    self.topframe.grid_columnconfigure(0, weight=1)
    self.topframe.grid_columnconfigure(1, weight=1)
    self.topframe.grid_rowconfigure(0, weight=1)
    self.topframe.grid_rowconfigure(1, weight=1)
    self.warning = ctk.CTkLabel(self.topframe, font=("Arial", 20),
                                text='Are you sure?')
    self.warning.grid(column=0, row=0, pady=10, padx=10, columnspan=3, sticky='nsew')
    self.yes_button = ctk.CTkButton(self.topframe, text='Yes, continue', command=lambda: [self.btn_exit_popup(),
                                                                                          btn_kill_mevegs_clicked(self),
                                                                                          return_running_jobs_to_null(
                                                                                              self)])
    self.yes_button.grid(column=0, row=1, pady=10, padx=10, sticky='nesw')
    self.exit_button = ctk.CTkButton(master=self.topframe, text='No, cancel', command=lambda: [self.btn_exit_popup()])
    self.exit_button.grid(column=1, row=1, pady=10, padx=10, sticky='nesw')


def are_you_sure_cleanup(self):
    self.topframe = ctk.CTkToplevel(self.gui)  # , fg_color="indian red")
    self.topframe.grab_set()
    self.topframe.geometry("700x300")
    self.topframe.attributes('-topmost', True)
    self.topframe.update()
    self.topframe.focus()
    self.topframe.title('Confirm')
    self.topframe.grid_columnconfigure(0, weight=1)
    self.topframe.grid_columnconfigure(1, weight=1)
    self.topframe.grid_rowconfigure(0, weight=1)
    self.topframe.grid_rowconfigure(1, weight=1)
    self.warning = ctk.CTkLabel(self.topframe, font=("Arial", 20),
                                text='Are you sure?')
    self.warning.grid(column=0, row=0, pady=10, padx=10, columnspan=3, sticky='nsew')
    self.yes_button = ctk.CTkButton(self.topframe, text='Yes, continue', command=lambda: [self.btn_exit_popup(),
                                                                                          self.btn_restore_mevegs_clicked()])
    self.yes_button.grid(column=0, row=1, pady=10, padx=10, sticky='nesw')
    self.exit_button = ctk.CTkButton(master=self.topframe, text='No, cancel', command=lambda: [self.btn_exit_popup()])
    self.exit_button.grid(column=1, row=1, pady=10, padx=10, sticky='nesw')


def btn_show_mevegs_jobs_clicked(self):
    f = wmi.WMI()
    count = 0
    for process in f.Win32_Process():
        if process.Name == 'mevegs.exe':
            count += 1
    write_to_console_log(self, 'MevEGS:\t\tThere are ' + str(count) + ' local jobs running')
    self.frame_1.update_idletasks()


def return_running_jobs_to_null(self):
    write_to_console_log(self, 'MevEGS:\t\tThere are 0 local jobs running')
    self.gui.update_idletasks()


def menu_full_screen_clicked(self):
    if self.gui.state() == 'normal':
        self.gui.state('zoomed')
        write_to_console_log(self, "Full Screen:\t\tTrue")
    else:
        self.gui.state('normal')
        write_to_console_log(self, "Full Screen:\t\tNormal")


def load_gmsh_data_for_figures(self, path_results_msh_file, path_directory_project, path_egsinp_file):
    if gmsh.isInitialized():
        pass
    else:
        gmsh.initialize()
    gmsh.logger.start()
    msh_data = MshResults_io(path_results_msh_file, path_directory_project, path_egsinp_file, [self.console_text_box_input, self.console_text_box_1, self.console_text_box_2, self.console_text_box_3])
    msh_data.load_model_information()
    view_tags = gmsh.view.getTags()
    view_names = msh_data.get_all_views()
    self.view_dict = {view_names[i]: view_tags[i] - 1 for i in range(len(view_names))}
    self.gmsh_views = '\n'.join(view_names)
    try:
        if self.view_scroll_frame_3.winfo_exists():
            self.view_scroll_frame_3.destroy()
    except AttributeError:
        pass
    try:
        if self.view_scroll_frame.winfo_exists():
            self.view_scroll_frame.destroy()
    except AttributeError:
        pass
    self.view_scroll_frame = ViewsCheckboxFrame(self.frame_3, 'Views', list(self.view_dict.keys()))
    self.view_scroll_frame.grid(column=0, row=4, pady=5, padx=5, sticky='w', rowspan=5)

    # gmsh.open(self.directory_file_project_msh)
    # views_names = [gmsh.option.getString(f'View[{gmsh.view.getIndex(tag)}].Name') for tag in views_tags]
    # self.gmsh_views = '\n'.join(views_names)
    gmsh_views_log = gmsh.logger.get()
    str_gmsh_views_log = '\n'.join(gmsh_views_log)
    gmsh.logger.stop()
    write_to_console_log(self, 'GMSH:\t\t' + str_gmsh_views_log)
    gmsh.finalize()  # might not need this
    return self.view_dict


def one_d_generation_gmsh(self):
    checked_view_list = self.view_scroll_frame.get()
    if len(checked_view_list) > 1:
        write_to_console_log(self, "MevEGS:\t\tOnly one GMSH view can be checked")
        return
    checked_view = ''.join(checked_view_list)
    view_tag = self.view_dict[checked_view]
    self.topframe = ctk.CTkToplevel(self.gui)
    # self.topframe.grab_set()
    # self.topframe.geometry("600x700")
    self.topframe.attributes('-topmost', True)
    self.topframe.geometry("+0+0")
    self.topframe.focus()
    self.topframe.title('1D Coordinates - ' + checked_view)
    self.topframe.update()
    msh_data = MshResults_io(self.directory_file_project_msh, self.directory_project, self.directory_file_egsinp,
                             [self.console_text_box_input, self.console_text_box_1, self.console_text_box_2, self.console_text_box_3])
    msh_data.load_model_information()
    self.lbl_create_figs_tf = ctk.CTkLabel(self.topframe, text="Enter start- and end-points",
                                           font=('Helvetica', 16, 'bold'), justify='center')
    self.lbl_create_figs_tf.grid(column=0, row=0, padx=5, pady=5, columnspan=4)

    self.lbl_x0_tf = ctk.CTkLabel(self.topframe, text="X0:", font=('Helvetica', 12, 'normal'))
    self.lbl_x0_tf.grid(column=0, row=1, padx=(5, 0), pady=5, sticky='e')
    self.lbl_y0_tf = ctk.CTkLabel(self.topframe, text="Y0:", font=('Helvetica', 12, 'normal'))
    self.lbl_y0_tf.grid(column=0, row=2, padx=(5, 0), pady=5, sticky='e')
    self.lbl_z0_tf = ctk.CTkLabel(self.topframe, text="Z0:", font=('Helvetica', 12, 'normal'))
    self.lbl_z0_tf.grid(column=0, row=3, padx=(5, 0), pady=5, sticky='e')
    self.lbl_x1_tf = ctk.CTkLabel(self.topframe, text="X1:", font=('Helvetica', 12, 'normal'))
    self.lbl_x1_tf.grid(column=2, row=1, padx=(5, 0), pady=5, sticky='e')
    self.lbl_y1_tf = ctk.CTkLabel(self.topframe, text="Y1:", font=('Helvetica', 12, 'normal'))
    self.lbl_y1_tf.grid(column=2, row=2, padx=(5, 0), pady=5, sticky='e')
    self.lbl_z1_tf = ctk.CTkLabel(self.topframe, text="Z1:", font=('Helvetica', 12, 'normal'))
    self.lbl_z1_tf.grid(column=2, row=3, padx=(5, 0), pady=5, sticky='e')
    self.lbl_num_points_3 = ctk.CTkLabel(self.topframe, text="Number of points - line:  ",
                                         font=('Helvetica', 12, 'normal'))
    self.lbl_num_points_3.grid(column=0, row=4, padx=(5, 0), pady=5, sticky='e', columnspan=3)

    self.x0_entry = ctk.CTkEntry(self.topframe, width=60)
    self.x0_entry.grid(column=1, row=1, padx=(0, 5), pady=5, sticky='w')
    self.y0_entry = ctk.CTkEntry(self.topframe, width=60)
    self.y0_entry.grid(column=1, row=2, padx=(0, 5), pady=5, sticky='w')
    self.z0_entry = ctk.CTkEntry(self.topframe, width=60)
    self.z0_entry.grid(column=1, row=3, padx=(0, 5), pady=5, sticky='w')
    self.x1_entry = ctk.CTkEntry(self.topframe, width=60)
    self.x1_entry.grid(column=3, row=1, padx=(0, 5), pady=5, sticky='w')
    self.y1_entry = ctk.CTkEntry(self.topframe, width=60)
    self.y1_entry.grid(column=3, row=2, padx=(0, 5), pady=5, sticky='w')
    self.z1_entry = ctk.CTkEntry(self.topframe, width=60)
    self.z1_entry.grid(column=3, row=3, padx=(0, 5), pady=5, sticky='w')
    self.num_points_entry_3 = ctk.CTkEntry(self.topframe, width=60)
    self.num_points_entry_3.grid(column=3, row=4, padx=(0, 5), pady=5, sticky='w')

    self.btn_make_fig = ctk.CTkButton(self.topframe, text='Plot Figure',
                                      command=lambda: one_d_generate_gmsh_figure(self, msh_data, view_tag,
                                                                                 float(self.x0_entry.get()),
                                                                                 float(self.y0_entry.get()),
                                                                                 float(self.z0_entry.get()),
                                                                                 float(self.x1_entry.get()),
                                                                                 float(self.y1_entry.get()),
                                                                                 float(self.z1_entry.get()),
                                                                                 int(self.num_points_entry_3.get())))
    self.btn_make_fig.grid(column=0, row=20, pady=5, padx=5, sticky='nesw', columnspan=2)
    self.exit_button_tf = ctk.CTkButton(self.topframe, text='Exit', command=lambda: [self.btn_exit_popup()])
    self.exit_button_tf.grid(column=2, row=20, pady=5, padx=5, sticky='nesw', columnspan=2)


def one_d_generate_gmsh_figure(self, msh_data, view_tag, x0, y0, z0, x1, y1, z1, numpoints):
    msh_data.return_1D(view_tag, x0, y0, z0, x1, y1, z1, numpoints)
    gmsh_line = pd.read_csv(self.directory_project + 'exports/' + 'gmsh_line.csv', sep=' ', header=None,
                            usecols=[4, 5, 6, 7])
    checked_view_list = self.view_scroll_frame.get()
    checked_view = ''.join(checked_view_list)
    gmsh_line.columns = ['X', 'Y', 'Z', checked_view]
    if len(checked_view.split(' ')) < 3:
        view_save_tag = ''.join(list(checked_view.split(' ')[0])[:6])
    elif (checked_view.split(' ')[2])[0] == '[':
        view_save_tag = (
                    ''.join(list(checked_view.split(' ')[0])[:3]) + '_' + ''.join(list(checked_view.split(' ')[1])[:3]))
    else:
        view_save_tag = (''.join(list(checked_view.split(' ')[0])[:3]) + '_' + ''.join(
            list(checked_view.split(' ')[1])[:3]) +
                         '_' + ''.join(list(checked_view.split(' ')[2])[0]))
    line_save_file = (view_save_tag + '_' + str(int(x0)) + '_' + str(int(y0)) + '_' + str(int(z0)) + '_' +
                      str(int(x1)) + '_' + str(int(y1)) + '_' + str(int(z1)) + '_' + str(int(numpoints)) + '.csv')
    gmsh_line.to_csv(self.directory_project + 'exports/line_gmsh_' + line_save_file, sep=',', index=False)
    os.remove(self.directory_project + 'exports/gmsh_line.csv')
    gmsh.finalize()
    self.btn_exit_popup()
    self.topframe = ctk.CTkToplevel(self.gui)
    # self.topframe.grab_set()
    # self.topframe.geometry("600x700")
    self.topframe.attributes('-topmost', True)
    cmd = 'wmic desktopmonitor get screenheight, screenwidth'
    size_tuple = tuple(map(int, os.popen(cmd).read().split()[-2::]))
    self.topframe.geometry("+" + str(0.75 * size_tuple[1]) + "+" + str(0.75 * size_tuple[0]))
    self.topframe.title('1D Coordinates - ' + checked_view)
    self.topframe.update()
    # self.topframe.focus()
    pd_line = pd.read_csv(self.directory_project + 'exports/line_gmsh_' + line_save_file, sep=',')
    file = 'line_gmsh_' + line_save_file
    figure = Figure(figsize=(6, 4), dpi=200)
    figure_canvas = FigureCanvasTkAgg(figure, self.topframe)
    NavigationToolbar2Tk(figure_canvas, self.topframe)
    ax1 = figure.add_subplot()
    if np.abs(pd_line['X'].max() - pd_line['X'].min()) >= np.abs(pd_line['Y'].max() - pd_line['Y'].min()) and np.abs(
            pd_line['X'].max() - pd_line['X'].min()) >= np.abs(pd_line['Z'].max() - pd_line['Z'].min()):
        ax1.plot(pd_line["X"], pd_line[pd_line.columns[3]], label=pd_line.columns[3])
        ax1.set_xlabel('Projected onto X')
    elif np.abs(pd_line['X'].max() - pd_line['X'].min()) < np.abs(pd_line['Y'].max() - pd_line['Y'].min()) and np.abs(
            pd_line['Y'].max() - pd_line['Y'].min()) >= np.abs(pd_line['Z'].max() - pd_line['Z'].min()):
        ax1.plot(pd_line["Y"], pd_line[pd_line.columns[3]], label=pd_line.columns[3])
        ax1.set_xlabel('Projected onto Y')
    else:
        ax1.plot(pd_line["Z"], pd_line[pd_line.columns[3]], label=pd_line.columns[3])
        ax1.set_ylim([np.min(pd_line[pd_line.columns[3]])-.05*np.min(pd_line[pd_line.columns[3]]), np.max(pd_line[pd_line.columns[3]])+.05*np.max(pd_line[pd_line.columns[3]])])
        ax1.set_xlabel('Projected onto Z')
    graph_title = '[' + file.split('.csv')[0].split('_')[-7] + ',' + file.split('.csv')[0].split('_')[-6] + ',' + \
                  file.split('.csv')[0].split('_')[-5] + '][' + \
                  file.split('.csv')[0].split('_')[-4] + ',' + file.split('.csv')[0].split('_')[-3] + ',' + \
                  file.split('.csv')[0].split('_')[-2] + '][' + file.split('.csv')[0].split('_')[-1] + ']'
    ax1.grid(which='both', axis='both', alpha=0.25)
    ax1.set_title('GMSH line plot ' + graph_title)
    ax1.legend()
    figure_canvas.get_tk_widget().pack()
    save_me = 'line_gmsh_' + view_save_tag + graph_title + '.png'
    self.btn_save_fig_to = ctk.CTkButton(self.topframe, text='Save Figure As',
                                         command=lambda: [save_fig_to_gmsh(self, figure, save_me)])
    self.btn_save_fig_to.pack(pady=5, padx=5)
    self.exit_button = ctk.CTkButton(self.topframe, text='Close', command=lambda: [self.btn_exit_popup()])
    self.exit_button.pack(pady=5, padx=5)


def save_fig_to_gmsh(self, figure, save_name):
    os.makedirs(self.directory_project + 'figures/', exist_ok=True)
    figure.savefig(self.directory_project + 'figures/' + save_name)
    self.btn_exit_popup()
    write_to_console_log(self, "MevEGS:\t\tFigure saved to " + self.directory_project + 'figures/' + save_name)


def two_d_generation_gmsh(self):
    checked_view_list = self.view_scroll_frame.get()
    if len(checked_view_list) > 1:
        write_to_console_log(self, "MevEGS:\t\tOnly one GMSH view can be checked")
        return
    checked_view = ''.join(checked_view_list)
    view_tag = self.view_dict[checked_view]
    self.topframe = ctk.CTkToplevel(self.gui)
    # self.topframe.grab_set()
    # self.topframe.geometry("600x700")
    self.topframe.attributes('-topmost', True)
    self.topframe.geometry("+0+0")
    self.topframe.focus()
    self.topframe.title('2D Coordinates - ' + checked_view)
    self.topframe.update()
    msh_data = MshResults_io(self.directory_file_project_msh, self.directory_project, self.directory_file_egsinp,
                             [self.console_text_box_input, self.console_text_box_1, self.console_text_box_2, self.console_text_box_3])
    msh_data.load_model_information()
    self.lbl_create_figs_tf = ctk.CTkLabel(self.topframe, text="P0: Origin", font=('Helvetica', 16, 'bold'),
                                           justify='center')
    self.lbl_create_figs_tf.grid(column=0, row=0, padx=5, pady=5, columnspan=2)
    self.lbl_create_figs_tf = ctk.CTkLabel(self.topframe, text="P1: Axis of U", font=('Helvetica', 16, 'bold'),
                                           justify='center')
    self.lbl_create_figs_tf.grid(column=2, row=0, padx=5, pady=5, columnspan=2)
    self.lbl_create_figs_tf = ctk.CTkLabel(self.topframe, text="P2: Axis of V (P0->P2)", font=('Helvetica', 16, 'bold'),
                                           justify='center')
    self.lbl_create_figs_tf.grid(column=4, row=0, padx=5, pady=5, columnspan=2)

    # SPACE LEFT TO EXPLAIN HOW TO MAKE 90 DEG ANGLE (ORTHOGONAL) PLANE

    self.lbl_x0_tf = ctk.CTkLabel(self.topframe, text="X0:", font=('Helvetica', 12, 'normal'))
    self.lbl_x0_tf.grid(column=0, row=3, padx=(5, 0), pady=5, sticky='e')
    self.lbl_y0_tf = ctk.CTkLabel(self.topframe, text="Y0:", font=('Helvetica', 12, 'normal'))
    self.lbl_y0_tf.grid(column=0, row=4, padx=(5, 0), pady=5, sticky='e')
    self.lbl_z0_tf = ctk.CTkLabel(self.topframe, text="Z0:", font=('Helvetica', 12, 'normal'))
    self.lbl_z0_tf.grid(column=0, row=5, padx=(5, 0), pady=5, sticky='e')
    self.lbl_x1_tf = ctk.CTkLabel(self.topframe, text="X1:", font=('Helvetica', 12, 'normal'))
    self.lbl_x1_tf.grid(column=2, row=3, padx=(5, 0), pady=5, sticky='e')
    self.lbl_y1_tf = ctk.CTkLabel(self.topframe, text="Y1:", font=('Helvetica', 12, 'normal'))
    self.lbl_y1_tf.grid(column=2, row=4, padx=(5, 0), pady=5, sticky='e')
    self.lbl_z1_tf = ctk.CTkLabel(self.topframe, text="Z1:", font=('Helvetica', 12, 'normal'))
    self.lbl_z1_tf.grid(column=2, row=5, padx=(5, 0), pady=5, sticky='e')
    self.lbl_x2_tf = ctk.CTkLabel(self.topframe, text="X2:", font=('Helvetica', 12, 'normal'))
    self.lbl_x2_tf.grid(column=4, row=3, padx=(5, 0), pady=5, sticky='e')
    self.lbl_y2_tf = ctk.CTkLabel(self.topframe, text="Y2:", font=('Helvetica', 12, 'normal'))
    self.lbl_y2_tf.grid(column=4, row=4, padx=(5, 0), pady=5, sticky='e')
    self.lbl_z2_tf = ctk.CTkLabel(self.topframe, text="Z2:", font=('Helvetica', 12, 'normal'))
    self.lbl_z2_tf.grid(column=4, row=5, padx=(5, 0), pady=5, sticky='e')

    self.lbl_num_pointsu_3 = ctk.CTkLabel(self.topframe, text="Number of points - P0 to P1:  ",
                                          font=('Helvetica', 12, 'normal'))
    self.lbl_num_pointsu_3.grid(column=0, row=6, padx=(5, 0), pady=5, sticky='e', columnspan=2)
    self.lbl_num_pointsv_3 = ctk.CTkLabel(self.topframe, text="Number of points - P0 to P2:  ",
                                          font=('Helvetica', 12, 'normal'))
    self.lbl_num_pointsv_3.grid(column=3, row=6, padx=(5, 0), pady=5, sticky='e', columnspan=2)

    self.x0_entry = ctk.CTkEntry(self.topframe, width=60)
    self.x0_entry.grid(column=1, row=3, padx=(0, 5), pady=5, sticky='w')
    self.y0_entry = ctk.CTkEntry(self.topframe, width=60)
    self.y0_entry.grid(column=1, row=4, padx=(0, 5), pady=5, sticky='w')
    self.z0_entry = ctk.CTkEntry(self.topframe, width=60)
    self.z0_entry.grid(column=1, row=5, padx=(0, 5), pady=5, sticky='w')
    self.x1_entry = ctk.CTkEntry(self.topframe, width=60)
    self.x1_entry.grid(column=3, row=3, padx=(0, 5), pady=5, sticky='w')
    self.y1_entry = ctk.CTkEntry(self.topframe, width=60)
    self.y1_entry.grid(column=3, row=4, padx=(0, 5), pady=5, sticky='w')
    self.z1_entry = ctk.CTkEntry(self.topframe, width=60)
    self.z1_entry.grid(column=3, row=5, padx=(0, 5), pady=5, sticky='w')
    self.x2_entry = ctk.CTkEntry(self.topframe, width=60)
    self.x2_entry.grid(column=5, row=3, padx=(0, 5), pady=5, sticky='w')
    self.y2_entry = ctk.CTkEntry(self.topframe, width=60)
    self.y2_entry.grid(column=5, row=4, padx=(0, 5), pady=5, sticky='w')
    self.z2_entry = ctk.CTkEntry(self.topframe, width=60)
    self.z2_entry.grid(column=5, row=5, padx=(0, 5), pady=5, sticky='w')
    self.num_pointsu_entry_3 = ctk.CTkEntry(self.topframe, width=60)
    self.num_pointsu_entry_3.grid(column=2, row=6, padx=(0, 5), pady=5, sticky='w')
    self.num_pointsv_entry_3 = ctk.CTkEntry(self.topframe, width=60)
    self.num_pointsv_entry_3.grid(column=5, row=6, padx=(0, 5), pady=5, sticky='w')

    self.btn_make_fig = ctk.CTkButton(self.topframe, text='Plot Figure',
                                      command=lambda: two_d_generate_gmsh_figure(self, msh_data, view_tag,
                                                                                 float(self.x0_entry.get()),
                                                                                 float(self.y0_entry.get()),
                                                                                 float(self.z0_entry.get()),
                                                                                 float(self.x1_entry.get()),
                                                                                 float(self.y1_entry.get()),
                                                                                 float(self.z1_entry.get()),
                                                                                 float(self.x2_entry.get()),
                                                                                 float(self.y2_entry.get()),
                                                                                 float(self.z2_entry.get()),
                                                                                 int(self.num_pointsu_entry_3.get()),
                                                                                 int(self.num_pointsv_entry_3.get())))
    self.btn_make_fig.grid(column=0, row=20, pady=5, padx=5, sticky='nesw', columnspan=3)
    self.exit_button_tf = ctk.CTkButton(self.topframe, text='Exit', command=lambda: [self.btn_exit_popup()])
    self.exit_button_tf.grid(column=3, row=20, pady=5, padx=5, sticky='nesw', columnspan=3)


def two_d_generate_gmsh_figure(self, msh_data, view_tag, x0, y0, z0, x1, y1, z1, x2, y2, z2, numpointsu, numpointsv):
    msh_data.return_2D(view_tag, x0, y0, z0, x1, y1, z1, x2, y2, z2, numpointsu, numpointsv)
    gmsh_plane = pd.read_csv(self.directory_project + 'exports/' + 'gmsh_plane.csv', sep=' ', header=None,
                             usecols=[4, 5, 6, 7])
    checked_view_list = self.view_scroll_frame.get()
    checked_view = ''.join(checked_view_list)
    gmsh_plane.columns = ['X', 'Y', 'Z', checked_view]
    if len(checked_view.split(' ')) < 3:
        view_save_tag = ''.join(list(checked_view.split(' ')[0])[:6])
    elif (checked_view.split(' ')[2])[0] == '[':
        view_save_tag = (
                    ''.join(list(checked_view.split(' ')[0])[:3]) + '_' + ''.join(list(checked_view.split(' ')[1])[:3]))
    else:
        view_save_tag = (''.join(list(checked_view.split(' ')[0])[:3]) + '_' + ''.join(
            list(checked_view.split(' ')[1])[:3]) +
                         '_' + ''.join(list(checked_view.split(' ')[2])[0]))
    plane_save_file = (view_save_tag + '_' + str(int(x0)) + '_' + str(int(y0)) + '_' + str(int(z0)) + '_' +
                       str(int(x1)) + '_' + str(int(y1)) + '_' + str(int(z1)) + '_' + str(int(x2)) + '_' +
                       str(int(y2)) + '_' + str(int(z2)) + '_' + str(int(numpointsu)) + '_' + str(int(numpointsv)) +
                       '.csv')
    gmsh_plane.to_csv(self.directory_project + 'exports/plane_gmsh_' + plane_save_file, sep=',', index=False)
    os.remove(self.directory_project + 'exports/gmsh_plane.csv')
    gmsh.finalize()
    self.btn_exit_popup()
    self.topframe = ctk.CTkToplevel(self.gui)
    # self.topframe.grab_set()
    # self.topframe.geometry("600x700")
    self.topframe.attributes('-topmost', True)
    cmd = 'wmic desktopmonitor get screenheight, screenwidth'
    size_tuple = tuple(map(int, os.popen(cmd).read().split()[-2::]))
    self.topframe.geometry("+" + str(0.75 * size_tuple[1]) + "+" + str(0.75 * size_tuple[0]))
    self.topframe.title('2D Coordinates - ' + checked_view)
    self.topframe.update()
    # self.topframe.focus()
    pd_plane = pd.read_csv(self.directory_project + 'exports/plane_gmsh_' + plane_save_file, sep=',')
    file = 'plane_gmsh_' + plane_save_file

    # X and Y larger than Z
    if np.abs(pd_plane['X'].max() - pd_plane['X'].min()) and np.abs(
            pd_plane['Y'].max() - pd_plane['Y'].min()) >= np.abs(
            pd_plane['Z'].max() - pd_plane['Z'].min()):
        range_x = np.arange(pd_plane['X'].min(), pd_plane['X'].max(),
                            (pd_plane['X'].max() - pd_plane['X'].min()) / int(numpointsu))
        range_y = np.arange(pd_plane['Y'].min(), pd_plane['Y'].max(),
                            (pd_plane['Y'].max() - pd_plane['Y'].min()) / int(numpointsv))
        hist, xedges, yedges, _ = plt.hist2d(pd_plane['X'], pd_plane['Y'], bins=[range_x, range_y],
                                             weights=pd_plane[checked_view])
        x_surf, y_surf = np.meshgrid(xedges[:-1] + xedges[1:], yedges[:-1] + yedges[1:]) - abs(xedges[1] - xedges[0])
        x_surf = x_surf.flatten() / 2
        y_surf = y_surf.flatten() / 2
        dx_surf = xedges[1] - xedges[0]
        dy_surf = yedges[1] - yedges[0]
        histT = hist.transpose()
        dz_surf = histT.flatten()
        figure = Figure(figsize=(8, 8), dpi=100)
        figure_canvas = FigureCanvasTkAgg(figure, self.topframe)
        NavigationToolbar2Tk(figure_canvas, self.topframe)
        ax1 = figure.add_subplot(1, 1, 1, projection='3d')
        picture = ax1.plot_trisurf(x_surf + dx_surf / 2, y_surf + dy_surf / 2, dz_surf,
                                   cmap=matplotlib.colormaps['turbo'], label=checked_view)
        ax1.set_xlabel('Projection U')
        ax1.set_ylabel('Projection V')
        ax1.set_xlim(np.max(x_surf + dx_surf / 2), np.min(x_surf + dx_surf / 2))
    elif np.abs(pd_plane['X'].max() - pd_plane['X'].min()) and np.abs(
            pd_plane['Z'].max() - pd_plane['Z'].min()) >= np.abs(
            pd_plane['Y'].max() - pd_plane['Y'].min()):
        range_x = np.arange(pd_plane['X'].min(), pd_plane['X'].max(),
                            (pd_plane['X'].max() - pd_plane['X'].min()) / int(numpointsu))
        range_y = np.arange(pd_plane['Z'].min(), pd_plane['Z'].max(),
                            (pd_plane['Z'].max() - pd_plane['Z'].min()) / int(numpointsv))
        hist, xedges, yedges, _ = plt.hist2d(pd_plane['X'], pd_plane['Z'], bins=[range_x, range_y],
                                             weights=pd_plane[checked_view])
        x_surf, y_surf = np.meshgrid(xedges[:-1] + xedges[1:], yedges[:-1] + yedges[1:]) - abs(xedges[1] - xedges[0])
        x_surf = x_surf.flatten() / 2
        y_surf = y_surf.flatten() / 2
        dx_surf = xedges[1] - xedges[0]
        dy_surf = yedges[1] - yedges[0]
        histT = hist.transpose()
        dz_surf = histT.flatten()
        figure = Figure(figsize=(8, 8), dpi=100)
        figure_canvas = FigureCanvasTkAgg(figure, self.topframe)
        NavigationToolbar2Tk(figure_canvas, self.topframe)
        ax1 = figure.add_subplot(projection='3d')  # 1, 1, 1,
        picture = ax1.plot_trisurf(x_surf + dx_surf / 2, y_surf + dy_surf / 2, dz_surf,
                                   cmap=matplotlib.colormaps['turbo'], label=checked_view)
        ax1.set_xlabel('Projection U')
        ax1.set_ylabel('Projection V')
        ax1.set_xlim(np.max(x_surf + dx_surf / 2), np.min(x_surf + dx_surf / 2))
    else:
        range_x = np.arange(pd_plane['Y'].min(), pd_plane['Y'].max(),
                            (pd_plane['Y'].max() - pd_plane['Y'].min()) / int(numpointsu))
        range_y = np.arange(pd_plane['Z'].min(), pd_plane['Z'].max(),
                            (pd_plane['Z'].max() - pd_plane['Z'].min()) / int(numpointsv))
        hist, xedges, yedges, _ = plt.hist2d(pd_plane['Y'], pd_plane['Z'], bins=[range_x, range_y],
                                             weights=pd_plane[checked_view])
        x_surf, y_surf = np.meshgrid(xedges[:-1] + xedges[1:], yedges[:-1] + yedges[1:]) - abs(xedges[1] - xedges[0])
        x_surf = x_surf.flatten() / 2
        y_surf = y_surf.flatten() / 2
        dx_surf = xedges[1] - xedges[0]
        dy_surf = yedges[1] - yedges[0]
        histT = hist.transpose()
        dz_surf = histT.flatten()
        figure = Figure(figsize=(8, 8), dpi=100)
        figure_canvas = FigureCanvasTkAgg(figure, self.topframe)
        NavigationToolbar2Tk(figure_canvas, self.topframe)
        ax1 = figure.add_subplot(1, 1, 1, projection='3d')
        picture = ax1.plot_trisurf(x_surf + dx_surf / 2, y_surf + dy_surf / 2, dz_surf,
                                   cmap=matplotlib.colormaps['turbo'],
                                   label=checked_view)
        ax1.set_xlabel('Projection U')
        ax1.set_ylabel('Projection V')
        ax1.set_xlim(np.max(x_surf + dx_surf / 2), np.min(x_surf + dx_surf / 2))

    graph_title = '[' + file.split('.csv')[0].split('_')[-11] + ',' + file.split('.csv')[0].split('_')[-10] + ',' + \
                  file.split('.csv')[0].split('_')[-9] + '][' + file.split('.csv')[0].split('_')[-8] + ',' + \
                  file.split('.csv')[0].split('_')[-7] + ',' + file.split('.csv')[0].split('_')[-6] + '][' + \
                  file.split('.csv')[0].split('_')[-5] + ',' + file.split('.csv')[0].split('_')[-4] + ',' + \
                  file.split('.csv')[0].split('_')[-3] + '][' + file.split('.csv')[0].split('_')[-2] + ',' + \
                  file.split('.csv')[0].split('_')[-1] + ']'
    ax1.set_title('GMSH plane plot ' + graph_title)
    ax1.legend()
    # ax1.set_aspect("equal")  # , adjustable="datalim")
    cbar_ax = figure.add_axes([0.91, 0.2, 0.03, 0.6])
    figure.colorbar(picture, cax=cbar_ax)
    figure_canvas.get_tk_widget().pack()
    save_me = 'plane_gmsh_' + view_save_tag + graph_title + '.png'
    self.btn_save_fig_to = ctk.CTkButton(self.topframe, text='Save Figure and Close',
                                         command=lambda: [save_fig_to_gmsh(self, figure, save_me)])
    self.btn_save_fig_to.pack(pady=5, padx=5)
    self.exit_button = ctk.CTkButton(self.topframe, text='Close', command=lambda: [self.btn_exit_popup()])
    self.exit_button.pack(pady=5, padx=5)


def color_theme_notice(self):
    self.topframe = ctk.CTkToplevel(self.gui)
    self.topframe.grab_set()
    # self.topframe.geometry("600x700")
    self.topframe.attributes('-topmost', True)
    self.topframe.geometry("+0+0")
    self.topframe.update()
    self.topframe.focus()
    self.topframe.title('Notice')
    self.warning = ctk.CTkLabel(self.topframe, font=("Arial", 20),
                                text='Please Exit and Restart the MevEGS application\nto initialize this color-theme change')
    self.warning.grid(column=0, row=0, pady=50, padx=30, columnspan=2, sticky='nsew')
    self.color_theme = ctk.ThemeManager._currently_loaded_theme
    dark_only_themes = ['Greengage', 'Hades', 'Harlequin', 'NightTrain', 'TrojanBlue']
    light_to_dark_trigger = False
    for _theme in dark_only_themes:
        if self.color_theme == _theme:
            if ctk.get_appearance_mode() == 'Light':
                light_to_dark_trigger = True
                self.theme_warning = ctk.CTkLabel(self.topframe, font=("Arial", 16),
                                                  text='The ' + self.color_theme + ' does not support \'Light\' appearance mode\n\'Dark\' mode will be enabled')
                self.theme_warning.grid(column=0, row=1, pady=5, padx=5, columnspan=2, sticky='nsew')
    self.restart_button = ctk.CTkButton(master=self.topframe, text='Restart Now', height=50,
                                        command=lambda: [self.btn_exit_popup(),
                                                         light_dark_trigger(self, light_to_dark_trigger),
                                                         restart_app_now(self)])  # ctk.set_appearance_mode('Dark'),
    self.restart_button.grid(column=0, row=2, pady=50, padx=5, sticky='nesw')
    self.exit_button = ctk.CTkButton(master=self.topframe, text='Restart Later', height=50,
                                     command=lambda: [self.btn_exit_popup()])
    self.exit_button.grid(column=1, row=2, pady=50, padx=5, sticky='nesw')


def light_dark_trigger(self, trigger):
    if trigger:
        ctk.set_appearance_mode('Dark')


def restart_app_now(self):
    save_dict = self.mevegs_save_dictionary()
    with open(self.directory_ini + '/mevegs_app.ini', 'w', newline='') as myfile:
        w = csv.writer(myfile)
        w.writerows(save_dict.items())
    # command = "python MevEGS_gui.py"
    self.gui.update_idletasks()
    self.gui.quit()
    self.gui.destroy()
    for after_id in self.gui.tk.eval('after info').split():  # Allows program to end by catching many of the 'after'
        self.gui.after_cancel(after_id)  # commands that CTk runs behind scenes
    os.chdir(self.directory_ini)
    #  Need a process here to close the old python window, which doesn't close on repeated
    subprocess.Popen(str("cmd python /k " + self.directory_ini + "MevEGS_gui.py"))


def save_project(self):
    self.topframe = ctk.CTkToplevel(self.gui)  # , fg_color="indian red")
    self.topframe.grab_set()
    self.topframe.geometry("400x200")
    self.topframe.attributes('-topmost', True)
    self.topframe.update()
    self.topframe.focus()
    self.topframe.title('Save Project')
    self.topframe.grid_columnconfigure(0, weight=1)
    self.topframe.grid_columnconfigure(1, weight=1)
    self.topframe.grid_columnconfigure(2, weight=1)
    self.topframe.grid_rowconfigure(0, weight=1)
    self.topframe.grid_rowconfigure(1, weight=1)
    self.warning = ctk.CTkLabel(self.topframe, font=("Arial", 24),
                                text='Save current project first?')
    self.warning.grid(column=0, row=0, pady=50, padx=50, columnspan=3, sticky='nsew')
    self.yes_button = ctk.CTkButton(self.topframe, text='Yes', width=150, command=lambda: [self.btn_exit_popup(),
                                                                                           self.btn_save_state_clicked(),
                                                                                           restore_defaults(self)])
    self.yes_button.grid(column=0, row=1, pady=20, padx=10, sticky='nesw')
    self.exit_button = ctk.CTkButton(master=self.topframe, text='No', width=150,
                                     command=lambda: [self.btn_exit_popup(), restore_defaults(self)])
    self.exit_button.grid(column=1, row=1, pady=20, padx=10, sticky='nesw')
    self.cancel_button = ctk.CTkButton(master=self.topframe, text='Cancel', width=145,
                                       command=lambda: [self.btn_exit_popup()])
    self.cancel_button.grid(column=2, row=1, pady=20, padx=10, sticky='nesw')


def restore_defaults(self):
    self.directory_file_egsinp = 'Choose .egsinp File'
    self.directory_file_msh = 'Choose .msh File'
    self.directory_project = 'Choose Project Directory'
    self.njobs = '1'
    self.directory_file_project_msh = 'Choose .results.msh File'
    self.gmsh_views = ''
    self.gmsh_groups = ''
    self.directory_source = ''
    self.file_source = ''
    self.bar_progress = 0
    self.quit_progress_bar = False
    self.menu_data = ''
    self.menu_source = ''
    self.view_dict = {}

    self.btn_egsinp_explore.configure(text=self.directory_file_egsinp)
    self.btn_mesh_explore.configure(text=self.directory_file_msh)
    self.btn_project_explore.configure(text=self.directory_project)
    self.job_number.set(self.njobs)
    self.btn_results_mesh_explore.configure(text=os.path.basename(self.directory_file_project_msh))
    self.gui.title('MevEGS - New Project')
    write_to_console_log(self, 'MevEGS:\t\tNew project started')
    self.gui.update_idletasks()
    return self.directory_file_egsinp, self.directory_file_msh, self.directory_project, self.directory_file_project_msh

def create_hover_tooltips(self):
    # Input Tab
    self.btn_project_explore_tip = CTkToolTip(self.btn_project_explore, delay=0.1, message=self.directory_project + '\n'
                                                                                            'One simulation per project folder\n'
                                                                                            'A main project folder can have many subfolders')
    self.btn_project_explore_new_tip = CTkToolTip(self.btn_project_explore_new, delay=0.1, message='Resets project and input files')
    self.btn_egsinp_explore_tip = CTkToolTip(self.btn_egsinp_explore, delay=0.1, message=self.directory_file_egsinp)
    self.btn_egsinp_build_tip = CTkToolTip(self.btn_egsinp_build, delay=0.1, message='Under development')
    self.btn_mesh_explore_tip = CTkToolTip(self.btn_mesh_explore, delay=0.1, message=self.directory_file_msh)
    self.btn_results_mesh_explore_tip = CTkToolTip(self.btn_results_mesh_explore, delay=0.1,
                                                   message=self.directory_file_project_msh)
    self.menu_source_1_tip = CTkToolTip(self.menu_source_1, delay=0.1,
                                        message=self.directory_ini + 'Source_Phasespace_Files/')
    self.btn_mevegs_explore_tip = CTkToolTip(self.btn_mevegs_explore, delay=0.1, message=self.directory_mevegs)
    self.btn_pegs_explore_tip = CTkToolTip(self.btn_pegs_explore, delay=0.1, message=self.directory_file_pegs)
    self.btn_postpro_explore_tip = CTkToolTip(self.btn_postpro_explore, delay=0.1, message=self.directory_post_pro)
    self.btn_cluster_explore_tip = CTkToolTip(self.btn_cluster_explore, delay=0.1, message=self.directory_ini)
    self.btn_egsinp_file_open_tip = CTkToolTip(self.btn_egsinp_file_open, delay=0.1, message='Open file location')
    self.btn_msh_file_open_tip = CTkToolTip(self.btn_msh_file_open, delay=0.1, message='Open file location')
    self.btn_project_msh_file_open_tip = CTkToolTip(self.btn_project_msh_file_open, delay=0.1, message='Open file location')
    # Simulate Tab
    self.btn_ptracks_tip = CTkToolTip(self.btn_ptracks, delay=0.1,
                                      message="Run a shortened MevEGS simulation to verify\n"
                                              "source location relative to geometry")
    self.btn_run_mevegs_tip = CTkToolTip(self.btn_run_mevegs, delay=0.1,
                                         message="Run MevEGS simulation with the\n"
                                                 "the dedicated number of CPUs")
    self.btn_show_mevegs_progressbar_tip = CTkToolTip(self.btn_show_mevegs_progressbar, delay=0.1,
                                                      message="Select this after "
                                                              "initiating a local MevEGS simulation")
    self.btn_show_mevegs_jobs_tip = CTkToolTip(self.btn_show_mevegs_jobs, delay=0.1,
                                               message="Queries Windows processes for MevEGS.exe")
    self.btn_clean_up_tip = CTkToolTip(self.btn_clean_up, delay=0.1,
                                       message="Consolidates all project files in project\n"
                                               "folder after a successful simulation")
    self.btn_kill_mevegs_tip = CTkToolTip(self.btn_kill_mevegs, delay=0.1,
                                          message="Stops all Windows processes (MevEGS.exe)")
    self.btn_restore_mevegs_tip = CTkToolTip(self.btn_restore_mevegs, delay=0.1,
                                             message="Returns MevEGS HOME directory to default after\n "
                                                     "an error or aborted simulation")
    self.entry_njobs_tip = CTkToolTip(self.entry_njobs, delay=0.1, message="Should be a divisor of \'ncase\' "
                                                                           "located in the .egsinp file")
    # Cluster Tab
    self.btn_submit_2_tip = CTkToolTip(self.btn_submit_2, delay=0.1, message="SSH to Jericho and submit job files")
    self.btn_check_cluster_2_tip = CTkToolTip(self.btn_check_cluster_2, delay=0.1, message="Initiates cluster-side htopmon to check Jericho core usage")
    self.optionmenu_user_2_tip = CTkToolTip(self.optionmenu_user_2, delay=0.1, message="Username for SSH login to Jericho")
    self.btn_display_job_progress_2_tip = CTkToolTip(self.btn_display_job_progress_2, delay=0.1, message="Displays progress of *_w1.egslog file")
    self.btn_display_cluster_status_2_tip = CTkToolTip(self.btn_display_cluster_status_2, delay=0.1, message="Displays Jericho job-controller job queue")
    self.btn_show_job_list_2_tip = CTkToolTip(self.btn_show_job_list_2, delay=0.1, message="Displays job IDs of jobs "
                                                                                           "submitted:\nqueued, "
                                                                                           "running, and complete "
                                                                                           "(but still on cluster)")
    self.optionmenu_job_2_tip = CTkToolTip(self.optionmenu_job_2, delay=0.1, message="Choose job ID of job on cluster")
    self.btn_kill_2_tip = CTkToolTip(self.btn_kill_2, delay=0.1, message="Cancels chosen job then removes its files "
                                                                         "from the cluster")
    self.btn_retrieve_2_tip = CTkToolTip(self.btn_retrieve_2, delay=0.1, message="SSH to Jericho and retrieves ALL "
                                                                                 "completed jobs")
    self.btn_results_retrieve_2_tip = CTkToolTip(self.btn_results_retrieve_2, delay=0.1, message="Open directory " + self.directory_project)
    self.btn_process_phasespace_2_tip = CTkToolTip(self.btn_process_phasespace_2, delay=0.1, message="Uses beamdp.bat (option 11) to convert files to human-readable")
    self.lbl_results_header_3_tip = CTkToolTip(self.lbl_results_header_3, delay=0.1, message="Displays current .results.msh file")
    self.btn_load_gmshviews_3_tip = CTkToolTip(self.btn_load_gmshviews_3, delay=0.1, message="Refresh list of views in current project")
    self.btn_generate_views_3_tip = CTkToolTip(self.btn_generate_views_3, delay=0.1, message="Opens window to create views not included above")
    self.btn_export_views_3_tip = CTkToolTip(self.btn_export_views_3, delay=0.1, message="Opens window to export data in .csv format")
    self.menu_data_3_tip = CTkToolTip(self.menu_data_3, delay=0.1, message="Contains exported .csv files\nassociated with this project")
    self.btn_create_1d_ex_tip = CTkToolTip(self.btn_create_1d_ex, delay=0.1, message="Opens window to define line geometry\nthrough chosen exported data")
    self.btn_create_2d_ex_tip = CTkToolTip(self.btn_create_2d_ex, delay=0.1, message="Opens window to define plane geometry\nthrough chosen exported data")
    self.btn_create_1d_tip = CTkToolTip(self.btn_create_1d, delay=0.1, message="Opens window to define line geometry\nthrough chosen GMSH view")
    self.btn_create_2d_tip = CTkToolTip(self.btn_create_2d, delay=0.1, message="Opens window to define plane geometry\nthrough chosen GMSH view")

def update_hover_tooltips(self):
    # Input Tab
    self.btn_project_explore_tip.configure(message=self.directory_project + '\nOne simulation per project folder\n'
                                                                            'A main project folder can have many subfolders')
    self.btn_project_explore_new_tip.configure(message='Resets project and input files')
    self.btn_egsinp_explore_tip.configure(message=self.directory_file_egsinp)
    self.btn_egsinp_build_tip.configure(message='Under development')
    self.btn_mesh_explore_tip.configure(message=self.directory_file_msh)
    self.btn_results_mesh_explore_tip.configure(message=self.directory_file_project_msh)
    self.menu_source_1_tip.configure(message=self.directory_ini + 'Source_Phasespace_Files/')
    self.btn_mevegs_explore_tip.configure(message=self.directory_mevegs)
    self.btn_pegs_explore_tip.configure(message=self.directory_file_pegs)
    self.btn_postpro_explore_tip.configure(message=self.directory_post_pro)
    self.btn_cluster_explore_tip.configure(message=self.directory_ini)
    # Simulate Tab
    self.btn_ptracks_tip.configure(message="Run a shortened MevEGS simulation to verify\n"
                                           "source location relative to geometry")
    self.btn_run_mevegs_tip.configure(message="Run MevEGS simulation with the\nthe dedicated number of CPUs")
    self.btn_show_mevegs_progressbar_tip.configure(message="Select this after initiating a local MevEGS simulation")
    self.btn_show_mevegs_jobs_tip.configure(message="Queries Windows processes for MevEGS.exe")
    self.btn_clean_up_tip.configure(message="Consolidates all project files in project\n"
                                            "folder after a successful simulation")
    self.btn_kill_mevegs_tip.configure(message="Stops all Windows processes (MevEGS.exe)")
    self.btn_restore_mevegs_tip.configure(message="Returns MevEGS HOME directory to default after\n "
                                                  "an error or aborted simulation")
    self.entry_njobs_tip.configure(message="Should be a divisor of \'ncase\' "
                                                                           "located in the .egsinp file")
    # Cluster Tab
    self.btn_submit_2_tip.configure(message="SSH to Jericho and submit job files")
    self.btn_check_cluster_2_tip.configure(message="Initiates cluster-side htopmon to check Jericho core usage")
    self.optionmenu_user_2_tip.configure(message="Username for SSH login to Jericho")
    self.btn_display_job_progress_2_tip.configure(message="Displays progress of *_w1.egslog file")
    self.btn_display_cluster_status_2_tip.configure(message="Displays Jericho job-controller job queue")
    self.btn_show_job_list_2_tip.configure(message="Displays job IDs of jobs submitted:\nqueued, "
                                                   "running, and complete (but still on cluster)")
    self.optionmenu_job_2_tip.configure(message="Choose job ID of job on cluster")
    self.btn_kill_2_tip.configure(message="Cancels chosen job then removes its files from the cluster")
    self.btn_retrieve_2_tip.configure(message="SSH to Jericho and retrieves ALL completed jobs")
    self.btn_results_retrieve_2_tip.configure(message="Open directory " + self.directory_project)
    self.btn_process_phasespace_2_tip.configure(message="Uses beamdp.bat (option 11) to convert files to human-readable")
    self.lbl_results_header_3_tip.configure(message="Displays current .results.msh file")
    self.btn_load_gmshviews_3_tip.configure(message="Button may not be necessary...")
    self.btn_generate_views_3_tip.configure(message="Opens window to create views not included above")
    self.btn_export_views_3_tip.configure(message="Opens window to export data in .csv format")
    self.menu_data_3_tip.configure(message="Contains exported .csv files\nassociated with this project")
    self.btn_create_1d_ex_tip.configure(message="Opens window to define line geometry\nthrough chosen exported data")
    self.btn_create_2d_ex_tip.configure(message="Opens window to define plane geometry\nthrough chosen exported data")
    self.btn_create_1d_tip.configure(message="Opens window to define line geometry\nthrough chosen GMSH view")
    self.btn_create_2d_tip.configure(message="Opens window to define plane geometry\nthrough chosen GMSH view")

def update_phasespace_warning_label(self):
    self.phasespace_warning_2.configure(text='\'Retrieve all\' downloads all available\n'
                                             'simulations to sub-folders of your\n'
                                             'project to four digit folder names\n   /'
                                             + os.path.basename(os.path.dirname(self.directory_project)) + '/####/\n'
                                               'You must change the \'.results.msh\'\n'
                                               '(directory path)\' in the \n'
                                               '\'Source Files\' tab to the\n'
                                               'correct directory before processing\n'
                                               'phase-space files and using the\n'
                                               '\'Post Process\' tab')

def one_d_generation_export(self):
    file_name = self.menu_data_3.get()
    data_type = file_name.split('_')[0]
    dataframe = pd.read_csv(self.directory_project + '/exports/' + file_name, sep=',', names=['x', 'y', 'z', data_type],
                            usecols=[0, 1, 2, 3])
    xmin = str(np.floor(dataframe['x'].min()))
    xmax = str(np.ceil(dataframe['x'].max()))
    ymin = str(np.floor(dataframe['y'].min()))
    ymax = str(np.ceil(dataframe['y'].max()))
    zmin = str(np.floor(dataframe['z'].min()))
    zmax = str(np.ceil(dataframe['z'].max()))
    self.topframe = ctk.CTkToplevel(self.gui)
    # self.topframe.grab_set()
    # self.topframe.geometry("600x700")
    self.topframe.attributes('-topmost', True)
    self.topframe.geometry("+0+0")
    self.topframe.focus()
    self.topframe.title('1D Coordinates - ' + file_name)
    self.topframe.update()
    self.lbl_create_figs_tf = ctk.CTkLabel(self.topframe, text="Enter start- and end-points",
                                           font=('Helvetica', 16, 'bold'), justify='center')
    self.lbl_create_figs_tf.grid(column=0, row=0, padx=5, pady=5, columnspan=4)

    self.lbl_x0_tf = ctk.CTkLabel(self.topframe, text="X0 ("+xmin+" to "+xmax+")", font=('Helvetica', 12, 'normal'))
    self.lbl_x0_tf.grid(column=0, row=1, padx=(5, 0), pady=5, sticky='e')
    self.lbl_y0_tf = ctk.CTkLabel(self.topframe, text="Y0 ("+ymin+" to "+ymax+")", font=('Helvetica', 12, 'normal'))
    self.lbl_y0_tf.grid(column=0, row=2, padx=(5, 0), pady=5, sticky='e')
    self.lbl_z0_tf = ctk.CTkLabel(self.topframe, text="Z0 ("+zmin+" to "+zmax+")", font=('Helvetica', 12, 'normal'))
    self.lbl_z0_tf.grid(column=0, row=3, padx=(5, 0), pady=5, sticky='e')
    self.lbl_x1_tf = ctk.CTkLabel(self.topframe, text="X1 ("+xmin+" to "+xmax+")", font=('Helvetica', 12, 'normal'))
    self.lbl_x1_tf.grid(column=2, row=1, padx=(5, 0), pady=5, sticky='e')
    self.lbl_y1_tf = ctk.CTkLabel(self.topframe, text="Y1 ("+ymin+" to "+ymax+")", font=('Helvetica', 12, 'normal'))
    self.lbl_y1_tf.grid(column=2, row=2, padx=(5, 0), pady=5, sticky='e')
    self.lbl_z1_tf = ctk.CTkLabel(self.topframe, text="Z1 ("+zmin+" to "+zmax+")", font=('Helvetica', 12, 'normal'))
    self.lbl_z1_tf.grid(column=2, row=3, padx=(5, 0), pady=5, sticky='e')

    self.x0_entry = ctk.CTkEntry(self.topframe, width=60)
    self.x0_entry.grid(column=1, row=1, padx=(0, 5), pady=5, sticky='w')
    self.y0_entry = ctk.CTkEntry(self.topframe, width=60)
    self.y0_entry.grid(column=1, row=2, padx=(0, 5), pady=5, sticky='w')
    self.z0_entry = ctk.CTkEntry(self.topframe, width=60)
    self.z0_entry.grid(column=1, row=3, padx=(0, 5), pady=5, sticky='w')
    self.x1_entry = ctk.CTkEntry(self.topframe, width=60)
    self.x1_entry.grid(column=3, row=1, padx=(0, 5), pady=5, sticky='w')
    self.y1_entry = ctk.CTkEntry(self.topframe, width=60)
    self.y1_entry.grid(column=3, row=2, padx=(0, 5), pady=5, sticky='w')
    self.z1_entry = ctk.CTkEntry(self.topframe, width=60)
    self.z1_entry.grid(column=3, row=3, padx=(0, 5), pady=5, sticky='w')
    self.num_points_entry_3 = ctk.CTkEntry(self.topframe, width=60)
    self.num_points_entry_3.grid(column=3, row=4, padx=(0, 5), pady=5, sticky='w')

    self.btn_make_fig = ctk.CTkButton(self.topframe, text='Plot Figure',
                                      command=lambda: one_d_generate_export_figure(self, dataframe, file_name,
                                                                                 float(self.x0_entry.get()),
                                                                                 float(self.y0_entry.get()),
                                                                                 float(self.z0_entry.get()),
                                                                                 float(self.x1_entry.get()),
                                                                                 float(self.y1_entry.get()),
                                                                                 float(self.z1_entry.get())))
    self.btn_make_fig.grid(column=0, row=20, pady=5, padx=5, sticky='nesw', columnspan=2)
    self.exit_button_tf = ctk.CTkButton(self.topframe, text='Exit', command=lambda: [self.btn_exit_popup()])
    self.exit_button_tf.grid(column=2, row=20, pady=5, padx=5, sticky='nesw', columnspan=2)


def one_d_generate_export_figure(self, dataframe, file_name, x0, y0, z0, x1, y1, z1):
    ...


def two_d_generation_export(self):
    ...


def two_d_generate_export_figure(self):
    ...
