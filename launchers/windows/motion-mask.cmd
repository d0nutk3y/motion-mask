@echo off
cd /d "%~dp0"
motion-mask.exe
if errorlevel 1 pause