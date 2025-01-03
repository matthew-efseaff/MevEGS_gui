#!/usr/bin/env python
# coding: utf-8

import os
import re
import shutil
import time
import subprocess
import glob
import MevEGS_gui_utils as utils
import customtkinter as ctk


def btn_submit_cluster_jobs_clicked(self):
    shutil.copy2(self.directory_file_egsinp, self.directory_ini)
    _, file_egsinp = os.path.split(self.directory_file_egsinp)
    shutil.copy2(self.directory_file_msh, self.directory_ini)
    _, file_msh = os.path.split(self.directory_file_msh)
    # Below code reads egsinp to find 'phase space file'. This file then must be in the project directory with the egsinp so that it can be copied to the mevegs 'home'/cluster for simulation
    source_file = str()
    phase_space_file_check = str()
    stripped_source_file = str()
    with open(self.directory_file_egsinp, "r") as f:
        for line in f:
            if re.search('phase space file', line):
                phase_space_file_check = line
                source_file = line.split('=')[1]
                stripped_source_file = source_file.strip()
                break
    if phase_space_file_check and source_file == '':
        utils.write_to_console_log(self,
                                   'Either the phase space source file is not in the project directory,'
                                   ' or the phase space file does not follow the convention: '
                                   'phase space file = filename.egsphsp1.txt or filename.txt')
    if stripped_source_file and phase_space_file_check:
        if not os.path.isfile(self.directory_project + stripped_source_file):
            utils.write_to_console_log(self,
                                       'Phase space source requested in .egsinp file is not in project directory')
    # host = str("ssh " + self.username + "@jericho-jobctrl.mevex.local test -f /electron-gamma-shower/egs_home/mevegs/"
    #            + stripped_source_file)
    # if subprocess.Popen(host):
    #     self.topframe = ctk.CTkToplevel(self.gui)
    #     self.topframe.grab_set()
    #     self.topframe.geometry("700x300")
    #     self.topframe.attributes('-topmost', True)
    #     self.topframe.update()
    #     self.topframe.focus()
    #     self.topframe.title('Overwrite?')
    #     self.topframe.grid_columnconfigure(0, weight=1)
    #     self.topframe.grid_columnconfigure(1, weight=1)
    #     self.topframe.grid_rowconfigure(0, weight=1)
    #     self.topframe.grid_rowconfigure(1, weight=1)
    #     self.warning = ctk.CTkLabel(self.topframe, font=("Arial", 20),
    #                                 text='Phasespace source exists on the cluster. Would you like to overwrite it?')
    #     self.warning.grid(column=0, row=0, pady=10, padx=10, columnspan=3, sticky='nsew')
    #     self.yes_button = ctk.CTkButton(self.topframe, text='Yes, continue', command=lambda: [])
    #     self.yes_button.grid(column=0, row=1, pady=10, padx=10, sticky='nesw')
    #     self.exit_button = ctk.CTkButton(master=self.topframe, text='No, cancel',
    #                                      command=lambda: [self.btn_exit_popup()])
    #     self.exit_button.grid(column=1, row=1, pady=10, padx=10, sticky='nesw')

    if os.path.isfile(self.directory_project + stripped_source_file):
        shutil.copy2(self.directory_project + stripped_source_file, self.directory_ini)
    elif not phase_space_file_check:
        utils.write_to_console_log(self, 'No phase space source requested in .egsinp file')
    time.sleep(3)  # to let things copy... big things
    os.chdir(self.directory_ini)

    if not os.path.isfile(self.directory_ini + stripped_source_file):
        command = 'local_job_submission_phasespace ' + file_egsinp + ' ' + file_msh
    else:
        _, file_source = os.path.split(self.directory_ini + stripped_source_file)
        command = 'local_job_submission_phasespace ' + file_egsinp + ' ' + file_msh + ' ' + file_source
    job_file_name = 'mevegs_cluster_console_output_1.mvgs'
    with open(job_file_name, "w") as f:
        process = subprocess.Popen(['cmd', '/c', command], stdout=f, stderr=subprocess.STDOUT, bufsize=0)
    utils.write_to_console_log(self, 'MEVEGS:\t\tSending job to cluster')
    while process.poll() is None:
        time.sleep(5)
    f_ = open(self.directory_ini + job_file_name, 'r')
    last_lines = f_.readlines()[-1]
    job_id = last_lines.split(' ')[-1].split('\n')[0]
    f_.close()
    f1 = open(self.directory_ini + job_file_name, 'a')
    f1.write(str(self.directory_file_egsinp) + '\n' + str(self.directory_file_msh) + '\n')
    f1.close()
    shutil.copy2(job_file_name, job_id + '.txt')
    os.remove(job_file_name)
    # delete files
    os.remove(self.directory_ini + file_egsinp)
    os.remove(self.directory_ini + file_msh)
    if os.path.isfile(self.directory_ini + file_source):
        os.remove(self.directory_ini + file_source)
    btn_show_job_list_clicked_2(self)
    if self.username != 'Choose':
        btn_display_cluster_status_clicked_2(self, self.username)
    os.chdir(self.directory_ini)


def btn_check_cluster_status_clicked(self):
    os.chdir(self.directory_ini)
    if os.path.isfile(self.directory_ini + 'cluster_perf_mon_htop.bat'):
        subprocess.Popen(['cmd', '/c', 'cluster_perf_mon_htop.bat'])


def btn_retrieve_cluster_jobs_clicked(self):
    shutil.copy2(self.directory_ini + 'local_job_retrieve.bat', self.directory_project)
    os.chdir(self.directory_project)
    command = 'local_job_retrieve.bat'
    process = subprocess.Popen(['cmd', '/c', command], stdout=subprocess.PIPE)  # , bufsize=1, universal_newlines=True)
    if process.poll() is None:
        utils.write_to_console_log(self, 'Cluster:\t\tDownloading files from the cluster')
        time.sleep(10)
    while process.poll() is None:
        # utils.write_to_console_log(self, 'Cluster:\t\tDownloading files from the cluster')
        time.sleep(2)
    # time.sleep(1)
    # delete file
    os.remove(self.directory_project + 'local_job_retrieve.bat')
    os.chdir(self.directory_ini)
    # REMOVE ALL JOB XXXX.txt files
    items_txt = glob.glob(self.directory_ini + '/[0-9][0-9][0-9][0-9].txt', recursive=False)
    for object_ in items_txt:
        if os.path.isfile(object_):
            os.remove(object_)
    modify_msh_results_msh_extension(self)
    btn_show_job_list_clicked_2(self)


def process_cluster_phase_space(self):
    os.makedirs(self.directory_project + 'phase_space_files/', exist_ok=True)
    phsp_filenames = []
    for fname in os.listdir(self.directory_project):
        if '.egsphsp1' in fname:
            phsp_filenames.append(os.path.basename(fname).split('.egsphsp1')[0])
    # print(phsp_filenames)
    process_cluster_human_phase_space_files(self, phsp_filenames)


def process_cluster_human_phase_space_files(self, phsp_filenames):
    os.chdir(self.directory_project + 'phase_space_files/')
    utils.write_to_console_log(self, "MEVEGS:\t\tPreparing human readable phase space files...")
    # Convert to human-readable, hardcoded beamdp option 11
    # move beamdp.bat to working dir
    shutil.copy2(self.directory_ini + 'beamdp.bat', self.directory_project + 'phase_space_files/')
    for file in phsp_filenames:
        shutil.move(self.directory_project + file + '.egsphsp1', self.directory_project + 'phase_space_files/')
    progress_read = []
    for j in range(len(phsp_filenames)):
        command = 'beamdp.bat ' + phsp_filenames[j] + '.egsphsp1'
        error_file_name = phsp_filenames[j] + '_console_log.mvgs'
        with open(error_file_name, 'w') as f:
            progress_read.append(
                subprocess.Popen(['cmd', '/c', command], stdout=f, stderr=subprocess.STDOUT, bufsize=0))
    for i in range(len(phsp_filenames)):
        utils.write_to_console_log(self, "MEVEGS:\t\tPreparing human readable phase space files " + str(i + 1) + '...')
        while progress_read[i].poll() is None:
            time.sleep(1)
    utils.write_to_console_log(self, "MEVEGS:\t\tReadable particle phase space files saved in: " + self.directory_project + 'phase_space_files/')
    # delete beamdp.bat
    os.remove(self.directory_project + 'phase_space_files/beamdp.bat')
    os.chdir(self.directory_ini)  # back to home


def btn_kill_cluster_jobs_clicked(self, username, job_id):
    # cmd1 = str("ssh "+username+"@192.168.105.105 scancel "+job_id)  # MDE@jericho-jobctrl.mevex.local
    cmd1 = str("ssh " + username + "@jericho-jobctrl.mevex.local scancel " + job_id)
    if username == 'Choose' or job_id == 'Job number' or job_id == 'None':
        display_queue = 'Missing Job number or username'
        utils.write_to_console_log(self, 'MEVEGS:\t\t' + display_queue)
        # self.lbl_display_queue_2.configure(text=display_queue)
        self.frame_2.update_idletasks()
        return
    else:
        final = subprocess.Popen("{}".format(cmd1), shell=True, stdin=subprocess.PIPE,
                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True, universal_newlines=True)
        stdout, nothing = final.communicate()
        log = open('cluster_log.txt', 'w')
        log.write(stdout)
        log.close()
        items_txt = glob.glob(self.directory_ini + job_id + '.txt', recursive=False)
        for object_ in items_txt:
            if os.path.isfile(object_):
                os.remove(object_)
        btn_show_job_list_clicked_2(self)
        os.remove(self.directory_ini + 'cluster_log.txt')
    if username != 'Choose' and job_id != 'Job number' and job_id != 'None':
        cmd2 = str('ssh '+username+'@jericho-jobctrl.mevex.local \"cd electron-gamma-shower/egs_home/mevegs; ./cleanup.sh; \\rm *.egsinp; \\rm *.msh\"')
        subprocess.Popen(cmd2)
        # cmd3 = str('ssh '+username+'@192.168.105.105 \"cd electron-gamma-shower/egs_home/mevegs; \\rm *.egsinp; \\rm *.msh\"')


def btn_show_job_list_clicked_2(self):
    items_txt = glob.glob(self.directory_ini + '/[0-9][0-9][0-9][0-9].txt', recursive=False)
    job_list = []
    new_object_ = ''
    for object_ in items_txt:
        string_parts = os.path.basename(object_).split('.')[0]
        job_list.append(string_parts)
        new_object_ = ', '.join(job_list)
    # self.lbl_display_job_2.configure(text=new_object_)
    utils.write_to_console_log(self, 'Cluster:\t\tJobs on the cluster - ' + new_object_)
    if not job_list:
        job = ctk.StringVar()
        job.set('None')
        self.optionmenu_job_2.configure(variable=job)
    else:
        self.optionmenu_job_2.configure(values=job_list)
    self.frame_2.update_idletasks()


def btn_display_cluster_status_clicked_2(self, username):
    # cmd1 = str("ssh " + username + "@192.168.105.105 squeue")  # MDE@jericho-jobctrl.mevex.local
    cmd1 = str("ssh " + username + "@jericho-jobctrl.mevex.local squeue")
    if username == 'Choose':
        display_queue = 'Choose cluster username'
    else:
        final = subprocess.Popen("{}".format(cmd1), shell=True, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True, universal_newlines=True)
        stdout, _ = final.communicate()
        log = open('cluster_queue.txt', 'w')
        log.write(stdout)
        log.close()
        queue_info = []
        with open('cluster_queue.txt', 'r') as myfile:
            for line in myfile:
                queue_info.append(line)
        display_queue = '\n'.join(queue_info)
        os.remove(self.directory_ini + 'cluster_queue.txt')
    # self.lbl_display_queue_2.configure(text=display_queue)
    utils.write_to_console_log(self, 'Cluster:\n' + display_queue)
    self.frame_2.update_idletasks()


def btn_display_cluster_log_file_clicked_2(self, username):
    os.chdir(self.directory_ini)
    _, file_egsinp = os.path.split(self.directory_file_egsinp)
    egsinp_ = file_egsinp.split('.egsinp')[0]
    if username != 'Choose':
        cmd1 = str('scp '+username+'@jericho-jobctrl.mevex.local:/home/'+username+'/electron-gamma-shower/egs_home/mevegs/egsrun_*/*_w1.egslog ./')  # .mevex.local
        process = subprocess.Popen(cmd1)
        process.wait()
        log_info = []
        if os.path.isfile(self.directory_ini + egsinp_+'_w1.egslog'):
            with open(egsinp_+'_w1.egslog', 'r') as myfile:
                for line in myfile:
                    log_info.append(line)
            log_info = log_info[-5:]
            log = '\n'.join(log_info)
        else:
            log = 'Cluster:\t\tThe ' + file_egsinp + ' job is not in progress. It may not have started or it may be complete'
    else:
        log = 'Cluster:\t\tChoose cluster username [File menu, Initial configuration wizard]'
    utils.write_to_console_log(self, log)
    utils.write_to_console_log(self, 'Cluster:\t\tProgress output from _w1.egslog file')
    # DELETE FILE
    if os.path.isfile(self.directory_ini + egsinp_ + '_w1.egslog'):
        os.remove(self.directory_ini + egsinp_ + '_w1.egslog')


def modify_msh_results_msh_extension(self):
    items_msh_results_msh = glob.glob(self.directory_project + '**/*.msh.results.msh', recursive=True)
    for object_ in items_msh_results_msh:  # renaming .msh.results.msh files
        if os.path.isfile(object_):
            string_parts = object_.split('.')[:-3]
            new_object_ = '.'.join(string_parts) + '.results.msh'
            os.replace(object_, new_object_)
    self.btn_project_explore.configure(text=os.path.basename(os.path.dirname(self.directory_project)))
    self.gui.update_idletasks()
