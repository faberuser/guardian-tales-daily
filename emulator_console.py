import logging
from json import load
from os import getcwd, path, listdir
from subprocess import run as terminal
from threading import Thread

logging.basicConfig(
    handlers=[logging.FileHandler("./.cache/log.log", "a", "utf-8")],
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)

def log(text):
    logging.info(text)
    print(text)

with open('./config.json') as j:
    config = load(j)


def ld_console(command):
    ldconsole_path = config['emulator']
    return terminal(ldconsole_path + ' ' + command, capture_output=True).stdout.decode('utf-8')

def ld_launch(index):
    result = ld_console('launch --index ' + str(index))
    if result+'/' == """b"player don't exist!"/""":
        log('Emulator with index ' + str(index) + " doesn't exist")
    else:
        log('Launched emulator with index ' + str(index))


def nox_console(command):
    noxconsole_path = config['emulator']
    devices = config['devices']
    if command == 'quitall':
        for device in devices:
            terminal(noxconsole_path + ' -clone:Nox_' + str(device) + ' -quit')
        return
    return terminal(noxconsole_path + ' ' + command, capture_output=True).stdout.decode('utf-8')

def nox_launch(index):
    thread = Thread(target=nox_console, args=('-clone:Nox_' + str(index),)) # Launching a Nox instance freeze a whole process so we need threading to split the process out
    thread.start()
    log('Launched emulator with index ' + str(index))

if 'ldconsole.exe' in config['emulator']:
    if path.exists('"'+getcwd()+'\\adb.exe" '):
        adb_dir = '"'+getcwd()+'\\adb.exe" '
    else:
        for item in listdir(getcwd()+'\\.cache\\tmp'):
            if "_MEI" in item:
                adb_dir = '"'+getcwd()+'\\.cache\\tmp\\'+item+'\\adb.exe" '
                break
    console = ld_console
    launch = ld_launch
elif 'Nox.exe' in config['emulator']:
    if path.exists('"'+getcwd()+'\\nox_adb.exe" '):
        adb_dir = '"'+getcwd()+'\\nox_adb.exe" '
    else:
        for item in listdir(getcwd()+'\\.cache\\tmp'):
            if "_MEI" in item:
                adb_dir = '"'+getcwd()+'\\.cache\\tmp\\'+item+'\\nox_adb.exe" '
                break
    console = nox_console
    launch = nox_launch