# guardian-tales-daily
#### A script to handle dailies in Guardian Tales mobile game

## What can this script do
- Handles all dailies except Enhance equipment

## Installations
* 3.7.x < Python < 3.9.x
* Use Virtual Environment:
    * Create virtual environment `virtualenv .env`
    * Activate:
        - Windows `.env\Scripts\activate`
1. Install requirements from requirements.txt:
  * `pip install -r requirements.txt`
2. Run:
  * `python main.py`

## Usage
#### Can only work with these settings:
- Windows 10 or higher
- Game language `ENGLISH`
- Multiple LDPlayer or NoxPlayer Emulator with tablet resolution (`960x540`, `1280x720`, `1600x900`, `1920x1080`)

#### Emulator setup:
- `3 cores CPU` and `4GB RAM` or above is recommended
- Open emulator's `Settings` and head to `Other settings` (or `Basic` on lower LDPlayer version) on the left menu, change `@adb_debug`/`ADB debugging` to `Open local connection`
- If you are using then you don't need to config `ADB debugging`

#### Game setup:
1. Download and install `QooApp` or `TapTap` APK
- `QooApp`: https://apps.qoo-app.com/en/dl/880
- `TapTap`: https://d.tap.io/latest/seo-google
##### After that login to your account or guest then download and install `Guardian Tales`
*I don't recommend using Emulator Store because of its slowly game version update*

2. Game testing
    1. Login to `Play Store`, if you are logging in to the game with a Google account, use that
    2. Launch `Guardian Tales`, if your game freeze of crash (can't login) then process to step 4
    3. If your game show `Unable to connect to server`, then install a `VPN` in `Play Store`
    *I recommend using `1.1.1.1` if you don't know which good*
    *You can set `Always-on-VPN` (for time-saving) by open `Settings`, search and click `VPN`, turn on `Always-on-VPN` and select yours*
    *Explanation of VPN needed: Some morden network infrastructure support IPv6 and usually use it first, but the game itself did not support IPv6 so VPN usually route your connection to IPv4. So the solution using VPN just a single emulator (device) solution. If you want a local network-wide solution, just disable IPv6 on your router instead of installing VPN on each device.*
    4. Hold `Play Store` App and drag it to `Info` in the left side of emulator then click the `Disable` button

3. Turn on your `VPN` if needed then launch `Guardian Tales`, if you can login smoothly then its ok, if it crash or freeze then i don't know what to do next, try asking for help on Emulator Discord support or something

##### Pakages built with pyinstaller and Python 3.9.13