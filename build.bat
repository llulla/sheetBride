@echo off
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --windowed --name SheetBride app.py
echo Done. See dist\SheetBride.exe
