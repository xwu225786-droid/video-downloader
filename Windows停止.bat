@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0VoxPull\scripts\manage-windows.ps1" -Action stop
set "result=%errorlevel%"
if not "%result%"=="0" echo Operation failed. See the message above.
pause
exit /b %result%
