import logging, shutil, sys
from json import load
from time import sleep
from random import random
from os import path, listdir, remove
from subprocess import run as terminal
from urllib.request import urlretrieve

from PIL import Image, ImageDraw
from numpy import array, asarray, empty
from cv2 import bilateralFilter

from locateonscreen import locateOnScreen
from emulator_console import adb_dir, console

logging.basicConfig(
    handlers=[logging.FileHandler("./.cache/log.log", "a", "utf-8")],
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)


def my_same_file_diff_checker(*args, **kwargs):
    return False

shutil._samefile = my_same_file_diff_checker

def _crop(image, box):
    # Return cropped image from given box
    _image = Image.open(image)
    cropped = _image.crop((box[0], box[1], box[0]+box[2], box[1]+box[3]))
    return cropped

def _remove(image, box):
    # Return image with removed given box
    imArray = asarray(Image.open(image).convert("RGBA"))

    rec = [box[0], box[1], box[0]+box[2], box[1]+box[3]]
    maskIm = Image.new('L', (imArray.shape[1], imArray.shape[0]), 0)
    ImageDraw.Draw(maskIm).rectangle(rec, outline=1, fill=1)
    mask = array(maskIm)

    newImArray = empty(imArray.shape, dtype='uint8')

    newImArray[:,:,:3] = imArray[:,:,:3]
    newImArray[:,:,3] = (1-mask)*255

    newIm = Image.fromarray(newImArray, "RGBA")
    return newIm

def _image_to_string(pil_image):
    open_cv_image = array(pil_image.convert('RGB')) 
    open_cv_image = open_cv_image[:, :, ::-1].copy()
    filterd = bilateralFilter(open_cv_image, 9, 75, 75)
    return image_to_string(filterd)


class Executor:
    def __init__(self):
        self.device = None
        self.cache = None
        self.bonus_cutoff = 0
        self.freeze_count = 0
        self.res = None
        self.assets_path = None
    
        self._clear_shop = False
        self._enhance_equipments = False
        self._guild_attendance = False
        self._guardian_points = False
        self._colosseum = False
        self._awakening_dungeon = False
        self._sweep_dungeon = False
        self._claim_mails = False
        self._claim_daily_rewards = False
    

    def log(self, text):
        _text = self.device + ': ' + text
        logging.info(_text)
        print(_text)

    def device_shell(self, command):
        return terminal(adb_dir + '-s ' + self.device + ' shell ' + command, capture_output=True).stdout.decode('utf-8')

    def update_cache(self):
        sleep(0.25)
        self.device_shell('screencap -p /sdcard/screencap.png') # screencap on emulator
        _device = self.device
        if '127.0.0.1' in self.device:
            _device = 'nox_' + self.device.replace('127.0.0.1:', '')
        if self.cache is None:
            terminal(adb_dir + '-s ' + self.device + ' pull /sdcard/screencap.png ./.cache/screencap-'+_device+'-cache-1.png') # pull that screenshot back to host at /.cache
            self.cache = './.cache/screencap-'+_device+'-cache-1.png'
            if self.res == None:
                width, height = Image.open(self.cache).size
                self.res = (0, 0, width, height)
            return
        terminal(adb_dir + '-s ' + self.device + ' pull /sdcard/screencap.png ./.cache/screencap-'+_device+'-cache-2.png') # cache second image to comparing if game freezing
        if locateOnScreen('./.cache/screencap-'+_device+'-cache-2.png', self.cache, minSearchTime=0, confidence=0.4-float(f'0.{self.bonus_cutoff}')):
            self.freeze_count += 1
        shutil.copy('./.cache/screencap-'+_device+'-cache-2.png', './.cache/screencap-'+_device+'-cache-1.png')
        self.cache = './.cache/screencap-'+_device+'-cache-1.png'
        if self.default_checks() == 'crash':
            return 'crash'

    def is_on_screen(self, image, cutoff=0.4):
        return locateOnScreen(image, self.cache, minSearchTime=0, confidence=cutoff-float(f'0.{self.bonus_cutoff}'))

    def get_center(self, coords):
        return (coords[0] + int(coords[2] / 2), coords[1] + int(coords[3] / 2))

    def tap(self, image, cutoff=0.4, hold:int=None):
        box = self.is_on_screen(image, cutoff)
        if box != None:
            center = self.get_center(box)
            if hold is None:
                self.device_shell('input tap ' + str(center[0]) + ' ' + str(center[1]))
            else:
                self.device_shell('input touchscreen swipe ' + str(center[0]) + ' ' + str(center[1]) + ' ' + str(center[0]) + ' ' + str(center[1]) + ' ' + str(hold) + '000')
            sleep(0.5)
        return None


    def execute(self, device, index):
        self.device = device

        with open('./config.json') as f:
            config = load(f)

        self.bonus_cutoff = config['bonus_cutoff']

        while True:
            self.verify_assets()
            if self.login() == 'crash':
                continue

            if self._clear_shop == False:
                if self.clear_shop() == 'crash':
                    continue

            # if self._enhance_equipments == False:
            #     if self.enhance_equipments() == 'crash':
            #         continue

            if self._guild_attendance == False:
                if self.guild_attendance() == 'crash':
                    continue

            if self._guardian_points == False:
                if self.guardian_points() == 'crash':
                    continue

            if self._colosseum == False:
                if self.colosseum() == 'crash':
                    continue

            if self._awakening_dungeon == False:
                if self.awakening_dungeon() == 'crash':
                    continue

            if self._sweep_dungeon == False:
                if self.sweep_dungeon(config) == 'crash':
                    continue

            if self._claim_mails == False:
                if self.claim_mails() == 'crash':
                    continue

            if self._claim_daily_rewards == False:
                if self.claim_daily_rewards() == 'crash':
                    continue

            break

        if 'ldconsole.exe' in config['emulator']:
            console('quit --index ' + str(index))
        elif 'Nox.exe' in config['emulator']:
            console('-clone:Nox_' + str(index) + ' -quit')


    def verify_assets(self):
        if self.update_cache() == 'crash':
            return 'crash'

        try:
            self.assets_path = sys._MEIPASS+'/assets/'+str(self.res[2])+'x'+str(self.res[3])+'/'
        except AttributeError:
            self.assets_path = './assets/'+str(self.res[2])+'x'+str(self.res[3])+'/'
        return

        assets = {
            'awakening_dungeon': {
                '+': False,
                '3_stars': False,
                'adventure': False,
                'auto_repeat': False,
                'awakening_dungeon': False,
                'back': False,
                'cancel': False,
                'confirm': False,
                'recharge_ticket': False,
                'rift': False,
                'sweep_unavailable': False,
                'sweep': False
            },
            'claim_daily_rewards': {
                'back': False,
                'confirm': False,
                'receive_all': False
            },
            'claim_mails': {
                'back': False,
                'confirm': False,
                'mails': False,
                'manage': False,
                'receive_all': False
            },
            'clear_shop': {
                '1000_coin': False,
                'back': False,
                'claim_now': False,
                'confirm': False,
                'equipment': False,
                'error_confirm': False,
                'error': False,
                'free_gold': False,
                'free': False,
                'hammer': False,
                'hero_growth': False,
                'menu_1': False,
                'menu_2': False,
                'resource': False,
                'shop': False
            },
            'colosseum': {
                'adventure': False,
                'attacked_confirm': False,
                'back': False,
                'battle_start': False,
                'caution_confirm': False,
                'colosseum': False,
                'confirm': False,
                'fight_1': False,
                'fight_2': False,
                'game_result_confirm': False,
                'not_enough': False
            },
            'guardian_points': {
                'base_camp': False,
                'collect': False,
                'confirm': False,
                'x': False
            },
            'guild_attendance': {
                'chat': False,
                'confirm': False,
                'guild': False,
                'lobby': False,
                'notice_enter': False,
                'notice_return': False,
                'receive': False,
                'up': False
            },
            'login': {
                'attendance_check_2': False,
                'attendance_check_confirm': False,
                'login_screen_1': False,
                'login_screen_2': False,
                'mission_1': False,
                'mission_2': False,
                'mission_3': False,
                'mission_4': False
            },
            'sweep_dungeon': {
                '+': False,
                '3_stars': False,
                'adventure': False,
                'auto_repeat': False,
                'back': False,
                'cancel': False,
                'confirm': False,
                'earth_basic_dungeon': False,
                'exp_dungeon': False,
                'fire_light_dungeon': False,
                'gold_dungeon': False,
                'item_dungeon': False,
                'resource_dungeon': False,
                'rift': False,
                'sweep_unavailable': False,
                'sweep': False,
                'water_dark_dungeon': False
            }
        }
        
        _path = './assets/'+str(self.res[2])+'x'+str(self.res[3])
        if path.exists(_path):
            for folder in listdir(_path):
                for file in listdir(_path+'/'+folder):
                    for item in assets[folder]:
                        if assets[folder][item] == False:
                            if item in file:
                                assets[folder][item] = True
        
        for item in assets:
            for _item in assets[item]:
                if assets[item][_item] == False:
                    self.log('Some file missing, please recheck to avoid error')


    def default_checks(self):
        # Check various common case may happen while performing
        if self.freeze_count >= 200:
            self.device_shell('am force-stop com.kakaogames.gdts')
            self.freeze_count = 0
            return 'crash'

        current_window = self.device_shell("dumpsys window windows | grep -E mCurrentFocus")
        if 'com.android.launcher' in str(current_window):
            self.log('Launcher deteced')
            return 'crash'


    def login(self):
        # Handle launch game to login
        self.device_shell('monkey -p com.kakaogames.gdts 1') # Launch game
        self.log('Waiting 30 secs for game fully launch...')
        sleep(30)
        login_screen_count = 0
        while True:
            if login_screen_count >= 10:
                self.device_shell('am force-stop com.kakaogames.gdts')
                sleep(1)
                self.device_shell('monkey -p com.kakaogames.gdts 1')
                sleep(30)
            if self.update_cache() == 'crash':
                return 'crash'

            # If chrome or play store is opening
            current_window = self.device_shell("dumpsys window windows | grep -E mCurrentFocus")
            if 'com.android.vending' in str(current_window):
                self.log('Play Store window detected')
                self.device_shell('am force-stop com.android.vending')

            login_screens = [self.assets_path+'login/login_screen_1.png', self.assets_path+'login/login_screen_2.png']
            for img in login_screens:
                if self.is_on_screen(img):
                    self.tap(img)
                    login_screen_count+=1

            if self.is_on_screen(self.assets_path+'login/attendance_check_confirm.png', 0.7):
                self.tap(self.assets_path+'login/attendance_check_confirm.png', 0.7)

            elif self.is_on_screen(self.assets_path+'login/attendance_check_2.png', 0.7):
                self.tap(self.assets_path+'login/attendance_check_2.png', 0.7)

            mission_buttons = [self.assets_path+'login/mission_1.png', self.assets_path+'login/mission_2.png', self.assets_path+'login/mission_3.png', self.assets_path+'login/mission_4.png']
            for img in mission_buttons:
                if self.is_on_screen(img, 0.7):
                    return


    def clear_shop(self):
        # Clear some kinda free shop items
        while True:
            if self.update_cache() == 'crash':
                return 'crash'

            menus = [self.assets_path+'clear_shop/menu_1.png', self.assets_path+'clear_shop/menu_2.png']
            for img in menus:
                if self.is_on_screen(img, 0.7):
                    self.tap(img, 0.7)
                    # package = False
                    # package_count = 0
                    while True:
                        # if package == True or package_count >= 50:
                        #     break
                        if self.update_cache() == 'crash':
                            return 'crash'

                        elif self.is_on_screen(self.assets_path+'clear_shop/shop.png', 0.7):
                            self.tap(self.assets_path+'clear_shop/shop.png', 0.7)

                        elif self.is_on_screen(self.assets_path+'clear_shop/error.png'):
                            self.tap(self.assets_path+'clear_shop/error_confirm.png', 0.7)
                            break

                        # if package == False and self.is_on_screen(self.assets_path+'clear_shop/claim_now.png'):
                        #     self.tap(self.assets_path+'clear_shop/claim_now.png')
                        #     while True:
                        #         if self.update_cache() == 'crash':
                        #             return 'crash'

                        #         elif self.is_on_screen(self.assets_path+'clear_shop/confirm.png'):
                        #             self.tap(self.assets_path+'clear_shop/confirm.png')
                        #             package = True
                        #             break
                        #     continue
                        # else:
                        #     package_count+=1

                    resource = False
                    resource_count = 0
                    while True:
                        if resource == True or resource_count >= 5:
                            break
                        if self.update_cache() == 'crash':
                            return 'crash'

                        if resource == False and self.is_on_screen(self.assets_path+'clear_shop/resource.png', 0.7):
                            self.tap(self.assets_path+'clear_shop/resource.png', 0.7)
                            while True:
                                if resource == True or resource_count >= 5:
                                    break
                                if self.update_cache() == 'crash':
                                    return 'crash'

                                if self.is_on_screen(self.assets_path+'clear_shop/free_gold.png'):
                                    self.tap(self.assets_path+'clear_shop/free_gold.png')
                                else:
                                    resource_count+=1

                                if self.is_on_screen(self.assets_path+'clear_shop/free.png', 0.7):
                                    self.tap(self.assets_path+'clear_shop/free.png', 0.7)

                                elif self.is_on_screen(self.assets_path+'clear_shop/confirm.png', 0.7):
                                    self.tap(self.assets_path+'clear_shop/confirm.png', 0.7)
                                    resource = True
                                    break

                    equipment = False
                    equipment_count = 0
                    while True:
                        if equipment == True or equipment_count >= 5:
                            break
                        if self.update_cache() == 'crash':
                            return 'crash'

                        if equipment == False and self.is_on_screen(self.assets_path+'clear_shop/equipment.png', 0.7):
                            self.tap(self.assets_path+'clear_shop/equipment.png', 0.7)
                            while True:
                                if equipment == True or equipment_count >= 5:
                                    break
                                if self.update_cache() == 'crash':
                                    return 'crash'

                                if self.is_on_screen(self.assets_path+'clear_shop/hammer.png'):
                                    self.tap(self.assets_path+'clear_shop/hammer.png')
                                else:
                                    equipment_count+=1
                            
                                if self.is_on_screen(self.assets_path+'clear_shop/confirm.png', 0.7):
                                    self.tap(self.assets_path+'clear_shop/confirm.png', 0.7)
                                    equipment = True
                                    break

                                elif self.is_on_screen(self.assets_path+'clear_shop/1000_coin.png', 0.7):
                                    self.tap(self.assets_path+'clear_shop/1000_coin.png', 0.7)

                    while True:
                        if self.update_cache() == 'crash':
                            return 'crash'

                        if self.is_on_screen(self.assets_path+'clear_shop/back.png', 0.7):
                            self.tap(self.assets_path+'clear_shop/back.png', 0.7)

                        mission_buttons = [self.assets_path+'login/mission_1.png', self.assets_path+'login/mission_2.png', self.assets_path+'login/mission_3.png', self.assets_path+'login/mission_4.png']
                        for img in mission_buttons:
                            if self.is_on_screen(img, 0.7):
                                self._clear_shop = True
                                return


    def enhance_equipments(self):
        # Enhance a random gear
        # while True:
        #     if self.update_cache() == 'crash':
        #         return 'crash'

        self._enhance_equipments = True

    def guild_attendance(self):
        # Receive Guide Attendance
        while True:
            if self.update_cache() == 'crash':
                return 'crash'

            elif self.is_on_screen(self.assets_path+'guild_attendance/guild.png', 0.7):
                self.tap(self.assets_path+'guild_attendance/guild.png', 0.7)
                while True:
                    if self.update_cache() == 'crash':
                        return 'crash'

                    if self.is_on_screen(self.assets_path+'guild_attendance/notice_enter.png'):
                        self.tap(self.assets_path+'guild_attendance/confirm.png', 0.7)
                        receive_count = 0
                        up = True
                        while True:
                            if receive_count >= 5:
                                while True:
                                    if self.update_cache() == 'crash':
                                        return 'crash'
                                    
                                    elif self.is_on_screen(self.assets_path+'guild_attendance/notice_return.png'):
                                        self.tap(self.assets_path+'guild_attendance/confirm.png', 0.7)

                                    elif self.is_on_screen(self.assets_path+'guild_attendance/lobby.png', 0.7):
                                        self.tap(self.assets_path+'guild_attendance/lobby.png', 0.7)

                                    mission_buttons = [self.assets_path+'login/mission_1.png', self.assets_path+'login/mission_2.png', self.assets_path+'login/mission_3.png', self.assets_path+'login/mission_4.png']
                                    for img in mission_buttons:
                                        if self.is_on_screen(img, 0.7):
                                            self._guild_attendance = True
                                            return

                            if self.update_cache() == 'crash':
                                return 'crash'

                            if self.is_on_screen(self.assets_path+'guild_attendance/chat.png', 0.8):
                                self.tap(self.assets_path+'guild_attendance/chat.png', 0.8)
                                up = False
                            else:
                                if up == True:
                                    self.tap(self.assets_path+'guild_attendance/up.png', 0.7, hold=1)
                                    continue

                            if self.is_on_screen(self.assets_path+'guild_attendance/receive.png', 0.7):
                                self.tap(self.assets_path+'guild_attendance/receive.png', 0.7)
                            else:
                                receive_count+=1

                            if self.is_on_screen(self.assets_path+'guild_attendance/received.png', 0.6):
                                while True:
                                    if self.update_cache() == 'crash':
                                        return 'crash'

                                    elif self.is_on_screen(self.assets_path+'guild_attendance/notice_return.png'):
                                        self.tap(self.assets_path+'guild_attendance/confirm.png', 0.7)

                                    elif self.is_on_screen(self.assets_path+'guild_attendance/lobby.png', 0.7):
                                        self.tap(self.assets_path+'guild_attendance/lobby.png', 0.7)

                                    mission_buttons = [self.assets_path+'login/mission_1.png', self.assets_path+'login/mission_2.png', self.assets_path+'login/mission_3.png', self.assets_path+'login/mission_4.png']
                                    for img in mission_buttons:
                                        if self.is_on_screen(img, 0.7):
                                            self._guild_attendance = True
                                            return

                            if self.is_on_screen(self.assets_path+'guild_attendance/confirm.png', 0.7):
                                self.tap(self.assets_path+'guild_attendance/confirm.png', 0.7)
                                while True:
                                    if self.update_cache() == 'crash':
                                        return 'crash'

                                    elif self.is_on_screen(self.assets_path+'guild_attendance/notice_return.png'):
                                        self.tap(self.assets_path+'guild_attendance/confirm.png', 0.7)

                                    elif self.is_on_screen(self.assets_path+'guild_attendance/lobby.png', 0.7):
                                        self.tap(self.assets_path+'guild_attendance/lobby.png', 0.7)

                                    mission_buttons = [self.assets_path+'login/mission_1.png', self.assets_path+'login/mission_2.png', self.assets_path+'login/mission_3.png', self.assets_path+'login/mission_4.png']
                                    for img in mission_buttons:
                                        if self.is_on_screen(img, 0.7):
                                            self._guild_attendance = True
                                            return
                

    def guardian_points(self):
        # Collect Guardian Points
        screen_center = self.get_center(self.res)
        down = True
        while True:
            if self.update_cache() == 'crash':
                return 'crash'

            if self.is_on_screen(self.assets_path+'guardian_points/base_camp.png', 0.7):
                self.tap(self.assets_path+'guardian_points/base_camp.png', 0.7)
                down = False
            else:
                if down == True:
                    self.device_shell('input touchscreen swipe ' + str(screen_center[0]) + ' ' + str(screen_center[1]+50) + ' ' + str(screen_center[0]) + ' ' + str(screen_center[1]-50))
                    continue

            if self.is_on_screen(self.assets_path+'guardian_points/collect.png', 0.7):
                self.tap(self.assets_path+'guardian_points/collect.png', 0.7)
                while True:
                    if self.update_cache() == 'crash':
                        return 'crash'
                    
                    elif self.is_on_screen(self.assets_path+'guardian_points/confirm.png', 0.7):
                        self.tap(self.assets_path+'guardian_points/confirm.png', 0.7)

                    elif self.is_on_screen(self.assets_path+'guardian_points/x.png', 0.7):
                        self.tap(self.assets_path+'guardian_points/x.png', 0.7)
                        self._guardian_points = True
                        return


    def colosseum(self):
        # Waste 3 entries in Colosseum
        count = 0
        while True:
            if count >= 3:
                while True:
                    if self.update_cache() == 'crash':
                        return 'crash'

                    if self.is_on_screen(self.assets_path+'colosseum/adventure.png', 0.7):
                        self._colosseum = True
                        return

                    elif self.is_on_screen(self.assets_path+'colosseum/game_result_confirm.png', 0.7):
                        self.tap(self.assets_path+'colosseum/game_result_confirm.png', 0.7)

                    elif self.is_on_screen(self.assets_path+'colosseum/attacked_confirm.png', 0.7):
                        self.tap(self.assets_path+'colosseum/attacked_confirm.png', 0.7)

                    elif self.is_on_screen(self.assets_path+'colosseum/back.png', 0.7):
                        self.tap(self.assets_path+'colosseum/back.png', 0.7)

            if self.update_cache() == 'crash':
                return 'crash'

            elif self.is_on_screen(self.assets_path+'colosseum/adventure.png', 0.7):
                self.tap(self.assets_path+'colosseum/adventure.png', 0.7)

            elif self.is_on_screen(self.assets_path+'colosseum/colosseum.png', 0.7):
                self.tap(self.assets_path+'colosseum/colosseum.png', 0.7)

            elif self.is_on_screen(self.assets_path+'colosseum/attacked_confirm.png', 0.7):
                self.tap(self.assets_path+'colosseum/attacked_confirm.png', 0.7)

            elif self.is_on_screen(self.assets_path+'colosseum/fight_1.png', 0.7) or self.is_on_screen(self.assets_path+'colosseum/fight_2.png', 0.7):
                self.tap(self.assets_path+'colosseum/fight_1.png', 0.7)
                self.tap(self.assets_path+'colosseum/fight_2.png', 0.7)
                while True:
                    if self.update_cache() == 'crash':
                        return 'crash'

                    elif self.is_on_screen(self.assets_path+'colosseum/battle_start.png', 0.7):
                        self.tap(self.assets_path+'colosseum/battle_start.png', 0.7)

                    elif self.is_on_screen(self.assets_path+'colosseum/game_result_confirm.png', 0.7):
                        self.tap(self.assets_path+'colosseum/game_result_confirm.png', 0.7)
                        count+=1
                        break

                    elif self.is_on_screen(self.assets_path+'colosseum/not_enough.png'):
                        self.tap(self.assets_path+'colosseum/caution_confirm.png', 0.7)
                        count+=1
                        break


    def awakening_dungeon(self):
        # Clear 3 entries in Awakening Dungeon
        while True:
            if self.update_cache() == 'crash':
                return 'crash'

            elif self.is_on_screen(self.assets_path+'awakening_dungeon/adventure.png', 0.7):
                self.tap(self.assets_path+'awakening_dungeon/adventure.png', 0.7)

            elif self.is_on_screen(self.assets_path+'awakening_dungeon/rift.png', 0.7):
                self.tap(self.assets_path+'awakening_dungeon/rift.png', 0.7)

            elif self.is_on_screen(self.assets_path+'awakening_dungeon/awakening_dungeon.png'):
                self.tap(self.assets_path+'awakening_dungeon/awakening_dungeon.png')

            elif self.is_on_screen(self.assets_path+'awakening_dungeon/auto_repeat.png', 0.7):
                self.tap(self.assets_path+'awakening_dungeon/auto_repeat.png', 0.7)
                while True:
                    if self.update_cache() == 'crash':
                        return 'crash'
                    
                    elif self.is_on_screen(self.assets_path+'awakening_dungeon/+.png', 0.7):
                        self.tap(self.assets_path+'awakening_dungeon/+.png', 0.7)
                        sleep(0.5)
                        self.tap(self.assets_path+'awakening_dungeon/+.png', 0.7)
                        sleep(0.5)
                        done = False
                        done_count = 0
                        while True:
                            if done_count >= 5:
                                while True:
                                    if self.update_cache() == 'crash':
                                        return 'crash'

                                    if self.is_on_screen(self.assets_path+'awakening_dungeon/adventure.png', 0.7):
                                        self._awakening_dungeon = True
                                        return

                                    elif self.is_on_screen(self.assets_path+'awakening_dungeon/back.png', 0.7):
                                        self.tap(self.assets_path+'awakening_dungeon/back.png', 0.7)

                            if done == True:
                                done_count+=1

                            if self.update_cache() == 'crash':
                                return 'crash'

                            elif self.is_on_screen(self.assets_path+'awakening_dungeon/sweep.png', 0.7):
                                self.tap(self.assets_path+'awakening_dungeon/sweep.png', 0.7)

                            elif self.is_on_screen(self.assets_path+'awakening_dungeon/confirm.png', 0.7):
                                self.tap(self.assets_path+'awakening_dungeon/confirm.png', 0.7)
                                done = True

                            elif self.is_on_screen(self.assets_path+'awakening_dungeon/sweep_unavailable.png'):
                                self.tap(self.assets_path+'awakening_dungeon/cancel.png', 0.7)
                                while True:
                                    if self.update_cache() == 'crash':
                                        return 'crash'

                                    if self.is_on_screen(self.assets_path+'awakening_dungeon/adventure.png', 0.7):
                                        self._awakening_dungeon = True
                                        return
                                    
                                    elif self.is_on_screen(self.assets_path+'awakening_dungeon/back.png', 0.7):
                                        self.tap(self.assets_path+'awakening_dungeon/back.png', 0.7)

                    elif self.is_on_screen(self.assets_path+'awakening_dungeon/3_stars.png'):
                        if self.is_on_screen(self.assets_path+'awakening_dungeon/confirm.png', 0.7):
                            self.tap(self.assets_path+'awakening_dungeon/confirm.png', 0.7)
                            while True:
                                if self.update_cache() == 'crash':
                                    return 'crash'

                                if self.is_on_screen(self.assets_path+'awakening_dungeon/adventure.png', 0.7):
                                    self._awakening_dungeon = True
                                    return
                                
                                elif self.is_on_screen(self.assets_path+'awakening_dungeon/back.png', 0.7):
                                    self.tap(self.assets_path+'awakening_dungeon/back.png', 0.7)

            elif self.is_on_screen(self.assets_path+'awakening_dungeon/recharge_ticket.png', 0.7):
                while True:
                    if self.update_cache() == 'crash':
                        return 'crash'

                    if self.is_on_screen(self.assets_path+'awakening_dungeon/adventure.png', 0.7):
                        self._awakening_dungeon = True
                        return
                    
                    elif self.is_on_screen(self.assets_path+'awakening_dungeon/back.png', 0.7):
                        self.tap(self.assets_path+'awakening_dungeon/back.png', 0.7)


    def sweep_dungeon(self, config):
        # Sweep 30 coffee for a configured dungeon
        resource_dungeon = None
        if config['sweep_dungeon'] == 'Gold':
            resource_dungeon = self.assets_path+'sweep_dungeon/resource_dungeon.png'
            dungeon = self.assets_path+'sweep_dungeon/gold_dungeon.png'
        elif config['sweep_dungeon'] == 'Exp':
            resource_dungeon = self.assets_path+'sweep_dungeon/resource_dungeon.png'
            dungeon = self.assets_path+'sweep_dungeon/exp_dungeon.png'
        elif config['sweep_dungeon'] == 'Item':
            resource_dungeon = self.assets_path+'sweep_dungeon/resource_dungeon.png'
            dungeon = self.assets_path+'sweep_dungeon/item_dungeon.png'

        elif config['sweep_dungeon'] == 'Earth - Basic':
            dungeon = self.assets_path+'sweep_dungeon/earth_basic_dungeon.png'
        elif config['sweep_dungeon'] == 'Fire - Light':
            dungeon = self.assets_path+'sweep_dungeon/fire_light_dungeon.png'
        elif config['sweep_dungeon'] == 'Water - Dark':
            dungeon = self.assets_path+'sweep_dungeon/water_dark_dungeon.png'

        else:
            dungeon = random([self.assets_path+'sweep_dungeon/gold_dungeon.png', self.assets_path+'sweep_dungeon/exp_dungeon.png', self.assets_path+'sweep_dungeon/item_dungeon.png'])

        count = 0
        while True:
            if count >= 10:
                while True:
                    if self.update_cache() == 'crash':
                        return 'crash'

                    if self.is_on_screen(self.assets_path+'sweep_dungeon/adventure.png', 0.7):
                        self._sweep_dungeon = True
                        return

                    elif self.is_on_screen(self.assets_path+'sweep_dungeon/back.png', 0.7):
                        self.tap(self.assets_path+'sweep_dungeon/back.png', 0.7)

            if self.update_cache() == 'crash':
                return 'crash'

            elif self.is_on_screen(self.assets_path+'sweep_dungeon/adventure.png', 0.7):
                self.tap(self.assets_path+'sweep_dungeon/adventure.png', 0.7)

            elif self.is_on_screen(self.assets_path+'sweep_dungeon/rift.png', 0.7):
                self.tap(self.assets_path+'sweep_dungeon/rift.png', 0.7)

            if resource_dungeon is not None:
                if self.is_on_screen(resource_dungeon):
                    self.tap(resource_dungeon)
                    while True:
                        if self.update_cache() == 'crash':
                            return 'crash'
                        
                        elif self.is_on_screen(dungeon, 0.7):
                            self.tap(dungeon, 0.7)
                            break
            else:
                if self.is_on_screen(dungeon):
                    self.tap(dungeon)

            if self.is_on_screen(self.assets_path+'sweep_dungeon/auto_repeat.png', 0.7):
                self.tap(self.assets_path+'sweep_dungeon/auto_repeat.png', 0.7)
                while True:
                    if self.update_cache() == 'crash':
                        return 'crash'
                    
                    elif self.is_on_screen(self.assets_path+'sweep_dungeon/+.png', 0.7):
                        self.tap(self.assets_path+'sweep_dungeon/+.png', 0.7)
                        sleep(0.5)
                        self.tap(self.assets_path+'sweep_dungeon/+.png', 0.7)
                        sleep(0.5)
                        done = False
                        done_count = 0
                        while True:
                            if done_count >= 5:
                                while True:
                                    if self.update_cache() == 'crash':
                                        return 'crash'

                                    if self.is_on_screen(self.assets_path+'sweep_dungeon/adventure.png', 0.7):
                                        self._sweep_dungeon = True
                                        return

                                    elif self.is_on_screen(self.assets_path+'sweep_dungeon/back.png', 0.7):
                                        self.tap(self.assets_path+'sweep_dungeon/back.png', 0.7)

                            if done == True:
                                done_count+=1

                            if self.update_cache() == 'crash':
                                return 'crash'

                            elif self.is_on_screen(self.assets_path+'sweep_dungeon/sweep.png', 0.7):
                                self.tap(self.assets_path+'sweep_dungeon/sweep.png', 0.7)

                            elif self.is_on_screen(self.assets_path+'sweep_dungeon/confirm.png', 0.7):
                                self.tap(self.assets_path+'sweep_dungeon/confirm.png', 0.7)
                                done = True

                            elif self.is_on_screen(self.assets_path+'sweep_dungeon/sweep_unavailable.png'):
                                self.tap(self.assets_path+'sweep_dungeon/cancel.png', 0.7)
                                while True:
                                    if self.update_cache() == 'crash':
                                        return 'crash'

                                    if self.is_on_screen(self.assets_path+'sweep_dungeon/adventure.png', 0.7):
                                        self._sweep_dungeon = True
                                        return
                                    
                                    elif self.is_on_screen(self.assets_path+'sweep_dungeon/back.png', 0.7):
                                        self.tap(self.assets_path+'sweep_dungeon/back.png', 0.7)

                    elif self.is_on_screen(self.assets_path+'sweep_dungeon/3_stars.png'):
                        if self.is_on_screen(self.assets_path+'sweep_dungeon/confirm.png', 0.7):
                            self.tap(self.assets_path+'sweep_dungeon/confirm.png', 0.7)
                            while True:
                                if self.update_cache() == 'crash':
                                    return 'crash'

                                if self.is_on_screen(self.assets_path+'sweep_dungeon/adventure.png', 0.7):
                                    self._sweep_dungeon = True
                                    return
                                
                                elif self.is_on_screen(self.assets_path+'sweep_dungeon/back.png', 0.7):
                                    self.tap(self.assets_path+'sweep_dungeon/back.png', 0.7)
            else:
                count+=1

    def claim_mails(self):
        # Claim all mails
        mails_count = 0
        while True:
            if mails_count >= 5:
                while True:
                    if self.update_cache() == 'crash':
                        return 'crash'

                    elif self.is_on_screen(self.assets_path+'claim_mails/back.png', 0.7):
                        self.tap(self.assets_path+'claim_mails/back.png', 0.7)

                    mission_buttons = [self.assets_path+'login/mission_1.png', self.assets_path+'login/mission_2.png', self.assets_path+'login/mission_3.png', self.assets_path+'login/mission_4.png']
                    for img in mission_buttons:
                        if self.is_on_screen(img, 0.7):
                            self._claim_mails = True
                            return

            if self.update_cache() == 'crash':
                return 'crash'
            
            elif self.is_on_screen(self.assets_path+'claim_mails/mails.png', 0.7):
                self.tap(self.assets_path+'claim_mails/mails.png', 0.7)
                receive_all_count = 0
                while True:
                    receive_all = False
                    if receive_all_count >= 5:
                        break
                    if self.update_cache() == 'crash':
                        return 'crash'

                    if self.is_on_screen(self.assets_path+'claim_mails/manage.png', 0.6):
                        self.tap(self.assets_path+'claim_mails/manage.png', 0.6)

                    if self.is_on_screen(self.assets_path+'claim_mails/receive_all.png', 0.9):
                        self.tap(self.assets_path+'claim_mails/receive_all.png', 0.9)
                        receive_all = True
                    else:
                        receive_all_count+=1

                    if receive_all == False:
                        if self.is_on_screen(self.assets_path+'claim_mails/confirm.png', 0.6):
                            self.tap(self.assets_path+'claim_mails/confirm.png', 0.6)
                            break
                
                while True:
                    if self.update_cache() == 'crash':
                        return 'crash'

                    elif self.is_on_screen(self.assets_path+'claim_mails/back.png', 0.7):
                        self.tap(self.assets_path+'claim_mails/back.png', 0.7)

                    mission_buttons = [self.assets_path+'login/mission_1.png', self.assets_path+'login/mission_2.png', self.assets_path+'login/mission_3.png', self.assets_path+'login/mission_4.png']
                    for img in mission_buttons:
                        if self.is_on_screen(img, 0.7):
                            self._claim_mails = True
                            return
            else:
                mails_count += 1


    def claim_daily_rewards(self):
        # Claim completed daily rewards
        count = 0
        while True:
            if count >= 10:
                while True:
                    if self.update_cache() == 'crash':
                        return 'crash'

                    mission_buttons = [self.assets_path+'login/mission_1.png', self.assets_path+'login/mission_2.png', self.assets_path+'login/mission_3.png', self.assets_path+'login/mission_4.png']
                    for img in mission_buttons:
                        if self.is_on_screen(img, 0.7):
                            self._claim_daily_rewards = True
                            return

                    if self.is_on_screen(self.assets_path+'claim_daily_rewards/back.png', 0.7):
                        self.tap(self.assets_path+'claim_daily_rewards/back.png', 0.7)

            if self.update_cache() == 'crash':
                return 'crash'

            mission_buttons = [self.assets_path+'login/mission_1.png', self.assets_path+'login/mission_2.png', self.assets_path+'login/mission_3.png', self.assets_path+'login/mission_4.png']
            for img in mission_buttons:
                if self.is_on_screen(img, 0.7):
                    self.tap(img, 0.7)

            if self.is_on_screen(self.assets_path+'claim_daily_rewards/receive_all.png', 0.9):
                self.tap(self.assets_path+'claim_daily_rewards/receive_all.png', 0.9)
            else:
                count+=1

            if self.is_on_screen(self.assets_path+'claim_daily_rewards/confirm.png', 0.9):
                self.tap(self.assets_path+'claim_daily_rewards/confirm.png', 0.9)
                while True:
                    if self.update_cache() == 'crash':
                        return 'crash'

                    mission_buttons = [self.assets_path+'login/mission_1.png', self.assets_path+'login/mission_2.png', self.assets_path+'login/mission_3.png', self.assets_path+'login/mission_4.png']
                    for img in mission_buttons:
                        if self.is_on_screen(img, 0.7):
                            self._claim_daily_rewards = True
                            return

                    if self.is_on_screen(self.assets_path+'claim_daily_rewards/back.png', 0.7):
                        self.tap(self.assets_path+'claim_daily_rewards/back.png', 0.7)


    def update_apk(self):
        self.log('Game update required, process terminated, please update for game and run this script again')
