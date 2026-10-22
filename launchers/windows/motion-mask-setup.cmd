@echo off
cd /d "%~dp0"
motion-mask.exe --setup
if errorlevel 1 pause