@echo off
rem Local script to send job to mevegs cluster (jericho-jobctrl)

rem scp source target
scp %1 %2 %3 MDE@jericho-jobctrl.mevex.local:/home/MDE/electron-gamma-shower/egs_home/mevegs/
ssh MDE@jericho-jobctrl.mevex.local sbatch ./cluster_job_submission_w_cleanup_phase_space.sh %1 %2 %3