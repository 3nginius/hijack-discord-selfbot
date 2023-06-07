@echo off
echo Installing necessary Python packages...
python -m pip install --upgrade pip
python -m pip install websockets
python -m pip install praw
python -m pip install requests
python -m pip install pywebview
echo Done!
pause
