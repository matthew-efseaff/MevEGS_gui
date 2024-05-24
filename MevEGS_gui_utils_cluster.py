#!/usr/bin/env python
# coding: utf-8

import os
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
    os.chdir(self.directory_ini)
    file_source = self.menu_source_1.get()
    if file_source in ('', 'Choose source', 'None', 'NaN'):
        command = 'local_job_submission ' + file_egsinp + ' ' + file_msh
    else:
        shutil.copy2(self.directory_ini + 'Source_Phasespace_Files/' + self.menu_source_1.get(), self.directory_ini)
        _, file_source = os.path.split(self.directory_ini + self.menu_source_1.get())
        command = 'local_job_submission ' + file_egsinp + ' ' + file_msh + ' ' + file_source
    job_file_name = 'mevegs_cluster_console_output_1.mvgs'
    if os.path.isfile(self.directory_ini + self.menu_source_1.get()):
        utils.write_to_console_log(self, "Mevegs:\t\tPhase-space file: " + str(self.directory_ini + self.menu_source_1.get()) + " included")
    with open(job_file_name, "w") as f:
        process = subprocess.Popen(['cmd', '/c', command], stdout=f, stderr=subprocess.STDOUT, bufsize=0)
    while process.poll() is None:
        utils.write_to_console_log(self, 'MevEGS:\t\tSending job to cluster')
        time.sleep(2)
    # launch performance monitor
    # if os.path.isfile(self.directory_ini + 'cluster_perf_mon_htop.bat'):
    #     subprocess.Popen(['cmd', '/c', 'cluster_perf_mon_htop.bat'])
    # time.sleep(2)

    # rename, read console output
    # try:
    #     f_ = open(self.directory_ini + job_file_name, 'r')
    #     last_lines = f_.readlines()[-1]
    #     job_id = last_lines.split(' ')[-1].split('\n')[0]
    #     f_.close()
    # except IndexError:
    #     time.sleep(5)
    # try:
    #     f_ = open(self.directory_ini + job_file_name, 'r')
    #     last_lines = f_.readlines()[-1]
    #     job_id = last_lines.split(' ')[-1].split('\n')[0]
    #     f_.close()
    # except IndexError:
    #     time.sleep(5)
    f_ = open(self.directory_ini + job_file_name, 'r')
    last_lines = f_.readlines()[-1]
    job_id = last_lines.split(' ')[-1].split('\n')[0]
    f_.close()
    f1 = open(self.directory_ini + job_file_name, 'w')
    f1.write('\n' + str(self.directory_file_egsinp) + '\n' + str(self.directory_file_msh) + '\n')
    f1.close()
    shutil.copy2(job_file_name, job_id + '.txt')
    os.remove(job_file_name)
    # delete files
    os.remove(self.directory_ini + file_egsinp)
    os.remove(self.directory_ini + file_msh)
    if os.path.isfile(self.directory_ini + file_source):
        os.remove(self.directory_ini + file_source)
    btn_show_job_list_clicked_2(self)
    if self.optionmenu_user_2.get() != 'Choose':
        btn_display_cluster_status_clicked_2(self, self.optionmenu_user_2.get())


def btn_check_cluster_status_clicked(self):
    os.chdir(self.directory_ini)
    if os.path.isfile(self.directory_ini + 'cluster_perf_mon_htop.bat'):
        subprocess.Popen(['cmd', '/c', 'cluster_perf_mon_htop.bat'])


def btn_retrieve_cluster_jobs_clicked(self):
    shutil.copy2(self.directory_ini + 'local_job_retrieve.bat', self.directory_project)
    os.chdir(self.directory_project)
    command = 'local_job_retrieve.bat'
    process = subprocess.Popen(['cmd', '/c', command], stdout=subprocess.PIPE)  # , bufsize=1, universal_newlines=True)
    while process.poll() is None:
        utils.write_to_console_log(self, 'Cluster:\t\tDownloading files from the cluster')
        time.sleep(5)
    time.sleep(1)
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
    directory_project = self.directory_project + 'phase_space_files/'
    items_phase_space = glob.glob(self.directory_project + '*.egsphsp1', recursive=False)
    for i in items_phase_space:
        os.replace(i, directory_project + os.path.basename(i))
    phsp_filenames = []
    for fname in os.listdir(directory_project):  # gets list of filenames
        if '.egsphsp1' in fname:
            phsp_filenames.append(os.path.basename(fname).split('.egsphsp1')[0])
    # Convert to human-readable, hardcoded beamdp option 11
    # move beamdp.bat to working dir
    shutil.copy2(self.directory_post_pro + 'beamdp.bat', directory_project)
    time.sleep(5)
    os.chdir(directory_project)  # navigate to beamdp.bat new 'home' temporarily
    print(os.getcwd())
    progress_read = []
    if os.path.isfile(directory_project + 'beamdp.bat') and os.path.isfile(directory_project + phsp_filenames[0] + '.egsphsp1'):
        for j in range(len(phsp_filenames)):
            print(directory_project + 'beamdp.bat', directory_project + phsp_filenames[j] + '.egsphsp1')
            # command2 = 'echo %PATH%'
            # command1 = "set PATH=%PATH%"  #;C:/Mevegs_local/HEN_HOUSE/bin/win3264/"
            command2 = "beamdp.bat " + phsp_filenames[j] + ".egsphsp1"
            # command1 = "set PATH=%PATH%;C:/Mevegs_local/HEN_HOUSE/bin/win3264/"  # ;' + 'cmd /c beamdp.bat ' + phsp_filenames[j] + '.egsphsp1'
            # directory_project + 'beamdp.bat', phsp_filenames[j] + ".egsphsp1"
            # python_ = subprocess.run(["cmd", '/c', 'echo %PATH%'])
            # print(command)
            # print(os.environ)
            # subprocess.Popen(['cmd', '/k', command1])
            progress_read.append(subprocess.Popen(['cmd', '/c', command2]))  # 'cmd', '/c',
            # command2 = "set PATH=%PATH%;C:/Mevegs_local/HEN_HOUSE/bin/win3264/&& echo %PATH%&& beamdp.bat " + phsp_filenames[j] + ".egsphsp1"
            # progress_read.append(subprocess.Popen([command1], shell=True))
            # command2 = "set PATH=%PATH%;C:/Mevegs_local/HEN_HOUSE/bin/win3264/&& echo %PATH%"
            # progress_read.append(subprocess.Popen(['cmd', '/V', '/c', com]))
            # progress_read.append(subprocess.Popen(['cmd', '/c', command1], env=dict(os.environ, PATH="path")))
            print(progress_read[j].args)
            # cmd2 = str(
            #     'ssh ' + username + '@192.168.105.105 \"cd electron-gamma-shower/egs_home/mevegs; ./cleanup.sh; \\rm *.egsinp; \\rm *.msh\"')  # @jericho-jobctrl.mevex.local
            # subprocess.Popen(cmd2)
    time.sleep(5)
    for i in range(len(phsp_filenames)):
        while progress_read[i].poll() is None:
            utils.write_to_console_log(self, 'MevEGS:\t\tPreparing human readable phase space files ' + str(i + 1) + '...')
            # print('Preparing human readable phase space files ', str(i + 1), '...')
            time.sleep(10)
    utils.write_to_console_log(self, 'MevEGS:\t\tReadable particle phase space files saved in:\n' + directory_project)
    # delete beamdp.bat
    # os.remove(directory_project + 'beamdp.bat')
    # for i in range(len(phsp_filenames)):
    #     if os.path.isfile(directory_project + phsp_filenames[i] + '.egsphsp1'):
    #         shutil.move(directory_project + phsp_filenames[i] + '.egsphsp1', self.directory_project)
    # items_egsphsp1 = glob.glob(directory_project + '*.egsphsp1', recursive=False)
    # for object_ in items_egsphsp1:
    #     if os.path.isfile(object_):
    #         os.remove(object_)  # Don't need .egsphsp1 files anymore - memory/storage savings
    # os.chdir(self.directory_mevegs)  # back to mevegs home


def btn_kill_cluster_jobs_clicked(self, username, job_id):
    # cmd1 = str("ssh "+username+"@192.168.105.105 scancel "+job_id)  # MDE@jericho-jobctrl.mevex.local
    cmd1 = str("ssh " + username + "@jericho-jobctrl.mevex.local scancel " + job_id)
    if username == 'Choose' or job_id == 'Job number' or job_id == 'None':
        display_queue = 'Missing Job number or username'
        utils.write_to_console_log(self, 'MevEGS:\t\t' + display_queue)
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
        cmd1 = str('scp -r MDE@jericho-jobctrl.mevex.local:/home/'+username+'/electron-gamma-shower/egs_home/mevegs/*/*_w1.egslog ./')  # .mevex.local
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
        log = 'Cluster:\t\tChoose cluster username'
    # self.lbl_display_queue_2.configure(text=log)
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
