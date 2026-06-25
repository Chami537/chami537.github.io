@echo off
cd /d "%~dp0"
python -c "import manage_launcher; manage_launcher.run()"
pause
