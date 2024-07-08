# Darkroom

Automated darkroom control for photo development based on smartlife / tuya devices

# Hardware

- Mandatory: a wifi controlled smartlife/tuya power outlet for switching the enlarger. Example: https://ae01.alicdn.com/kf/S97fb815945d1451cbc119818dae47ebdA/
Tuya-Smart-Plug-Wifi-EU-16a-20a-Smart-Socket-mit-Power-Monitor-Timing-Smart-Life-Support.jpg_640x640.jpg_.webp
- Optionally: a wifi controlled smartlife/tuya power outlet for switching the computer monitor. 
- Optionally: one or more wifi controlled smartlife/tuya RGB LED bulbs. Example: https://ae01.alicdn.com/kf/S46afcd28b23b400791dad89e8fa60a265/Tuya-wifi-bluetooth-smart-lampe-alexa-led-lampe-e27-rgb-smart-gl-hbirnen-110v-220v-smart.jpg_.webp
- Optionally: a wifi controlled usb powered smartlife/tuya light sensor. Example: https://ae01.alicdn.com/kf/S9557b883c7ea4769bb3171bf9ce00533T/Tuya-ZigBee-Wifi-Lichtsensor-Intelligente-Home-Beleuchtung-Sensor-Helligkeits-detektor-Automatisierung-Arbeit-mit-Smart-Life-Linkage.jpg_640x640.jpg_.webp
- Recommended: A LED bulb for the enlarger head. White glass, at least 2000 lumen, 2700 Kelvin (warm white). Example: https://shop.ledvance.com/cdn/shop/files/4058075305014_290_LEDSCLA15017W-827230VGLFRE27FS1OSRAM.jpg or https://www.beleuchtung-mit-led.de/images/product_images/original_images/ledvance_4099854069833.jpg

# Preparing the code

Note: this program is fully functional on Windows only. MacOS and Linux would need upgrades to the audio output code.
If 'python' points to python3 on your system, you can use 'python' in the commands below.

A. Make sure you have the latest version of python3 installed  
B. In Terminal go to the directory with the Darkroom.py sourcecode.  
C. Create a virtual environment: python3 -m venv ./.venv  
   Check if a .venv subdirectory has been created.  
D. If you use an IDE such as Visual Code, make sure the python interpreter is set to the one in .venv:  
   Open commands palette, option "Python: select interpreter" and choose the one in .venv  
   Now you can install the dependancies into the .venv virtual environment.  
E. Install dependencies:  
    pip install --upgrade setuptools wheel  
    pip install tk  
      On macos, "pip install tk" might not work. In that case try: brew install python-tk  
    pip install pillow  
    pip install tinytuya  
    pip install pyttsx3  
    pip install playsound  
    pin install winsound (On Windows only!)  
F. Setup your devices - see below.  
G. Run the application. You can run it without set up devices, but then device control will of course not work.  

# Preparation for darkroom usage

1. Install your smart devices.

The smart outlet switch is mandatory. Please plug the enlarger power cord into it. The outlet switch will control the exposure time. 
The second smart outlet switch is optional. Please plug your computer monitor power cord into it. This will allow switching off the monitor when exposing.  
The RGB LED(s) are optional, but recommended. They work great as darkroom safelights. If you use a traditional safelight, set the option "switch_off_lamps_when_exposing" to false.  
The light sensor is optional, but recommended. It allows automatic exposure time calculation. It should be placed on the baseboard, facing the enlarger lens.  
To take a light intensity (lux) measurement, switch on the enlarger with SPACEBAR, make your settings on the enlarger, then press BACKSPACE.  

2. Create the devices.json file

**Please start by linking your devices to the local wifi network via the Smartlife / Tuya application on a smartphone.**
**Next you should setup an account on https://iot.tuya.com/. Please see https://github.com/jasonacox/tinytuya for instructions.**

Once you can see your devices on iot.tuya.com, please proceed with the next steps:

In Terminal go to the directory with the Darkroom.py sourcecode.
Generate the 'devices.json' file with: python3 -m tinytuya wizard  
Scan local devices: python3 -m tinytuya scan  

**Check afterwards if devices.json lists the IP adresses, version numbers and keys for your devices.**  
For more information please see: https://github.com/jasonacox/tinytuya  

If there is something wrong with devices.json, delete and recreate it with the wizard.  

3. Edit the settings.json file  

**The uuids of the relevant devices must be copied from the devices.json file, into the settings.json file.**  
The rest of the settings can be left at their initial values.

**Notes on uuids**  

"enlarger_switch_uuid" : Providing this will allow using a smart outlet to switch the enlarger on and off. This uuid is mandatory.

"monitor_switch_uuid" : Providing this will allow turning the computer monitor off when exposing. This uuid is optional. To turn the monitor back on, press the TAB key.

"lamp_uuids" : Providing this will allow switching on and off the RGB LEDs which serve as darkroom safelights.   
If you have more smart RGB LEDs to use as safelights, put their guids in the array, comma separated.  

 "light_intensity_sensor_uuid" : Providing this will allow taking a light intensity measurement under the enlarger head and calculating the exposure time automatically.

<pre>
{  
  "lamp_uuids": [ <-- Set uuids of your RGB LED darkroom safelight(s). Optional. 
    "xxx", "yyy"
  ],  
  "enlarger_switch_uuid": "xxx", <-- Set uuid of your smart power outlet that will control your enlarger. Mandatory.  
  "light_intensity_sensor_uuid": "xxx", <-- Set uuid of your light intensity sensor. Optional. Without it, automatic exposure time calculation will not work.  
  "lamps_brightness": 123,  <-- Initial safelights brightness. It will get updated automatically if you change it in the application.
  "base_exposure_time": 20.0, <-- The default exposure time that will be in the middle of the time and F-Stop adjustment scales.
  "time_increments": 0.1, <-- Exposure time increase step in seconds, when moving the exposure slider.  
  "f_stop_increment": "1/10", <-- Fraction by which the F-Stops will be adjusted when you move the F-Stop adjustment slider.
  "f_stop_steps": 50, <-- Total number of F-Stop adjustment steps on both sides of the F-Stop adjustment slider.
  "red": "#6a0500", <-- Hex code of interface color. See: https://icolorpalette.com/color/pastel-red  
    "red": "#6a0500",
  "interface_font_size": 15, <-- fontsize of all elements except sliders
  "large_slider_font_size": 20,  <-- fontsize of the large sliders
  "small_slider_font_size": 10, <-- fontsize of the small sliders
  "switch_off_lamps_when_exposing": true, <-- Whether the darkroom lamps should go off when the enlarger is switched on.  
  "switch_off_monitor_when_exposing": true <-- Whether the computer monitor should go off when the enlarger is switched on. For this to work, the monitor must be powered via a smart switch.  
  "voice_output": true, <-- Should user messages be spoken out loud. This enables using the application with the monitor turned off.  
  "beep_each_second": true, <-- Make a beep after each second during exposure.
  "voice_id": "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_EN-GB_HAZEL_11.0", <-- Registry key of the voice to use.  
  "papers": [ <-- Add the names of your papers to this list. For exposure values, use an empty string. Example: "new_paper" : "",
    {  
      "foma low": "744.0 lumen for 5.0 seconds", <-- Example exposure values. These are set when you make a teststrip for chosen paper and double click on the best teststrip.
      "foma high": "355.0 lumen for 13.3 seconds"
    }  
  ],  
  "teststrip": { 
    "save_screenshot": true, <-- Should a screenshot be saved to the program directory, when you double click on the best teststrip? 
    "strips": 11, <-- Number of strips on the test photo. Choose an odd number.
    "base_time": 15, <-- The exposure time in seconds of the teststrip that will be in the middle. 
    "time_increment": 3, <-- Number of seconds of difference between two consecutive teststrips. Applies to (T) Teststrip mode.
    "f_stop_increment": "1/3" <-- F-Stop difference between two consecutive teststrips. Applies to (F) Teststrip mode.
  }  
}  
</pre>

# Control without display

Most functions of the application can be controlled via the keyboard.

ARROW UP : Increase exposure time by 1 second.  
ARROW DOWN : Decrease exposure time by 1 second.  
ARROW LEFT : Increase exposure time by the increment set in the settings file.  
ARROW RIGHT : Decrease exposure time by the increment set in the settings file.  
ESCAPE : Quit the program.  
BACKSPACE : Calculate the exposure time. This will only work if you have set up a light intensity sensor and determined the exposure value for the used paper.  
RIGHT SHIFT : Reset the testtrip exposure time.  
ENTER : Expose for the set time.  
TAB : Toggle the computer monitor ON and OFF. This will only work if you have connected your monitor via a smart outlet and provided its uuid in settings.json.  

# Making a teststrip

- Enter the minimal exposure time, the time increment and the number of strips in the settings file.
- Start the program.
- Choose the used paper in the dropdown list.
- Switch the operation mode from Timer to Teststrip.
- Press BACKSPACE to take a light intensity reading. Without this, you will not be able to save exposure values for the chosen paper.
- Expose the entire photo for the set time by pressing ENTER.
- Cover the strip(s) shown in the program. Press ENTER to expose the remaining uncovered part of the photo.
- Reapeat until there are no strips left to expose.
- Develop your photo and determine which strip has the best exposure.
- Double click on the corresponding strip in the program.
- The exposure value for the used paper is now saved in the settings file. 
- If "save_screenshot" is set to true in the settings file, a screenshot of the saved exposure values will be saved in the program directory.

The exposure values will be used when calculating the best exposure time for the given paper based on the light sensor reading.

# Troubleshooting

**Offline devices**
When a device goes offline, try power cycling it. It often helps to get it back online again.

**Lightbleed from the monitor**

Most LCD monitors will bleed light from the backlight which might be too much for the darkroom and fog the paper.
To alleviate this you have the following options:

- Turn down the brightness of the monitor to the minimal value
- Use a monitor with deeper black levels (IPS, AV, OLED)
- Place a blanket over the monitor when exposing
- Turn off the monitor and use the application with voice output. If you use a smart outlet for powering the monitor, you can toggle the monitor on and off with the TAB key.

# Helpful resources
Tints of red hex color codes to use for the interface color setting: 
https://icolorpalette.com/color/pastel-red

Instructions for setting up the tuya account and generating devices.json with the tinytuya wizard can be found in the README at: 
https://github.com/jasonacox/tinytuya

The legendary Nocon 
https://www.youtube.com/watch?v=xoAiBNSpg6Y