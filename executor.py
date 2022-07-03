import logging
from json import load
from time import sleep, time
from os import system
from math import ceil
from subprocess import run as terminal
from threading import Thread

from modules import Executor
from emulator_console import adb_dir, console, launch


logging.basicConfig(
    handlers=[logging.FileHandler("./.cache/log.log", "a", "utf-8")],
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)

def log(text):
    logging.info(text)
    print(text)


def load_devices():
    log('Loading emulator(s)...\n')
    terminal(adb_dir + 'kill-server')
    loads = 0
    while True:
        try:
            loads += 1
            if loads == 11:
                break

            result = terminal(adb_dir + 'devices', capture_output=True).stdout.decode('utf-8')
            state = None
            devices = []
            for line in result.split('\n'):
                if 'List of devices attached' in line:
                    continue
                if line == '' or line == '\r':
                    continue
                device = line.replace('\r', '').split('\t')
                if device[0] == '127.0.0.1:5555':
                    continue
                if device[1] == 'device':
                    devices.append(device[0])
                else:
                    state = 'offline'

            if devices == [] or state == 'offline':
                if loads != 1:
                    log('No emulator(s) found or some not fully loaded, retrying after 5 secs...')
                sleep(5)
                continue
            else:
                break
        except IndexError:
            continue

    return devices


def executor(devices, indexes):
    threads = []
    for i in range(len(devices)):
        log('Executing on device ' + str(devices[i]))
        thread = Thread(target=Executor().execute, args=(devices[i],indexes[i],))
        thread.name = devices[i]
        thread.start()
        threads.append(thread)

    start_time = time()
    seconds = 10800 # above a bit of average time of completing all dailies of an account
    done = []
    current_time = None
    for thread in threads:
        while True:
            # current_time = time()
            # elapsed_time = current_time - start_time
            # if elapsed_time > seconds:
            #     break
            if thread.is_alive() == False or thread._is_stopped == True:
                break
            sleep(10)
        done.append(thread.name)
    return done

def indexer():
    with open('./config.json') as j:
        config = load(j)
    configured_devices = config['devices']
    set_max_devices = config['max_devices']

    run_infos = {}
    run_times = ceil(len(configured_devices) / set_max_devices)
    if run_times == 1:
        run_infos[0] = {
            'devices': configured_devices,
            'max': len(configured_devices)
        }
        return run_infos
    
    devices_ran_before_last = 0
    for i in range(run_times - 1):
        devices_ran_before_last += set_max_devices
    last_run_devices = len(configured_devices) - devices_ran_before_last

    queue = configured_devices
    for i in range(run_times - 1):
        run_infos[i] = {
            'devices': queue[:set_max_devices],
            'max': set_max_devices
        }
        del queue[:set_max_devices]

    run_infos[list(run_infos.keys())[-1] + 1] = {
        'devices': queue,
        'max': last_run_devices
    }
    return run_infos


clear = lambda: system('cls')

def run():
    clear()
    log('Launching emulator(s)...')
    console('quitall')
    sleep(5)
    run_infos = indexer()

    for run_time in run_infos:
        quit_retries = 0
        while True:
            for index in run_infos[run_time]['devices']:
                launch(index)

            log('Waiting 30 secs for fully boot up')
            sleep(30)

            devices = load_devices()
            if quit_retries >= 3:
                console('quitall')
                log('Failed on launching and loading emulator(s), please check the config and try again')
                return

            if devices == []:
                quit_retries += 1
                log('No emulator(s) found after 10 loading retries, quitting all emulator(s) and retrying...')
                console('quitall')
                sleep(5)
                continue

            if len(devices) != run_infos[run_time]['max']:
                quit_retries += 1
                log('Emulator(s) found not match configured or calculated max number of devices on this run, quit all emulator(s) and retrying...')
                console('quitall')
                sleep(5)
                continue

            break

        executor(devices, run_infos[run_time]['devices'])