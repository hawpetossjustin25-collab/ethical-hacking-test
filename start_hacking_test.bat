@echo off
cd /d "%~dp0"
python -c "import PyQt6" 2>nul || python -m pip install --user PyQt6
start "" pythonw -m ethical_hacking_test
