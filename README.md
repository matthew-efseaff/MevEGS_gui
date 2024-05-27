# MevEGS_gui
Wrapper for controlling the various inputs and outputs for MevEGS

README for MevEGS app/gui/program - (added to github after v005 development wrapped up)

'''
Initial Notes:
    This project has, along with the project structure, been hacked together with not enough thought... but it 'works'. 

REQUIREMENTS:

* Windows
    - Many Windows-only imports used, not cross-platform tested
* Python 3
* The Gmsh Python SDK >= v4.12 ? (developed with v4.12, Gmsh must have gmsh.view.getHomogeneousModelData which was added in v4.6 or v4.7)
* 'new' ptracks.py (in a directory called 'Post_Processing', which resides in same directory as MevEGS_gui.py)
    - 'new' ptracks.py has method/function process_ptracks()
* addphsp.exe (hidden in HEN_HOUSE/bin/mevegs/
* beampd.bat (in previously mentioned post_processing directory) - possible to change particle max quantity to suit
* import statement modules
    - CTkXYFrame included here in same folder as README.txt
        - Originally sourced from https://github.com/Akascape/CTkXYFrame)
        - CTkXYFrame folder must reside in same directory as 'MevEGS_gui.py'


STRUCTURE:

'/EGS_HOME / mevegs "home" ' directory: 
                 - permanently contains .pegs4dat, mevegs.cpp (and entourage)
                 - temporarily will contain copied input and output files 

'GUI Home' directory (can be located anywhere)
           |     - contains MevEGS_gui.py, "MevEGS_gui_utils.py, "MevEGS_gui_utils_cluster.py, mevegs_app.ini (.ini shows up on program exit),
           |        local_job_submission.bat, local_job_retrieve.bat, cluster_perf_mon_htop.bat (these need to be updated to include FQDN (fully qualified domain names) 'username'@jericho-jobctrl.mevex.local)
           |     - temporarily will contain various GUI files
           |
           |_    + 'Post_Processing' directory: contains beampd.bat, ptracks.py (changes made to the name 'Post_Processing'  
           |        can be made in the import statements)
           |_    + 'CTkXYFrame' directory: ensures that content doesn't spill outside viewable GUI
           |
           |_    + 'Source_Phasespace_Files' directory: contains library of phasespace sources (needs encryption)
           |
           |     + Extra (unnecessary) .json color themes were added. If you want them they need to be stored in your Python customtkinter 'theme' folder. MDE's path looked like this--> C:\Users\Matthew_Efseaff\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages\customtkinter\assets\themes
           |        
           |

Project files (storage for .egsinp and .msh inputs as well as simulation results) should not be buried too deep otherwise the path/filename combo could exceed system limits (Windows < 260 char)


NOTES

    * .egsinp file:
        scaling = ## line can't have any '#' comment after the factor
    * Phasespace handling is broken AFAIK
'''
