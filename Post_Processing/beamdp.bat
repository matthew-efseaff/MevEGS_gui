@echo off
setlocal EnableDelayedExpansion

(echo n
echo 11
echo 1,1000000000,2
echo %1)|beamdp.exe > %1.txt