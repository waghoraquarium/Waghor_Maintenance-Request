@echo off
chcp 65001 >nul
REM === Waghor Auto-Print Agent ===
cd /d "%~dp0"
start /min "" "C:\Users\Naity\AppData\Local\Python\pythoncore-3.15-64\pythonw.exe" "%~dp0waghor_print_agent.py"
