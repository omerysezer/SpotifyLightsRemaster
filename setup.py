import subprocess

subprocess.run('sudo apt-get update && sudo apt-get upgrade'.split(' '))
subprocess.run('sudo apt install python3-pyqt5'.split(' '))
subprocess.run('sudo pip3 install -r requirements.txt'.split(' '))

