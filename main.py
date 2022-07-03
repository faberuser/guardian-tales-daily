import sys, logging, traceback

from datetime import datetime
from time import sleep
from shutil import copy
from json import load, dump
from os import path as pth, mkdir, chdir, getcwd, listdir, remove
from subprocess import call

chdir(getcwd())
if pth.exists('./.cache') == False:
    mkdir('./.cache')
if pth.exists('./.cache/log.log') == False:
    open('./.cache/log.log', 'a').close()
logging.basicConfig(
    handlers=[logging.FileHandler("./.cache/log.log", "a", "utf-8")],
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)

def log(text):
    logging.info(text)
    print(text)

try:
    with open('./config.json') as f:
        config = load(f)
except FileNotFoundError:
    log('Config not found, creating new one...')
    config = {
        "bonus_cutoff": 0,
        "time": "00:10",
        "max_devices": 1,
        "devices": [],
        "emulator": "",
        "sweep_dungeon": "Random 3 resource Dungeon",
        "startup": "none"
    }
    with open('./config.json', 'a') as f:
        dump(config, f, indent=4)

from PyQt5.QtWidgets import ( QApplication, QPushButton, QWidget, QLineEdit, QFileDialog,
    QAction, QComboBox, QLabel, QDesktopWidget, QInputDialog, QSystemTrayIcon, QMenu, QMessageBox, QCheckBox )
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import QThread, Qt, pyqtSlot

class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.initUI()
        self.worker = None
        if config['startup'] == 'none':
            pass
        elif config['startup'] == 'once':
            self.run_once.setDisabled(True)
            self.run_once.setText('Run this script once (Running)')
            self.run_background.setDisabled(True)
            self.start_config.setDisabled(True)

            self.worker = OnRunOnce()
            self.worker.start()
            self.worker.finished.connect(self.on_run_once_click_finished)
        elif config['startup'] == 'background':
            self.run_once.setDisabled(True)
            self.run_background.setText('Run this script in background (Running) - Stop')
            self.start_config.setDisabled(True)

            self.worker = OnRunBackground()
            self.worker.start()
            self.worker.finished.connect(self.on_run_background_click_finished)

    def initUI(self):
        # Widget settings
        scriptDir = pth.dirname(pth.realpath(__file__))
        icon = QIcon(scriptDir + pth.sep + 'ico.png')

        self.setWindowTitle("Guardian Tales Daily")
        self.setWindowIcon(icon)
        self.setGeometry(10, 10, 320, 330)
        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)
        
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setVisible(True)
        self.tray_menu = QMenu(self)
        self.tray_menu.addAction(QAction("Restore", self, triggered=self.showNormal))
        self.tray_menu.addAction(QAction("Quit", self, triggered=QApplication.instance().quit))
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        self.format_options = QLabel("Select an option:", self)
        self.format_options.setFont(QFont('Arial', 12))
        self.format_options.move(12, 8)

        # 1) Run this script once
        self.run_once = QPushButton("Run this script once", self)
        self.run_once.setFont(QFont('Arial', 10))
        self.run_once.setToolTip("Run this script once")
        self.run_once.resize(300, 40)
        self.run_once.move(10, 35)
        self.run_once.clicked.connect(self.on_run_once_click)

        # 2) Run this script in background to check and run when new day
        self.run_background = QPushButton("Run this script in background", self)
        self.run_background.setFont(QFont('Arial', 10))
        self.run_background.setToolTip("Run this script in background") # TODO minimizing window
        self.run_background.resize(300, 40)
        self.run_background.move(10, 80)
        self.run_background.clicked.connect(self.on_run_background_click)

        # 3) Make this script auto start in background upon Windows startup
        had = False
        for file in listdir(pth.expanduser('~\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup')):
            if file == 'Guardian Tales Daily.lnk':
                had = True
        if had == False:
            self.make_background = QPushButton("Sign this script on Windows startup", self)
        else:
            self.make_background = QPushButton("Unsign this script on Windows startup", self)
        self.make_background.setFont(QFont('Arial', 10))
        self.make_background.setToolTip("Sign or Unsign this script on Windows startup")
        self.make_background.resize(300, 40)
        self.make_background.move(10, 125)
        self.make_background.clicked.connect(self.on_make_background_click)

        # 4) Start config this script
        self.start_config = QPushButton("Start config this script", self)
        self.start_config.setFont(QFont('Arial', 10))
        self.start_config.setToolTip("Start configure this script")
        self.start_config.resize(300, 40)
        self.start_config.move(10, 170)
        self.start_config.clicked.connect(self.on_start_config_click)

        # 5) View current configuration
        self.view_config = QPushButton("View current configuration", self)
        self.view_config.setFont(QFont('Arial', 10))
        self.view_config.setToolTip("View current configuration")
        self.view_config.resize(300, 40)
        self.view_config.move(10, 215)
        self.view_config.clicked.connect(self.on_view_config_click)

        # 6) Exit Program
        self.exit_program = QPushButton("Minimize windows", self)
        self.exit_program.setFont(QFont('Arial', 10))
        self.exit_program.setToolTip("Safe quit program")
        self.exit_program.resize(300, 40)
        self.exit_program.move(10, 260)
        self.exit_program.clicked.connect(self.close)

        self.author = QLabel('Made by Faber', self)
        self.author.move(130, 307)
        quit = QAction("Quit", self)
        quit.triggered.connect(self.close)

    def on_tray_icon_activated(self, event):
        if event == QSystemTrayIcon.DoubleClick:
            if self.isHidden():
                self.show()
            else:
                self.hide()

    def did_not_configured(self):
        QMessageBox.information(self, "Notice", "The script hasn't been configured correctly. Please config again with <b>Start config this script</b>.")

    def on_run_once_click(self):
        with open('./config.json') as f:
            config = load(f)
        if config['emulator'] == '' or config['devices'] == []:
            self.did_not_configured()
            return

        self.run_once.setDisabled(True)
        self.run_once.setText('Run this script once (Running)')
        self.run_background.setDisabled(True)
        self.start_config.setDisabled(True)

        self.worker = OnRunOnce()
        self.worker.start()
        self.worker.finished.connect(self.on_run_once_click_finished)

    def on_run_once_click_finished(self):
        self.run_once.setDisabled(False)
        self.run_once.setText('Run this script once')
        self.run_background.setDisabled(False)
        self.start_config.setDisabled(False)

    def on_run_background_click(self):
        with open('./config.json') as f:
            config = load(f)
        if config['emulator'] == '' or config['devices'] == []:
            self.did_not_configured()
            return

        if isinstance(self.worker, OnRunBackground):
            if self.worker.alive:
                self.worker.stop()
                return

        self.run_once.setDisabled(True)
        self.run_background.setText('Run this script in background (Running) - Stop')
        self.start_config.setDisabled(True)

        self.worker = OnRunBackground()
        self.worker.start()
        self.worker.finished.connect(self.on_run_background_click_finished)

    def on_run_background_click_finished(self):
        self.run_once.setDisabled(False)
        self.run_background.setDisabled(False)
        self.run_background.setText('Run this script in background')
        self.start_config.setDisabled(False)

    def on_make_background_click(self):
        with open('./config.json') as f:
            config = load(f)
        if config['emulator'] == '' or config['devices'] == []:
            self.did_not_configured()
            return

        call([r'generate-shortcut.bat'])
        startup = pth.expanduser('~\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup')
        had = False
        for file in listdir(startup):
            if file == 'Guardian Tales Daily.lnk':
                had = True
        if had == False:
            parent = getcwd()
            copy(parent+r'\Guardian Tales Daily.lnk', startup)
            QMessageBox.information(self, f"Notice", "Script signed to <b>"+startup+"</b>.")
            self.make_background.setText('Unsign this script on Windows startup')
        else:
            remove(startup+'\\Guardian Tales Daily.lnk')
            QMessageBox.information(self, f"Notice", "Script unsigned to <b>"+startup+"</b>.")
            self.make_background.setText('Sign this script on Windows startup')


    def on_start_config_click(self, checked):
        self.configer = Configer()
        self.configer.show()

    def on_view_config_click(self):
        self.view_config = ViewConfig()
        self.view_config.show()

    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            QMessageBox.information(self, "Notice",
                    "The program will keep running in the system tray. To "
                    "terminate the program, choose <b>Quit</b> in the "
                    "context menu of the system tray entry.")
            self.hide()
            event.ignore()


class ViewConfig(QWidget):
    def __init__(self):
        super(ViewConfig, self).__init__()
        self.initUI()
        self.worker = None

    def initUI(self):
        with open('./config.json') as f:
            config = load(f)

        self.setWindowTitle("Config Viewer")
        scriptDir = pth.dirname(pth.realpath(__file__))
        self.setWindowIcon(QIcon(scriptDir + pth.sep + 'ico.png'))
        self.setGeometry(10, 10, 320, 430)
        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())

        self.emulator_label = QLabel('Emulator Path (support LDPlayer and NoxPlayer):', self)
        self.emulator_label.setFont(QFont('Arial', 10))
        self.emulator_label.move(10, 8)

        self.emulator_textbox = QLineEdit(config['emulator'], self)
        self.emulator_textbox.setDisabled(True)
        self.emulator_textbox.move(11, 30)
        self.emulator_textbox.resize(280, 30)


        self.devices_label = QLabel('Added Devices (left number row in LDMultiPlayer):', self)
        self.devices_label.setFont(QFont('Arial', 10))
        self.devices_label.move(10, 70)

        current_devices = ''
        for device in config['devices']:
            current_devices+=str(device)+', '
        self.devices_textbox = QLineEdit(current_devices[:-2], self)
        self.devices_textbox.setDisabled(True)
        self.devices_textbox.move(11, 90)
        self.devices_textbox.resize(280, 30)


        self.max_devices_label = QLabel('Max device(s) running at 1 time:', self)
        self.max_devices_label.setFont(QFont('Arial', 10))
        self.max_devices_label.move(10, 130)

        self.max_devices_textbox = QLineEdit(str(config['max_devices']), self)
        self.max_devices_textbox.setDisabled(True)
        self.max_devices_textbox.move(11, 150)
        self.max_devices_textbox.resize(280, 30)


        self.time_label = QLabel('Time to execute the script:', self)
        self.time_label.setFont(QFont('Arial', 10))
        self.time_label.move(10, 190)

        self.time_textbox = QLineEdit(config['time'], self)
        self.time_textbox.setDisabled(True)
        self.time_textbox.move(11, 210)
        self.time_textbox.resize(280, 30)

        self.sweep_dungeon_label = QLabel('Sweep 30 coffee (3 entries) for a Dungeon', self)
        self.sweep_dungeon_label.setFont(QFont('Arial', 10))
        self.sweep_dungeon_label.move(10, 250)

        self.sweep_dungeon_selector = QComboBox(self)
        dungeons = ['Gold', 'Exp', 'Item', 'Earth - Basic', 'Fire - Light', 'Water - Dark', 'Random 3 resource Dungeon']
        self.sweep_dungeon_selector.addItems(dungeons)
        self.sweep_dungeon_selector.setCurrentIndex(dungeons.index(config['sweep_dungeon']))
        self.sweep_dungeon_selector.setFont(QFont('Arial', 10))
        self.sweep_dungeon_selector.setDisabled(True)
        self.sweep_dungeon_selector.resize(240, 30)
        self.sweep_dungeon_selector.move(10, 270)

        self.bonus_cutoff_label = QLabel('Bonus cutoff for image detection:', self)
        self.bonus_cutoff_label.setFont(QFont('Arial', 10))
        self.bonus_cutoff_label.move(10, 310)

        self.bonus_cutoff_textbox = QLineEdit(str(config['bonus_cutoff']), self)
        self.bonus_cutoff_textbox.setDisabled(True)
        self.bonus_cutoff_textbox.move(11, 330)
        self.bonus_cutoff_textbox.resize(280, 30)

        self.execute_on_startup = QCheckBox('Run once on startup', self)
        self.execute_on_startup.setFont(QFont('Arial', 9))
        self.execute_on_startup.move(4, 370)
        self.execute_on_startup.setDisabled(True)

        self.execute_background_on_startup = QCheckBox('Run in background on startup', self)
        self.execute_background_on_startup.setFont(QFont('Arial', 9))
        self.execute_background_on_startup.move(136, 370)
        self.execute_background_on_startup.setDisabled(True)

        if config['startup'] == 'once':
            self.execute_on_startup.setChecked(True)
        elif config['startup'] == 'background':
            self.execute_background_on_startup.setChecked(True)

        self.cancel_button = QPushButton('Close', self)
        self.cancel_button.setFont(QFont('Arial', 10))
        self.cancel_button.resize(60, 32)
        self.cancel_button.move(120, 395)
        self.cancel_button.clicked.connect(self.close)

        quit = QAction("Quit", self)
        quit.triggered.connect(self.close)

    def closeEvent(self, event):
        if self.worker == None:
            pass
        else:
            self.worker.quit()


class Configer(QWidget):
    def __init__(self):
        super(Configer, self).__init__()
        self.initUI()
        self.worker = None
        self.once = False
        self.background = False

    def initUI(self):
        with open('./config.json') as f:
            config = load(f)

        self.setWindowTitle("Configer")
        scriptDir = pth.dirname(pth.realpath(__file__))
        self.setWindowIcon(QIcon(scriptDir + pth.sep + 'ico.png'))
        self.setGeometry(10, 10, 320, 500)
        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())


        self.emulator_label = QLabel('Emulator Path (Support LDPlayer and NoxPlayer):', self)
        self.emulator_label.setFont(QFont('Arial', 10))
        self.emulator_label.move(10, 8)

        self.emulator_textbox = QLineEdit(config['emulator'], self)
        self.emulator_textbox.setDisabled(True)
        self.emulator_textbox.move(11, 30)
        self.emulator_textbox.resize(240, 30)

        self.emulator_browse = QPushButton("Browse", self)
        self.emulator_browse.setFont(QFont('Arial', 10))
        self.emulator_browse.resize(57, 32)
        self.emulator_browse.move(257, 30)
        self.emulator_browse.clicked.connect(self.on_emulator_browse_click)


        self.devices_label = QLabel('Add Devices (left number row in LDMultiPlayer):', self)
        self.devices_label.setFont(QFont('Arial', 10))
        self.devices_label.move(10, 70)

        current_devices = ''
        if config['devices'] != []:
            for device in config['devices']:
                current_devices+=str(device)+', '
        self.devices_textbox = QLineEdit(current_devices[:-2], self)
        self.devices_textbox.setDisabled(True)
        self.devices_textbox.move(11, 90)
        self.devices_textbox.resize(280, 30)

        self.devices_add = QPushButton('Add', self)
        self.devices_add.setFont(QFont('Arial', 10))
        self.devices_add.resize(57, 32)
        self.devices_add.move(100, 125)
        self.devices_add.clicked.connect(self.add_device_number)

        self.devices_remove = QPushButton('Remove', self)
        self.devices_remove.setFont(QFont('Arial', 10))
        self.devices_remove.resize(57, 32)
        self.devices_remove.move(160, 125)
        self.devices_remove.clicked.connect(self.remove_device_number)


        self.max_devices_label = QLabel('Max device(s) running at 1 time:', self)
        self.max_devices_label.setFont(QFont('Arial', 10))
        self.max_devices_label.move(10, 170)

        self.max_devices_textbox = QLineEdit(str(config['max_devices']), self)
        self.max_devices_textbox.setDisabled(True)
        self.max_devices_textbox.move(11, 190)
        self.max_devices_textbox.resize(240, 30)

        self.max_devices_edit = QPushButton('Edit', self)
        self.max_devices_edit.setFont(QFont('Arial', 10))
        self.max_devices_edit.resize(57, 32)
        self.max_devices_edit.move(257, 190)
        self.max_devices_edit.clicked.connect(self.on_max_devices_edit)


        self.time_label = QLabel('Time to execute the script:', self)
        self.time_label.setFont(QFont('Arial', 10))
        self.time_label.move(10, 230)

        self.time_textbox = QLineEdit(config['time'], self)
        self.time_textbox.setDisabled(True)
        self.time_textbox.move(11, 250)
        self.time_textbox.resize(240, 30)

        self.time_hour_edit = QPushButton('Edit Hour', self)
        self.time_hour_edit.setFont(QFont('Arial', 10))
        self.time_hour_edit.resize(80, 32)
        self.time_hour_edit.move(90, 285)
        self.time_hour_edit.clicked.connect(self.on_hour_edit)

        self.time_minute_edit = QPushButton('Edit Minute', self)
        self.time_minute_edit.setFont(QFont('Arial', 10))
        self.time_minute_edit.resize(80, 32)
        self.time_minute_edit.move(170, 285)
        self.time_minute_edit.clicked.connect(self.on_minute_edit)


        self.sweep_dungeon_label = QLabel('Sweep 30 coffee (3 entries) for a Dungeon', self)
        self.sweep_dungeon_label.setFont(QFont('Arial', 10))
        self.sweep_dungeon_label.move(10, 320)

        self.sweep_dungeon_selector = QComboBox(self)
        dungeons = ['Gold', 'Exp', 'Item', 'Earth - Basic', 'Fire - Light', 'Water - Dark', 'Random 3 resource Dungeon']
        self.sweep_dungeon_selector.addItems(dungeons)
        self.sweep_dungeon_selector.setCurrentIndex(dungeons.index(config['sweep_dungeon']))
        self.sweep_dungeon_selector.setFont(QFont('Arial', 10))
        self.sweep_dungeon_selector.resize(240, 30)
        self.sweep_dungeon_selector.move(10, 340)

        
        self.bonus_cutoff_label = QLabel('Bonus cutoff for image detection:', self)
        self.bonus_cutoff_label.setFont(QFont('Arial', 10))
        self.bonus_cutoff_label.move(10, 380)

        self.bonus_cutoff_textbox = QLineEdit(str(config['bonus_cutoff']), self)
        self.bonus_cutoff_textbox.setDisabled(True)
        self.bonus_cutoff_textbox.move(11, 400)
        self.bonus_cutoff_textbox.resize(240, 30)

        self.bonus_cutoff_edit = QPushButton('Edit', self)
        self.bonus_cutoff_edit.setFont(QFont('Arial', 10))
        self.bonus_cutoff_edit.resize(57, 32)
        self.bonus_cutoff_edit.move(257, 400)
        self.bonus_cutoff_edit.clicked.connect(self.on_bonus_cutoff_edit)


        self.execute_on_startup = QCheckBox('Run once on startup', self)
        self.execute_on_startup.setFont(QFont('Arial', 9))
        self.execute_on_startup.move(4, 435)
        self.execute_on_startup.stateChanged.connect(self.onStateChange)

        self.execute_background_on_startup = QCheckBox('Run in background on startup', self)
        self.execute_background_on_startup.setFont(QFont('Arial', 9))
        self.execute_background_on_startup.move(136, 435)
        self.execute_background_on_startup.stateChanged.connect(self.onStateChange)

        if config['startup'] == 'once':
            self.once = True
            self.execute_on_startup.setChecked(True)
        elif config['startup'] == 'background':
            self.background = True
            self.execute_background_on_startup.setChecked(True)


        self.save_button = QPushButton('Save', self)
        self.save_button.setFont(QFont('Arial', 10))
        self.save_button.resize(57, 32)
        self.save_button.move(100, 460)
        self.save_button.clicked.connect(self.on_save)

        self.cancel_button = QPushButton('Cancel', self)
        self.cancel_button.setFont(QFont('Arial', 10))
        self.cancel_button.resize(57, 32)
        self.cancel_button.move(160, 460)
        self.cancel_button.clicked.connect(self.close)

        quit = QAction("Quit", self)
        quit.triggered.connect(self.close)

    def closeEvent(self, event):
        if self.worker == None:
            pass
        else:
            self.worker.quit()

    @pyqtSlot(int)
    def onStateChange(self, state):
        if state == Qt.Checked:
            if self.sender() == self.execute_on_startup:
                self.execute_background_on_startup.setChecked(False)
            elif self.sender() == self.execute_background_on_startup:
                self.execute_on_startup.setChecked(False)

    def on_save(self):
        bonus_cutoff = int(self.bonus_cutoff_textbox.text())
        time = self.time_textbox.text()
        max_devices = int(self.max_devices_textbox.text())
        devices = []
        if self.devices_textbox.text() != '':
            for device in self.devices_textbox.text().split(', '):
                devices.append(int(device))
        emulator_path = self.emulator_textbox.text()
        sweep_dungeon = self.sweep_dungeon_selector.currentText()
        if self.execute_on_startup.isChecked():
            startup = 'once'
        elif self.execute_background_on_startup.isChecked():
            startup = 'background'
        elif self.execute_on_startup.isChecked() == False and self.execute_background_on_startup.isChecked() == False:
            startup = 'none'

        _config = {
            'bonus_cutoff': bonus_cutoff,
            'time': time,
            'max_devices': max_devices,
            'devices': devices,
            'emulator': emulator_path,
            'sweep_dungeon': sweep_dungeon,
            'startup': startup
        }

        with open('./config.json', 'w') as f:
            dump(_config, f, indent=4)

        self.close()

    def on_bonus_cutoff_edit(self):
        num, done = QInputDialog.getInt(self, 'number', 'Edit a number:')
        if done:
            self.bonus_cutoff_textbox.setText(str(num))

    def on_hour_edit(self):
        num, done = QInputDialog.getInt(self, 'number', 'Edit hour:')
        if done:
            if len(str(num)) == 1:
                new_time = str('0'+str(num)+':'+self.time_textbox.text().split(':')[1])
            elif num == 0 or len(str(num)) > 2 or num > 23:
                return
            elif num == 24:
                new_time = str('00:'+self.time_textbox.text().split(':')[1])
            else:
                new_time = str(str(num)+':'+self.time_textbox.text().split(':')[1])
            self.time_textbox.setText(new_time)

    def on_minute_edit(self):
        num, done = QInputDialog.getInt(self, 'number', 'Edit minute:')
        if done:
            if len(str(num)) == 1:
                new_time = str(self.time_textbox.text().split(':')[0]+':0'+str(num))
            elif num == 0 or len(str(num)) > 2 or num > 59:
                return
            elif num == 60:
                new_time = str(self.time_textbox.text().split(':')[0]+':00')
            else:
                new_time = str(self.time_textbox.text().split(':')[0]+':'+str(num))
            self.time_textbox.setText(new_time)

    def on_max_devices_edit(self):
        num, done = QInputDialog.getInt(self, 'number', 'Edit a number:')
        if done:
            if num != 0:
                self.max_devices_textbox.setText(str(num))
            else:
                self.max_devices_textbox.setText('1')

    def add_device_number(self):
        num, done = QInputDialog.getInt(self, 'number', 'Add a device number:')
        if done:
            if self.devices_textbox.text() == '':
                new_text = str(num)

            elif str(num) not in self.devices_textbox.text().split(', '):
                new_text = self.devices_textbox.text()+', '+str(num)
            
            self.devices_textbox.setText(new_text)

    def remove_device_number(self):
        num, done = QInputDialog.getInt(self, 'number', 'Remove a device number:')
        if done:
            if str(num) in self.devices_textbox.text().split(', '):
                new_text = ''
                for _num in self.devices_textbox.text().split(', '):
                    if _num == str(num):
                        continue
                    new_text+=_num+', '
                self.devices_textbox.setText(new_text[:-2])

    def on_emulator_browse_click(self):
        emulator_path = str(QFileDialog.getExistingDirectory(self, "Select Emulator (LDPlayer/NoxPlayer) Folder/Path/Directory"))
        if emulator_path:
            emulator = None
            emulator_console = False
            last_path = None
            for item in listdir(emulator_path):
                if 'ldconsole.exe' in item:
                    emulator = 'ld'
                    emulator_console = True
                    break
                elif 'Nox.exe' in item:
                    emulator = 'nox'
                    emulator_console = True
                    break
            if emulator_console == False:
                for item in listdir(emulator_path):
                    if 'LDPlayer' in item:
                        emulator = 'ld'
                        last_path = item
                        break
                    elif 'bin' in item:
                        emulator = 'nox'
                        last_path = item
                        break
                if emulator == 'ld':
                    self.emulator_textbox.setText(emulator_path+'/'+last_path+'/ldconsole.exe')
                elif emulator == 'nox':
                    self.emulator_textbox.setText(emulator_path+'/'+last_path+'/Nox.exe')
            else:
                if emulator == 'ld':
                    self.emulator_textbox.setText(emulator_path+'/ldconsole.exe')
                elif emulator == 'nox':
                    self.emulator_textbox.setText(emulator_path+'/Nox.exe')


class OnRunOnce(QThread):
    def __init__(self):
        QThread.__init__(self)
        self.alive = True

    def run(self):
        import executor
        executor.run()
        
    def stop(self):
        self.alive = False

class OnRunBackground(QThread):
    def __init__(self):
        QThread.__init__(self)
        self.alive = True

    def run(self):
        import executor
        while self.alive:
            now = datetime.now().strftime("%H:%M")
            print('Checking at '+str(now))
            if str(now) != config['time']:
                sleep(1)
                continue
            executor.run()
            log('Executed successfully at '+str(now))

    def stop(self):
        self.alive = False


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        ex = MainWindow()
        ex.show()
        sys.exit(app.exec_())
    except:
        traceback.print_exc()