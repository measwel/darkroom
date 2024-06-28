####################### IMPORTS ##############################

import tinytuya
from playsound import playsound
import pyttsx3
from PIL import ImageGrab
from tkinter import *
import json
from random import randrange
import threading
import concurrent.futures
import time
from fractions import Fraction
import math
from datetime import datetime
import sys
import numbers

if sys.platform == 'win32':
    import winsound

debug = True

####################### User Interface Class ##############################

class UserInterface(Tk):
    def __init__(self, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)

        self.settings = {}
        self.devices = {
            "enlarger_switch" : None,
            "darkroom_lamps" : [],
            "light_sensor" : None,
            "listing" : None
        }

        self.readSettingsAndDevices()

        self.paper = StringVar()
        self.mode = StringVar()
        self.increment = StringVar()
        self.calculated_exposure_time = DoubleVar(value=0.0)
        self.exposure_time = DoubleVar(value=self.settings["base_exposure_time"])
        self.slider_time = DoubleVar(value=self.settings["base_exposure_time"])
        self.f_stop = DoubleVar(value=0.0)
        self.lamps_brightness = IntVar(value=self.settings["lamps_brightness"])
        self.calculated_exposure_time = DoubleVar(value=0.0)
        self.papers = []
        self.strip_times = []
        self.unaltered_f_times = []
        self.strip_labels = []
        self.strip_nr = 0
        self.measured_lux = 0
        self.lasttime = 0
        self.starttime = 0
        self.exposing = False

        ####################### Create Interface Elements ##############################

        # main window
        self.attributes('-fullscreen', True)
        self.configure(background=self.settings["background_color"])

        for i in range(3):
            self.grid_rowconfigure(i, weight=1)

        self.grid_columnconfigure(0, weight=1, uniform="foo")
        self.grid_columnconfigure(1, weight=3, uniform="foo")
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
        self.i3.grid(row=4, column=0, ipady=5, sticky='wens', padx=(2,0), pady=(2,0))
        self.i4 = self.style_element(Label(self.settings_frame, text=self.calculated_exposure_time.get(), anchor="w"))
        self.i4.grid(row=4, column=1, sticky='wens', padx=(2,2), pady=(2,0))

        self.i5 = self.style_element(Label(self.settings_frame, text="Measured lux", anchor="w"))
        self.i5.grid(row=5, column=0, ipady=5, sticky='wens', padx=(2,0), pady=(2,0))
        self.i6 = self.style_element(Label(self.settings_frame, text=self.measured_lux, anchor="w"))
        self.i6.grid(row=5, column=1, sticky='wens', padx=(2,2), pady=(2,0))

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

        self.paper.set(self.papers[0])
        self.mode.set(self.modes[0])

        # commands frame
        self.commands_frame = Frame(self, bg=self.settings["foreground_color"])
        self.commands_frame.grid_columnconfigure(0, weight=1)
        self.commands_frame.grid(column=2, row=1, columnspan=1, sticky='wen')

        # commands
        self.commands_label = self.style_element(Label(self.commands_frame, text="Commands"))
        self.commands_label.grid(padx=2, pady=(2,0), ipady=10, sticky='we')

        self.dummy_label = Label(self.commands_frame, bg=self.settings["background_color"])
        self.dummy_label.grid(padx=2, pady=(2,0), ipady=1, sticky='we')

        self.quit_button = self.style_element(Button(self.commands_frame, text="ESC : Quit", anchor="w"))
        self.quit_button.bind('<Button-1>', self.quit)
        self.quit_button.grid(sticky='we', padx=2, pady=(2,0))

        self.enlarger_switch_button = self.style_element(Button(self.commands_frame, text="SPACEBAR : Switch enlarger ON / OFF", anchor="w"))
        self.enlarger_switch_button.bind('<Button-1>', self.switch_enlarger)
        self.enlarger_switch_button.grid(sticky='we', padx=2, pady=(2,0))

        self.measure_lux_button = self.style_element(Button(self.commands_frame, text="BACKSPACE : Measure lux", anchor="w"))
        self.measure_lux_button.bind('<Button-1>', self.measure_lux)
        self.measure_lux_button.grid(sticky='we', padx=2, pady=(2,0))

        self.reset_strip_button = self.style_element(Button(self.commands_frame, text="SHIFT : Reset teststrip", anchor="w"))
        self.reset_strip_button.bind('<Button-1>', self.reset_strips)
        self.reset_strip_button.grid(sticky='we', padx=2, pady=(2,0))

        self.expose_button = self.style_element(Button(self.commands_frame, text=f'ENTER : Expose for {self.exposure_time.get()} seconds', anchor="w"))
        self.expose_button.bind('<Button-1>', self.expose)
        self.expose_button.grid(sticky='we', padx=2, pady=(2,2))

        self.test_strip_frame =  Frame(self, bg=self.settings["foreground_color"])
        self.test_strip_frame.grid(column=1, row=1, columnspan=1, sticky='wens', padx=30)
        self.test_strip_frame.grid_rowconfigure(0,weight=1)
        self.test_strip_frame.grid_remove()

        # teststrips
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
        self.bind("<BackSpace>", self.measure_lux)
        self.bind("<Return>", self.expose)
        self.bind("<Shift_R>", self.reset_strips)
        self.bind("<Left>", lambda e: self.exposure_slider.set(self.exposure_slider.get()-self.settings["time_increment"]))
        self.bind("<Right>", lambda e: self.exposure_slider.set(self.exposure_slider.get()+self.settings["time_increment"]))
        self.bind("<Down>", lambda e: self.exposure_slider.set(self.exposure_slider.get()-1))
        self.bind("<Up>", lambda e: self.exposure_slider.set(self.exposure_slider.get()+1))

        self.reset_strip_button.grid_remove()
        self.paper.trace_add("write", self.paper_changed)
        self.mode.trace_add("write", self.mode_changed)
        self.increment.trace_add("write", self.increment_changed)

    ####################### FUNCTIONS ##############################

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
            self.switch_darkroom_lamps("red")
            self.message_to_user("All devices are online.")
        except:
            msg = "See the README how to setup your devices."
            self.after(5000, self.message_to_user, msg)

    def setup_devices(self):
        try:
            self.checkSettings()

            self.devices["light_sensor"] = None
            self.devices["enlarger_switch"] = None
            self.devices["darkroom_lamps"] = []

            for dev in self.devices["listing"]:
                if dev["uuid"]==self.settings["light_intensity_sensor_uuid"]: 
                    self.devices["light_sensor"] = self.get_device_handle(dev, 'outlet')

                if dev["uuid"]==self.settings["enlarger_switch_uuid"]: 
                    self.devices["enlarger_switch"] = self.get_device_handle(dev, 'outlet')

                for bu in self.settings["lamp_uuids"]:
                    if dev["uuid"]==bu: 
                        lamp = self.get_device_handle(dev, 'bulb')
                        self.devices["darkroom_lamps"].append(lamp)
        except:
            raise Exception()

    def checkSettings(self):
        if not self.settings["lamp_uuids"][0]:
            self.message_to_user("Please fill the darkroom lamp(s) uuids in the settings jayson file.")
            raise Exception()

        if not len(self.settings["enlarger_switch_uuid"]) > 5:
            self.message_to_user("Please fill the enlarger switch uuid in the settings jayson file.")
            raise Exception() 

    def test_devices(self):
        # self.after(300000, self.test_devices) #recheck the devices each 5 minutes
        try:
            self.check_device_status(self.devices["enlarger_switch"])

            for l in self.devices["darkroom_lamps"]:
                self.check_device_status(l)
            
            if self.devices["light_sensor"]: 
                self.check_device_status(self.devices["light_sensor"])
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

    def switch_enlarger(self, ev):
        if not self.devices["enlarger_switch"]: return self.message_to_user("Enlarger switch is not available. Please read the README how to set it up.")
        status = self.check_device_status(self.devices["enlarger_switch"])
        switch_state=status['dps']['1'] 
        if switch_state==0: 
            self.switch_enlarger_on()
        else:
            self.switch_enlarger_off()

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

    def switch_enlarger_on(self):
        if self.settings["switch_off_lamps_when_exposing"]: 
            self.switch_darkroom_lamps("off")
            
        d = self.devices["enlarger_switch"]
        if d: d.turn_on()
        self.starttime = time.time()

    def switch_enlarger_off(self):
        if self.exposing:
            t = threading.Thread(target=self.beep, args=(700,))
            t.start()
            self.do_next_strip() 
        self.exposing = False  

        print(f"exposed for: {time.time() - self.starttime}")
        d = self.devices["enlarger_switch"]
        if d: d.turn_off()

        if self.settings["switch_off_lamps_when_exposing"]: 
            self.switch_darkroom_lamps("red") 

    def request_light_measurement(self):
        self.message_to_user("Turn on the enlarger and then press BACKSPACE to measure the light intensity.")

    def expose(self, ev):
        if self.exposing or self.exposure_time.get() == 0 : return 
        
        if not self.mode.get() == "Timer" and self.measured_lux == 0.0: 
            return self.request_light_measurement()

        self.exposing = True
        self.after(1000, self.start_beeping)
        self.switch_enlarger_on()
        t = self.exposure_time.get()*1000
        self.after(int(t), self.switch_enlarger_off) 

    def beep(self, i):
        if self.settings["beep_each_second"]: winsound.Beep(i,900)

    def start_beeping(self):
        if self.exposing: 
            t = threading.Thread(target=self.beep, args=(400,))
            t.start()
            self.after(1000, self.start_beeping)

    def say(self, message):
        def speak(message):
            e = pyttsx3.init() 
            e.setProperty('voice', self.settings["voice_id"])
            e.say(message)
            if e._inLoop: e.endLoop()
            e.runAndWait()

        t = threading.Thread(target=speak, args=(message,))
        t.start()

    def message_to_user(self, message):
        self.message_box.configure(text=message)
        if self.settings["voice_output"]: self.say(message)

    def style_element(self, widget):
        widget.configure(font=(("Arial"), self.settings["interface_font_size"]), bg=self.settings["background_color"], fg=self.settings["foreground_color"], bd=0, highlightbackground=self.settings["foreground_color"], activebackground=self.settings["background_color"], activeforeground=self.settings["foreground_color"])
        return widget

    def get_lux_from_sensor(self):
        if not self.devices["light_sensor"]: 
            lux = randrange(1,1000)
            self.after(7000, self.message_to_user,"The set lux value is simulated. Add a light sensor to measure real lux values.")
        else:
            s = self.devices["light_sensor"].status()
            if s and s["dps"]["7"]:
                lux = s["dps"]["7"]
            else:
                lux = 0.0
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

        if self.measured_lux == 0:
            self.message_to_user("No light sensor reading.")
            return 0
        elif lux == 0 or seconds == 0:
            self.message_to_user(f"Exposure values are incorrect. Make a teststrip and set the exposure values for {self.paper.get()} paper.")
            return 0
        else:
            factor = lux/self.measured_lux
            new_time = seconds*factor
            return round(new_time,1)

    def measure_lux(self, ev):
        lux = self.get_lux_from_sensor()
        self.measured_lux = lux
        self.i6["text"] = lux
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
                    self.after(1000,self.capture)  # save screenshot

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
        self.strip_times = []
        self.unaltered_f_times = []
        self.measured_lux = 0.0
        self.i6["text"] = 0.0

        if self.settings["teststrip"]["strips"] % 2 == 0: 
            self.settings["teststrip"]["strips"] = self.settings["teststrip"]["strips"] + 1
            self.save_settings()

        steps = math.floor(self.settings["teststrip"]["strips"]/2)
        cor = 0

        for s in range(-steps, steps + 1) :
            if self.mode.get() == "(F) Teststrip":
                stop_fraction = float(sum(Fraction(s) for s in self.settings["teststrip"]["f_stop_increment"].split()))
                factor = 2**float(s*stop_fraction)
                t2 = round(self.settings["teststrip"]["base_time"]*factor,1)
                t = round(t2 - cor,1)
                cor = t2
                self.unaltered_f_times.append(t2)
            elif self.mode.get() == "(T) Teststrip":
                t = round(self.settings["teststrip"]["base_time"] + (s*self.settings["teststrip"]["time_increment"] ), 1)
            
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
        self.after(5000, self.message_to_user, msg)

    def do_next_strip(self):
        if not (self.mode.get() == "(F) Teststrip" or self.mode.get() == "(T) Teststrip") : 
            return

        if self.strip_nr == self.settings["teststrip"]["strips"]: 
            self.strip_labels[self.strip_nr-1].configure(text="", bg=self.settings["background_color"], fg=self.settings["foreground_color"]) 
            self.set_times_on_strip_labels()
            return
        
        if self.strip_nr == 0:
            self.exposure_time_changed(self.strip_times[0])
            if self.measured_lux == 0.0:
                self.strip_nr = 1
                return self.after(5000, self.request_light_measurement)
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

    def paper_changed(*args):
        return True

    def increment_changed(*args):
        return True

    def mode_changed(self, *args):
        self.measured_lux = 0.0
        self.i4["text"] = 0.0
        self.i6["text"] = 0.0
        if self.mode.get() == "Timer":
            self.test_strip_frame.grid_remove()
            self.exposure_slider.configure(state='normal')
            self.exposure_slider_f.configure(state='normal')
            self.reset_strip_button.grid_remove()
            self.exposure_time_changed(self.settings["base_exposure_time"])
        elif self.mode.get() == "(T) Teststrip" or self.mode.get() == "(F) Teststrip":
            self.test_strip_frame.grid()
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
        self.after(1000, self.check_set_time, t)
        self.i2["text"]=t
        self.expose_button["text"]=f'ENTER : Expose for {t} seconds'
        f = self.time_to_stops(t)
        if isinstance(f, numbers.Number): 
            self.f_stop.set(f)

    def f_stops_changed(self, f):
        t = self.stops_to_time(f)
        self.exposure_time.set(t)
        self.slider_time.set(t)
        self.after(1000, self.check_set_time, t)
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

    def enlarger_brightness_changed(self, b):
        self.after(1000, self.check_enlarger_brightness, b)
        
    def quit(self, ev): 
        self.switch_darkroom_lamps("white")
        if self.devices["enlarger_switch"]: self.devices["enlarger_switch"].turn_off()
        sys.exit()

####################### MAIN ##############################

tinytuya.set_debug(False)

interface = UserInterface()
interface.after(200, interface.initialize_devices) 
interface.mainloop() # show interface

