####################### IMPORTS ##############################

import tinytuya
import math
import numbers
import pyttsx3
import json
import concurrent.futures
import time
import sys

from PIL import ImageGrab
from tkinter import *
from random import randrange
from fractions import Fraction
from playsound import playsound
from datetime import datetime
from win32api import SendMessage
from threading import Thread, Timer
from queue import Queue

if sys.platform == 'win32':
    import winsound

debug = True

####################### Voice Output Class ##############################

class VoiceOutput():
    engine = None
    rate = None
    message_queue = None
    say_thread = None

    def __init__(self, *args):
        self.engine = pyttsx3.init()
        self.engine.setProperty('voice', args[0])
        self.message_queue = Queue()
        say_thread = Thread(target=self.say, args=(self.message_queue,))
        say_thread.deamon = True
        say_thread.start()

    def say(self, queue):
        while True:
            msg = queue.get()
            self.engine.say(msg)
            self.engine.runAndWait()

    def say_message(self, msg):
        self.message_queue.put(msg)    

####################### Timer Beeper Class ##############################

class Beeper():
    t = None
    continous_beep = 0
    stop_beep = 0
    time_counter = 0.0

    def __init__(self, *args):
        self.continous_beep = 400
        self.stop_beep = 700

    def start_beeping(self, beep_time):
        if self.time_counter < beep_time:
            self.time_counter = round(self.time_counter + 0.1, 1)
            if self.time_counter.is_integer(): 
                Thread(target=self.beep, args=(self.continous_beep,)).start()
            self.t = Timer(0.1, self.start_beeping, (beep_time,))
            self.t.daemon = True
            self.t.start()
        else:
            self.time_counter = 0.0
            Thread(target=self.beep, args=(self.stop_beep,)).start()

    def beep(self, pitch):
        winsound.Beep(pitch, 500)

####################### User Interface Class ##############################

class UserInterface(Tk):
    def __init__(self, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)

        self.settings = {}
        self.devices = {
            "enlarger_switch" : None,
            "monitor_switch" : None,
            "light_sensor" : None,
            "darkroom_lamps" : [],
            "listing" : None
        }

        self.readSettingsAndDevices()

        self.voice_engine = VoiceOutput(self.settings["voice_id"])
        self.beeper = Beeper()

        self.paper = StringVar()
        self.mode = StringVar()
        self.increment = StringVar()
        self.default_size = StringVar()
        self.default_time = StringVar()
        self.new_size = StringVar()
        self.calculated_exposure_time = DoubleVar(value=0.0)
        self.exposure_time = DoubleVar(value=self.settings["base_exposure_time"])
        self.slider_time = DoubleVar(value=self.settings["base_exposure_time"])
        self.f_stop = DoubleVar(value=0.0)
        self.lamps_brightness = IntVar(value=self.settings["lamps_brightness"])
        self.papers = []
        self.strip_times = []
        self.unaltered_f_times = []
        self.strip_labels = []
        self.strip_nr = 0
        self.measured_lux = 0
        self.lasttime = 0
        self.starttime = 0

        self.exposing = False
        self.enlarger_is_on = False
        self.monitor_is_on = True

        ####################### User Interface Elements ##############################

        # main window
        self.attributes('-fullscreen', True)
        self.configure(background=self.settings["background_color"])

        for i in range(3):
            self.grid_rowconfigure(i, weight=1)

        self.grid_columnconfigure(0, weight=1, uniform="foo")
        self.grid_columnconfigure(1, weight=2, uniform="foo")
        self.grid_columnconfigure(2, weight=1, uniform="foo")

        # exposure frame
        self.exposure_frame = Frame(self, bg=self.settings["foreground_color"])
        self.exposure_frame.grid_columnconfigure(0, weight=1)
        self.exposure_frame.grid(column=0, row=0, columnspan=3,  pady=(20,0), sticky='wen')

        self.dummy_label = Label(self.exposure_frame, bg=self.settings["background_color"])
        self.dummy_label.grid(padx=2, pady=(2,0), ipady=1, sticky='we')

        # exposure time label
        self.exposure_label = self.style_element(Label(self.exposure_frame,text="Exposure time in seconds"))
        self.exposure_label.grid(padx=2, pady=(2,0), ipady=10, sticky='we')

        self.dummy_label = Label(self.exposure_frame, bg=self.settings["background_color"])
        self.dummy_label.grid(padx=2, pady=(2,0), ipady=1, sticky='we')

        # exposure slider - seconds
        self.exposure_slider = Scale(self.exposure_frame,
                                from_=0.0, 
                                to=self.settings["base_exposure_time"]*2, 
                                tickinterval=1, 
                                resolution=self.settings["time_increment"], 
                                orient=HORIZONTAL, 
                                variable=self.slider_time, 
                                font = (("Arial"), self.settings["large_slider_font_size"]), 
                                bg=self.settings["background_color"], fg=self.settings["foreground_color"], bd=0,
                                troughcolor=self.settings["background_color"],
                                highlightbackground=self.settings["foreground_color"],
                                activebackground=self.settings["foreground_color"],
                                command = self.exposure_time_changed)

        self.exposure_slider.grid(sticky='we', ipady=10)

        self.dummy_label = Label(self.exposure_frame, bg=self.settings["background_color"])
        self.dummy_label.grid(padx=2, pady=(0,0), ipady=1, sticky='we')

        self.exposure_label = self.style_element(Label(self.exposure_frame,text="F-Stop adjustment"))
        self.exposure_label.grid(padx=2, pady=(2,0), ipady=10, sticky='we')

        self.dummy_label = Label(self.exposure_frame, bg=self.settings["background_color"])
        self.dummy_label.grid(padx=2, pady=(2,0), ipady=1, sticky='we')

        stop_fraction = float(sum(Fraction(s) for s in self.settings["f_stop_increment"].split()))
        to_stop = self.settings["f_stop_steps"]*stop_fraction
        from_stop = - to_stop

        # exposure slider - f stops
        self.exposure_slider_f = Scale(self.exposure_frame,
                                from_= from_stop, 
                                to = to_stop,
                                tickinterval=1, 
                                resolution=stop_fraction, 
                                orient=HORIZONTAL, 
                                variable=self.f_stop, 
                                font = (("Arial"), self.settings["large_slider_font_size"]), 
                                bg=self.settings["background_color"], fg=self.settings["foreground_color"], bd=0,
                                troughcolor=self.settings["background_color"],
                                highlightbackground=self.settings["foreground_color"],
                                activebackground=self.settings["foreground_color"],
                                command = self.f_stops_changed)

        self.exposure_slider_f.grid(sticky='we', ipady=10)

        # settings frame
        self.settings_frame = Frame(self, bg=self.settings["foreground_color"])
        self.settings_frame.grid_columnconfigure(0, weight=1)
        self.settings_frame.grid_columnconfigure(1, weight=1)
        self.settings_frame.grid(column=0, row=1, columnspan=1, sticky='wen')

        # settings label
        self.settings_label = self.style_element(Label(self.settings_frame, text="Settings"))
        self.settings_label.grid(columnspan=2, padx=2, pady=(2,0), ipady=10, sticky='we')

        self.dummy_label = Label(self.settings_frame, bg=self.settings["background_color"])
        self.dummy_label.grid(columnspan=2, padx=2, pady=(2,0), ipady=1, sticky='we')

        self.i1 = self.style_element(Label(self.settings_frame, text="Set exposure time", anchor="w"))
        self.i1.grid(row=3, column=0, ipady=5, sticky='wens', padx=(2,0), pady=(2,0))
        self.i2 = self.style_element(Label(self.settings_frame, text=self.exposure_time.get(), anchor="w"))
        self.i2.grid(row=3, column=1, sticky='wens', padx=(2,2), pady=(2,0))

        self.i3 = self.style_element(Label(self.settings_frame, text="Calculated time", anchor="w"))
        self.i4 = self.style_element(Label(self.settings_frame, text=self.calculated_exposure_time.get(), anchor="w"))

        self.i5 = self.style_element(Label(self.settings_frame, text="Measured lux", anchor="w"))
        self.i6 = self.style_element(Label(self.settings_frame, text=self.measured_lux, anchor="w"))

        self.fill_papers_dropdown()
        self.i7 = self.style_element(Label(self.settings_frame, text="Photographic paper", anchor="w"))
        self.i7.grid(row=6, column=0, ipady=5, sticky='wens', padx=(2,0), pady=(2,0))
        self.i8 = self.get_dropdown(self.settings_frame, self.paper, self.papers)
        self.i8.grid(row=6, column=1, sticky='wens', padx=(0,0), pady=(0,0))

        self.modes=["Timer", "(F) Teststrip", "(T) Teststrip"]
        self.i9 = self.style_element(Label(self.settings_frame, text="Operation mode", anchor="w"))
        self.i9.grid(row=7, column=0, ipady=5, sticky='wens', padx=(2,0), pady=(2,0))
        self.i10 = self.get_dropdown(self.settings_frame, self.mode, self.modes)
        self.i10.grid(row=7, column=1, sticky='wens', padx=(0,0), pady=(0,0))

        """ increments=["Seconds", "F-Stops"]
        self.i11 = self.style_element(Label(self.settings_frame, text="Increments", anchor="w"))
        self.i11.grid(row=8, column=0, ipady=5, sticky='wens', padx=(2,0), pady=(2,0))
        self.i12 = get_dropdown(self.settings_frame, increment, increments)
        self.i12.grid(row=8, column=1, sticky='wens', padx=(0,0), pady=(0,0)) """

        self.i13 = self.style_element(Label(self.settings_frame, text="Lamps brightness", anchor="w"))
        self.i13.grid(row=9, column=0, ipady=5, sticky='wens', padx=(2,0), pady=(2,2))

        # lamps brightness slider
        self.lamps_brightness_slider = Scale(self.settings_frame,
                                from_=0, 
                                to=255, 
                                resolution=1, 
                                orient=HORIZONTAL, 
                                variable=self.lamps_brightness, 
                                font = (("Arial"), self.settings["small_slider_font_size"]), 
                                bg=self.settings["background_color"], fg=self.settings["foreground_color"], bd=0,
                                troughcolor=self.settings["background_color"],
                                highlightbackground=self.settings["foreground_color"],
                                activebackground=self.settings["foreground_color"],
                                command = self.lamps_brightness_changed)

        self.lamps_brightness_slider.grid(row=9, column=1, sticky='wens', padx=0, pady=0)

        # commands frame
        self.commands_frame = Frame(self, bg=self.settings["foreground_color"])
        self.commands_frame.grid_columnconfigure(0, weight=1)
        self.commands_frame.grid(column=2, row=1, columnspan=1, sticky='wen')

        # commands
        self.commands_label = self.style_element(Label(self.commands_frame, text="Commands"))
        self.commands_label.grid(padx=2, pady=(2,2), ipady=10, sticky='we')

        self.dummy_label = Label(self.commands_frame, bg=self.settings["background_color"])
        self.dummy_label.grid(padx=2, pady=(0,2), ipady=1, sticky='we')

        self.quit_button = self.style_element(Button(self.commands_frame, text="ESC : Quit", anchor="w"))
        self.quit_button.bind('<Button-1>', self.quit)
        self.quit_button.grid(sticky='we', padx=2, pady=(0,2))

        self.switch_monitor_button = self.style_element(Button(self.commands_frame, text="TAB : Switch monitor ON / OFF", anchor="w"))
        self.measure_lux_button = self.style_element(Button(self.commands_frame, text="BACKSPACE : Measure lux", anchor="w"))

        self.expose_button = self.style_element(Button(self.commands_frame, text=f'ENTER : Expose for {self.exposure_time.get()} seconds', anchor="w"))
        self.expose_button.bind('<Button-1>', self.expose)
        self.expose_button.grid(sticky='we', padx=2, pady=(0,2))

        self.reset_strip_button = self.style_element(Button(self.commands_frame, text="SHIFT : Reset teststrip", anchor="w"))
        self.reset_strip_button.bind('<Button-1>', self.reset_strips)
        self.reset_strip_button.grid(sticky='we', padx=2, pady=(0,2))
                
        self.enlarger_switch_button = self.style_element(Button(self.commands_frame, text="SPACEBAR : Switch enlarger ON / OFF", anchor="w"))
        self.enlarger_switch_button.bind('<Button-1>', self.switch_enlarger)
        self.enlarger_switch_button.grid(sticky='we', padx=2, pady=(0,2))

        # exposure time calculator frame
        self.calculator_frame = Frame(self, bg=self.settings["foreground_color"])
        self.calculator_frame.grid_columnconfigure(0, weight=1)
        self.calculator_frame.grid_columnconfigure(1, weight=1)
        self.calculator_frame.grid_columnconfigure(2, weight=1)
        self.calculator_frame.grid_columnconfigure(3, weight=1)
        self.calculator_frame.grid(column=1, row=1, columnspan=1, sticky='wen', padx=30)

        self.calculator_label = self.style_element(Label(self.calculator_frame, text="Exposure Time Calculator"))
        self.calculator_label.grid(columnspan=4, padx=2, pady=(2,2), ipady=10, sticky='we')

        self.dummy_label = Label(self.calculator_frame, bg=self.settings["background_color"])
        self.dummy_label.grid(columnspan=4, padx=2, pady=(0,2), ipady=1, sticky='we')

        self.c1 =  self.style_element(Entry(self.calculator_frame, insertbackground=self.settings["foreground_color"], textvariable=self.default_size))
        self.c2 =  self.style_element(Entry(self.calculator_frame, insertbackground=self.settings["foreground_color"], textvariable=self.new_size))
        self.c3 =  self.style_element(Entry(self.calculator_frame, insertbackground=self.settings["foreground_color"], textvariable=self.default_time))

        self.default_size.trace_add("write", self.calculate_time)
        self.default_time.trace_add("write", self.calculate_time)
        self.new_size.trace_add("write", self.calculate_time)

        self.calculator_label2 = self.style_element(Label(self.calculator_frame, text="default size in cm", anchor="w"))
        self.calculator_label2.grid(column=0, row=2, ipady=5, sticky='wens', padx=(2,0), pady=(0,2))

        self.c1.grid(column=1, row=2, ipady=5, sticky='wens', padx=(2,0), pady=(0,2))

        self.calculator_label2 = self.style_element(Label(self.calculator_frame, text="default time in seconds", anchor="w"))
        self.calculator_label2.grid(column=0, row=3, ipady=5, sticky='wens', padx=(2,0), pady=(0,2))

        self.c2.grid(column=3, row=2, ipady=5, sticky='wens', padx=2, pady=(0,2))

        self.calculator_label2 = self.style_element(Label(self.calculator_frame, text="new size in cm", anchor="w"))
        self.calculator_label2.grid(column=2, row=2, ipady=5, sticky='wens', padx=(2,0), pady=(0,2))

        self.c3.grid(column=1, row=3, ipady=5, sticky='wens', padx=(2,0), pady=(0,2))

        self.calculator_label2 = self.style_element(Label(self.calculator_frame, text="new time in seconds", anchor="w"))
        self.calculator_label2.grid(column=2, row=3, ipady=5, sticky='wens', padx=(2,0), pady=(0,2))

        self.c4 = self.style_element(Label(self.calculator_frame, text="", anchor="w"))
        self.c4.grid(column=3, row=3, ipady=5, sticky='wens', padx=2, pady=(0,2))

        # teststrips
        self.test_strip_frame =  Frame(self, bg=self.settings["foreground_color"])
        self.test_strip_frame.grid(column=1, row=1, columnspan=1, sticky='wens', padx=30)
        self.test_strip_frame.grid_rowconfigure(0,weight=1)
        self.test_strip_frame.grid_remove()

        for i in range (1, self.settings["teststrip"]["strips"]+1):
            strip_label = self.style_element(Label(self.test_strip_frame, text=""))
            strip_label.grid(column=i, row=0, padx=2, pady=(2,2), ipady=0, sticky='wens')
            self.test_strip_frame.grid_columnconfigure(i, weight=1)
            self.strip_labels.append(strip_label)

        # user message box
        self.message_box = Message(self, width=1024, font = (("Arial"), self.settings["interface_font_size"]), bg=self.settings["background_color"], fg=self.settings["foreground_color"])
        self.message_box = Message(self, width=1024, font = (("Arial"), self.settings["interface_font_size"]), bg=self.settings["background_color"], fg=self.settings["foreground_color"])
        self.message_box.grid(column=0, row=2, columnspan=3, pady=20, sticky='wes')

        self.bind( "<Escape>", self.quit )
        self.bind("<space>", self.switch_enlarger)
        self.bind("<Return>", self.expose)
        self.bind("<Shift_R>", self.reset_strips)
        self.bind("<Down>", lambda e: self.exposure_slider.set(self.exposure_slider.get()-self.settings["time_increment"]))
        self.bind("<Up>", lambda e: self.exposure_slider.set(self.exposure_slider.get()+self.settings["time_increment"]))
        self.bind("<Left>", lambda e: self.exposure_slider.set(self.exposure_slider.get()-1))
        self.bind("<Right>", lambda e: self.exposure_slider.set(self.exposure_slider.get()+1))

        self.reset_strip_button.grid_remove()

        self.paper.trace_add("write", self.paper_changed)
        self.mode.trace_add("write", self.mode_changed)
        self.increment.trace_add("write", self.increment_changed)

        self.mode.set(self.modes[0])
        self.paper.set(self.papers[0])

        self.message_to_user("Welcome")

    ####################### FUNCTIONS ##############################

    def say(self, message):
        self.voice_engine.say_message(message)

    def readSettingsAndDevices(self):
        try:
            with open('settings.json', encoding='utf-8') as f: self.settings = json.load(f)
            with open('devices.json', encoding='utf-8') as f:  self.devices["listing"] = json.load(f)
        except Exception as err:
            f = open('README.md', 'r')
            file_contents = f.read()
            print (file_contents)
            f.close()
            msg = f"\n'{err.filename}' {err.strerror}. Scroll up or open the README.md to read how to solve it.\n"
            print (msg)

    def initialize_devices(self):
        try:
            self.setup_devices() 
            self.test_devices()
            if self.devices["enlarger_switch"]: self.devices["enlarger_switch"].turn_off()
            self.switch_darkroom_lamps("red")
            self.message_to_user("All devices are online.")
        except:
            msg = "See the README how to setup your devices."
            self.message_to_user(msg)

    def setup_devices(self):
        try:
            self.checkSettings()
            self.devices["light_sensor"] = None
            self.devices["enlarger_switch"] = None
            self.devices["monitor_switch"] = None
            self.devices["darkroom_lamps"] = []

            for dev in self.devices["listing"]:
                if dev["uuid"]==self.settings["enlarger_switch_uuid"]: 
                    self.devices["enlarger_switch"] = self.get_device_handle(dev, 'outlet')

                for bu in self.settings["lamp_uuids"]:
                    if dev["uuid"]==bu: 
                        lamp = self.get_device_handle(dev, 'bulb')
                        self.devices["darkroom_lamps"].append(lamp)
        
                if dev["uuid"]==self.settings["monitor_switch_uuid"]: 
                    self.devices["monitor_switch"] = self.get_device_handle(dev, 'outlet')
                    self.switch_monitor_button.grid(sticky='we', padx=2, pady=(0,2))
                    self.switch_monitor_button.bind('<Button-1>', self.switch_monitor)
                    self.bind("<Tab>", self.switch_monitor)
                                
                if dev["uuid"]==self.settings["light_intensity_sensor_uuid"]: 
                    self.devices["light_sensor"] = self.get_device_handle(dev, 'outlet')
                    self.measure_lux_button.grid(sticky='we', padx=2, pady=(0,2))
                    self.i3.grid(row=4, column=0, ipady=5, sticky='wens', padx=(2,0), pady=(2,0))
                    self.i4.grid(row=4, column=1, sticky='wens', padx=(2,2), pady=(2,0))
                    self.i5.grid(row=5, column=0, ipady=5, sticky='wens', padx=(2,0), pady=(2,0))
                    self.i6.grid(row=5, column=1, sticky='wens', padx=(2,2), pady=(2,0))
                    self.measure_lux_button.bind('<Button-1>', self.measure_lux)
                    self.bind("<BackSpace>", self.measure_lux)

        except:
            raise Exception()

    def checkSettings(self):
        if not len(self.settings["enlarger_switch_uuid"]) > 5:
            self.message_to_user("Please fill the enlarger switch uuid in the settings jayson file.")
            raise Exception() 

    def test_devices(self):
        # self.after(300000, self.test_devices) #recheck the devices each 5 minutes
        try:
            self.check_device_status(self.devices["enlarger_switch"])
            if self.devices["monitor_switch"]: self.check_device_status(self.devices["monitor_switch"])
            if self.devices["light_sensor"]: self.check_device_status(self.devices["light_sensor"])
            for l in self.devices["darkroom_lamps"]: self.check_device_status(l)
            
        except:
            raise Exception()
            
    def get_device_handle(self, device, type):        
        if device["ip"] and device["version"] and device["key"]:
            device_id = device["id"]
            device_ip = device["ip"]
            device_key = device["key"]
            device_version = float(device["version"])
            if type=='outlet' : dev_handle = tinytuya.OutletDevice(dev_id=device_id, address=device_ip, local_key=device_key, connection_timeout=1, connection_retry_limit=1, connection_retry_delay=0)
            elif type=='bulb' : dev_handle = tinytuya.BulbDevice(dev_id=device_id, address=device_ip, local_key=device_key, connection_timeout=1, connection_retry_limit=1, connection_retry_delay=0)
            dev_handle.set_version(device_version)
        else:
            msg = f'{device["name"]} cannot be initialized. Check if ip, version and key are present in devices jayson'
            self.message_to_user(msg)
            dev_handle = None
            raise Exception("Device error")
        
        return dev_handle

    def device_name(self, device_handle):
        devname="Unknown"
        for dev in self.devices["listing"]:
            if device_handle.id == dev["id"]: devname=dev["name"]
        return devname

    def switch_darkroom_lamps(self, state):
        if state=="white":
            for l in self.devices["darkroom_lamps"]:
                l.set_white(10,1)
                l.turn_on()
        elif state=="red":
            for l in self.devices["darkroom_lamps"]:
                l.set_colour(self.lamps_brightness.get(),0,0)
                l.turn_on()
        else:
            for l in self.devices["darkroom_lamps"]:
                l.turn_off()

    def check_status(self, s, d):
        ok = True
        if d == None or s == None:
            ok = False
        elif s and "Error" in s: 
            msg = f'{self.device_name(d)} : {s["Error"]}'
            self.message_to_user(msg)
            ok = False

        if not ok: 
            raise Exception("Device error")
        else:
            return s

    def check_device_status(self, d):
        def get_device_status(d):
            if not d == None:
                return d.status()
            else:
                return None   

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(get_device_status, d)
            status = future.result()

        return self.check_status(status, d)

    def switch_enlarger(self, state):
        d = self.devices["enlarger_switch"]
        if not d: return self.message_to_user("Enlarger switch is not available.")

        if state == "on":
            if self.settings["switch_off_monitor_when_exposing"]: self.switch_monitor("off")
            if self.settings["switch_off_lamps_when_exposing"]: self.switch_darkroom_lamps("off")
            d = self.devices["enlarger_switch"]
            if d: d.turn_on()
            self.enlarger_is_on = True
            self.starttime = time.time()
        elif state == "off":
            if self.exposing:
                self.do_next_strip() 
                print(f"exposed for: {time.time() - self.starttime}")

            self.exposing = False  
            
            if d: d.turn_off() 
            self.enlarger_is_on = False
            if self.settings["switch_off_lamps_when_exposing"]: self.switch_darkroom_lamps("red")
        else:
            if not self.enlarger_is_on: 
                self.switch_enlarger("on")
            else:
                self.switch_enlarger("off")

    def request_light_measurement(self):
        self.message_to_user("Press BACKSPACE to measure the light intensity.")

    def expose(self, ev):
        if self.exposing or self.exposure_time.get() == 0 : return 
        
        if not self.mode.get() == "Timer" and self.measured_lux == 0.0 and self.devices["light_sensor"]: 
            return self.request_light_measurement()

        if self.settings["beep_each_second"]: self.beeper.start_beeping(self.exposure_time.get())
        self.exposing = True
        self.switch_enlarger("on")
        t = self.exposure_time.get()*1000
        self.after(int(t), self.switch_enlarger, "off") 

    def message_to_user(self, message):
        print(message)
        self.message_box.configure(text=message)
        if self.settings["voice_output"]: self.say(message)

    def style_element(self, widget):

        if widget.widgetName == "entry":
            widget.configure(font=(("Arial"), self.settings["interface_font_size"]), bg=self.settings["background_color"], fg=self.settings["foreground_color"], bd=0, highlightbackground=self.settings["foreground_color"])
        else:
            widget.configure(font=(("Arial"), self.settings["interface_font_size"]), bg=self.settings["background_color"], fg=self.settings["foreground_color"], bd=0, highlightbackground=self.settings["foreground_color"], activebackground=self.settings["background_color"], activeforeground=self.settings["foreground_color"])
              
        return widget

    def get_lux_from_sensor(self):
        lux = 0
        if not self.enlarger_is_on:
            self.message_to_user("Press SPACE to turn the enlarger on.") 
            return lux
        
        s = self.devices["light_sensor"].status()
        if s and s["dps"]["7"]: 
            lux = s["dps"]["7"]

        return lux
            
    def lux_to_time(self):
        units=0
        for p in self.settings["papers"]:
            for key in p.keys():
                if key==self.paper.get():
                    units=p[key].split(" lux for ")
        if len(units) != 2:
            self.message_to_user(f"No exposure values found for {self.paper.get()} paper. Make a teststrip and set the exposure values.")
            return 0
        else:
            lux = float(units[0])
            seconds = float(units[1].split()[0]) 

        if self.measured_lux == 0: return 0
        elif lux == 0 or seconds == 0:
            self.message_to_user(f"Exposure values are missing. Make a teststrip and set the exposure values for {self.paper.get()} paper.")
            return 0
        else:
            factor = lux/self.measured_lux
            new_time = seconds*factor
            return round(new_time,1)

    def measure_lux(self, ev):
        lux = self.get_lux_from_sensor()
        self.measured_lux = lux
        self.i6["text"] = lux

        if lux == 0: self.message_to_user("No light sensor reading.")
        else : self.message_to_user(f"{lux} lux.")

        if self.mode.get() == "Timer":
            t=self.lux_to_time()
            if t>0:
                self.exposure_time_changed(t)
                self.i4["text"]=t

    def fill_papers_dropdown(self):
        self.papers = []
        for p in self.settings["papers"]:
            for key in p.keys():
                self.papers.append(key)

    def get_dropdown(self, frame, var, options):
        d = self.style_element(OptionMenu(frame, var, *options))
        d["menu"].config(font=(("Arial"), self.settings["interface_font_size"]), bg=self.settings["background_color"], fg=self.settings["foreground_color"], activeforeground="#9b0700", activebackground=self.settings["background_color"])
        return d

    def save_exposure_time(self, ev):
        label = ev.widget.cget("text")
        time = float(label.split()[1])
        exposure_values = f"{float(self.measured_lux)} lux for {time} seconds" # lux and seconds
        for p in self.settings["papers"]:
            for key in p.keys():
                if key==self.paper.get():
                    p[key]=exposure_values
                    self.message_to_user(f'You chose strip {label.split()[0]}. {exposure_values} saved for {self.paper.get()} paper.')
                    self.save_settings()
                    self.after(1000, self.capture)  # save screenshot

    def save_settings(self):
        with open('settings.json', 'w', encoding='utf-8') as f: json.dump(self.settings, f, ensure_ascii=False, indent=2)

    def find_fraction(self, fr, steps):
        sign = "+"
        if steps < 0: sign = "-"
        s = abs(steps)
        fr = fr.split("/")
        numerator = s * int(fr[0])
        denominator = int(fr[1])
        whole_number = numerator // denominator
        remainder = numerator % denominator
        proper_fraction = Fraction(remainder, denominator)
        fraction = str(proper_fraction)

        if whole_number != 0 and fraction != "0":
            return f"{sign}{whole_number} {fraction}"
        elif whole_number != 0:
            return f"{sign}{whole_number}"
        elif fraction != "0":
            return f"{sign}{fraction}"
        else:
            return "0"

    def reset_strips(self, ev):
        if self.mode.get() == "Timer": return
        self.strip_times = []
        self.unaltered_f_times = []
        self.measured_lux = 0.0
        self.i6["text"] = 0.0

        if self.settings["teststrip"]["strips"] % 2 == 0: 
            self.settings["teststrip"]["strips"] = self.settings["teststrip"]["strips"] + 1
            self.save_settings()

        steps = math.floor(self.settings["teststrip"]["strips"]/2)
        cor = 0

        base_time = self.get_time_for_paper()
        if not base_time: base_time = self.settings["teststrip"]["base_time"]

        for s in range(-steps, steps + 1) :
            if self.mode.get() == "(F) Teststrip":
                stop_fraction = float(sum(Fraction(s) for s in self.settings["teststrip"]["f_stop_increment"].split()))
                factor = 2**float(s*stop_fraction)
                t2 = round(base_time*factor,1)
                t = round(t2 - cor,1)
                cor = t2
                self.unaltered_f_times.append(t2)
            elif self.mode.get() == "(T) Teststrip":
                t = round(base_time + (s*self.settings["teststrip"]["time_increment"] ), 1)
            
            if t <= 0:
                self.message_to_user("The exposure time must be greater than zero. Please check your teststrip settings.")
                return
            
            self.strip_times.append(t)
           
        self.strip_nr = 0
        for l in self.strip_labels:
            l.configure(text=f" {self.strip_times[0]} s", bg=self.settings["foreground_color"], fg=self.settings["background_color"]) 
        
        self.do_next_strip()

    def set_times_on_strip_labels(self):
        if self.mode.get() == "(F) Teststrip":
            for i in range(len(self.unaltered_f_times)):
                steps = i - math.floor(self.settings["teststrip"]["strips"]/2)
                f_stop = self.find_fraction(self.settings["teststrip"]["f_stop_increment"], steps)
                text = f'({i+1}) \n\n\n\n\n {self.unaltered_f_times[i]} s\n\n\n{f_stop} F'
                self.strip_labels[i].configure(text=text) 
                self.strip_labels[i].bind('<Double-Button-1>', self.save_exposure_time)
        elif self.mode.get() == "(T) Teststrip":
            for i in range(len(self.strip_times)):
                text = f'({i+1}) \n\n\n\n\n\n\n {self.strip_times[i]} s'
                self.strip_labels[i].configure(text=text) 
                self.strip_labels[i].bind('<Double-Button-1>', self.save_exposure_time)

        msg = f'Double click on the best strip to save the exposure values for {self.paper.get()} paper.'
        self.message_to_user(msg)

    def do_next_strip(self):
        if not (self.mode.get() == "(F) Teststrip" or self.mode.get() == "(T) Teststrip") : 
            return

        if self.strip_nr == self.settings["teststrip"]["strips"]: 
            self.strip_labels[self.strip_nr-1].configure(text="", bg=self.settings["background_color"], fg=self.settings["foreground_color"]) 
            self.set_times_on_strip_labels()
            return
        
        if self.strip_nr == 0:
            self.exposure_time_changed(self.strip_times[0])
            if self.measured_lux == 0.0 and self.devices["light_sensor"]: 
                return self.request_light_measurement()
        else:
            self.strip_labels[self.strip_nr-1].configure(text=f"({self.strip_nr})", bg=self.settings["background_color"], fg=self.settings["foreground_color"]) 
            if self.mode.get() == "(T) Teststrip":
                self.exposure_time_changed(self.settings["teststrip"]["time_increment"])
            else: 
                self.exposure_time_changed(self.strip_times[self.strip_nr])

        for i in range(self.strip_nr, self.settings["teststrip"]["strips"]):
            self.strip_labels[i].configure(text=f'{self.exposure_time.get()} s') 
            
        self.strip_nr = self.strip_nr + 1
        return

    def capture(self):
        if not self.settings["teststrip"]["save_screenshot"]: return
        
        filename = datetime.now().strftime("%d %b %Y - %H-%M-%S") + ".jpg"
        im = ImageGrab.grab(bbox=None)
        im.save(f'Darkroom Settings {filename}') 

    def check_lamps_brightness(self, b):
        if int(b)==self.lamps_brightness.get(): 
            self.switch_darkroom_lamps("red")
            self.settings["lamps_brightness"] = self.lamps_brightness.get()
            self.save_settings()

    def paper_changed(self, *args):
        t = self.get_time_for_paper()
        s = self.get_size_for_paper()
        self.calculator_label.configure(text=f"Exposure Time Calculator for {self.paper.get()} paper")
        if self.mode.get() == "Timer": 
            if t: 
                self.new_size.set("")
                self.exposure_time_changed(t)
                self.default_time.set(t)
            else: self.exposure_time_changed(self.settings["base_exposure_time"])
            if s: self.default_size.set(s)
        else: self.reset_strips(None)

    def increment_changed(self, *args):
        return True

    def mode_changed(self, *args):
        self.measured_lux = 0.0
        self.i4["text"] = 0.0
        self.i6["text"] = 0.0
        self.new_size.set("")
        if self.mode.get() == "Timer":
            self.test_strip_frame.grid_remove()
            self.exposure_slider.configure(state='normal')
            self.exposure_slider_f.configure(state='normal')
            self.reset_strip_button.grid_remove()
            self.calculator_frame.grid()
            self.exposure_time_changed(self.get_time_for_paper())
        elif self.mode.get() == "(T) Teststrip" or self.mode.get() == "(F) Teststrip":
            self.test_strip_frame.grid()
            self.calculator_frame.grid_remove()
            self.exposure_slider.configure(state='disabled')
            self.exposure_slider_f.configure(state='disabled')
            self.reset_strip_button.grid()
            self.reset_strips(None)

    def check_set_time(self, t):
        #if no change for 1 second, message user
        if float(t)==self.exposure_time.get(): 
            self.message_to_user(f'Exposure time set to {t} seconds.')

    def exposure_time_changed(self, t):
        self.exposure_time.set(t)
        self.slider_time.set(t)
        self.after(2000, self.check_set_time, t)
        self.i2["text"]=t
        self.expose_button["text"]=f'ENTER : Expose for {t} seconds'
        f = self.time_to_stops(t)
        if isinstance(f, numbers.Number): 
            self.f_stop.set(f)

    def f_stops_changed(self, f):
        t = self.stops_to_time(f)
        self.exposure_time.set(t)
        self.slider_time.set(t)
        self.after(2000, self.check_set_time, t)
        self.i2["text"]=t
        self.expose_button["text"]=f'ENTER : Expose for {t} seconds'

    def stops_to_time(self, f):
        factor = 2**float(f)
        t = round(self.settings["base_exposure_time"]*factor,1)
        return t
    
    def time_to_stops(self, t):
        try:
            factor = float(t)/self.settings["base_exposure_time"]
            stops = math.log(factor)/math.log(2)
            stops = round(stops,2)
            return stops
        except:
            return None
    
    def lamps_brightness_changed(self, b):
        self.after(1000, self.check_lamps_brightness, b)

    def switch_monitor(self, state):
        m = self.devices["monitor_switch"]
        if m:
            if state == "off" : 
                m.turn_off()
                self.monitor_is_on = False
            elif state == "on": 
                m.turn_on()
                self.monitor_is_on = True
            elif self.monitor_is_on: self.switch_monitor("off")
            else: self.switch_monitor("on")

    def calculate_time(self, a,b,c):
        default_size = self.is_float(self.c1.get())
        default_time = self.is_float(self.c3.get())
        new_size = self.is_float(self.c2.get())

        if default_size and default_time and new_size:
            factor = (new_size/default_size)**2
            new_time = round(default_time * factor,1)
            self.c4.configure(text=new_time)
            self.exposure_time_changed(new_time)
        else:
            self.c4.configure(text="")

    def is_float(self, n):
        try:
            n = float(n)
            return n
        except ValueError:
            return None
            
    def get_time_for_paper(self):
        units = None
        for p in self.settings["papers"]:
            for key in p.keys():
                if key==self.paper.get():
                    units=p[key].split(" lux for ")

        if not units or len(units) != 2: return 0
        else: seconds = float(units[1].split()[0]) 
        return seconds

    def get_size_for_paper(self):
        name_parts = self.paper.get().split(" ")
        for p in name_parts:
            if self.is_float(p): return p
        return 0

    def quit(self, ev):
        self.message_to_user("Goodbye")
        del(self.voice_engine)
        self.switch_enlarger("off")
        self.switch_darkroom_lamps("white")
        self.switch_monitor("on")
        self.destroy()
        sys.exit()

####################### MAIN ##############################

tinytuya.set_debug(False)

interface = UserInterface()
interface.after(200, interface.initialize_devices) 
interface.mainloop() # show interface

