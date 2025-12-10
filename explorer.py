import requests
import time
from SimConnect import *
import tkinter as tk
from tkinter import ttk
import webbrowser
import sys
import reverse_geocoder as rg
import configparser
import pyttsx3

### Configuration variables
loop_time = 1
use_parking_brake = 0
use_copilot = 1
parking_brake_gl = 500
stayontop = 1
window_theme = 'light'  ### Use light or dark
flight_mode = 'start'
real_flight_mode = 'start'
flight_mode_counter = 0
current_altitude = 0
climb_notify = 0
descent_notify = 0

### Startup Variables
sim_errors_logged = 0
brake_mapped = 0
user_has_quit = False
if window_theme == 'light':
    fg_color = 'black'
    bg_color = '#F0F0F0'
elif window_theme == 'dark':
    fg_color = 'white'
    bg_color = 'black'

def soft_wait():  ### Function to handle a non-blocking wait time
    start_time = time.time()
    while (time.time() - start_time)  < loop_time:
        pass

def update_window():
    error_this_time = False
    global datapoints_sent
    global server_errors_logged
    global sim_errors_logged
    global current_latitude
    global current_longitude
    global current_heading
    global current_altitude
    global agl
    global parking_brake
    global brake_mapped
    global landing_lights
    global flight_mode
    global flight_mode_counter
    global real_flight_mode
    global climb_notify
    global descent_notify
    last_altitude = current_altitude
    if on_top.get() == 1:
        window.attributes('-topmost',True)
    else:
        window.attributes('-topmost',False)
    try:
        ### Get Variables
        parking_brake = bool(aq.get("BRAKE_PARKING_POSITION"))
        landing_lights = bool(aq.get("LIGHT_LANDING"))
        agl = int(aq.get("PLANE_ALT_ABOVE_GROUND"))
        current_altitude = aq.get("PLANE_ALTITUDE")
        current_latitude = aq.get("PLANE_LATITUDE")
        current_longitude = aq.get("PLANE_LONGITUDE")
        current_heading = int(aq.get("MAGNETIC_COMPASS"))
        ### Set Labels
        latitude_label['text']="{:.4f}".format(current_latitude)
        longitude_label['text']="{:.4f}".format(current_longitude)
        heading_label['text']=str(int(current_heading)) + "°"
        altitude_label['text']=str(int(current_altitude)) + " ft -- " + str(int(agl)) + " ft AGL"
        landing_lights_label['text']=str(landing_lights)
        sim_status_label['text']="Connected"
        sim_status_label['fg']="green"
        notes_label['text']="/mode:" + str(flight_mode) + " /count:" + str(flight_mode_counter) + "/last:" + str(int(last_altitude)) + "/real:" + str(real_flight_mode)
        get_place()
        ### Determine climb or descent
        altitude_diff = current_altitude - last_altitude
        if last_altitude > current_altitude:
            if flight_mode == "descent":
                flight_mode_counter = flight_mode_counter + 1
            else:
                flight_mode_counter = 0
            flight_mode = "descent"
            
        elif last_altitude < current_altitude:
            if flight_mode == "climb":
                flight_mode_counter = flight_mode_counter + 1
            else:
                flight_mode_counter = 0
            flight_mode = "climb"
        if flight_mode_counter > 10:
            real_flight_mode = flight_mode
        ### Copilot routines
        if use_cp.get() == 1:
            ### Turn off landing lights crossing over 10000
            if real_flight_mode == "climb" and current_altitude > 10000 and climb_notify == 0:
                sim_status_label['text'] = "Climbing through ten thousand feet"
                lights_off()
                engine = pyttsx3.init()
                engine.say('Climbing through ten thousand feet')
                engine.runAndWait()
                climb_notify = 1
            ### Turn on landing lights crossing below 10000
            if real_flight_mode == "descent" and current_altitude < 10500 and descent_notify == 0:
                sim_status_label['text'] = "Descending through ten thousand feet"
                lights_on()
                engine = pyttsx3.init()
                engine.say('Descending through ten thousand feet')
                engine.runAndWait()
                descent_notify = 1
    except Exception as e:
        sim_status_label['text']="Error getting data."
        sim_status_label['fg']="red"
        error_this_time = True
    if use_pb.get() == 1 and agl >= parking_brake_gl and parking_brake:
        if brake_mapped:
            sim_status_label['text'] = "Flying : Already mapped."
        else:
            sim_status_label['text'] = "Flying : Mapping."
            brake_mapped = True
            release_brakes = ae.find("PARKING_BRAKES")
            release_brakes()
            open_map()
            brake_mapped = False

    return "ok"

def test():
    lights_on()

def lights_on():
    ll_on = ae.find("LANDING_LIGHTS_ON")
    ll_on()

def lights_off():
    ll_off = ae.find("LANDING_LIGHTS_OFF")
    ll_off()

    
def get_place():
    global current_latitude
    global current_longitude
    coordinates = (current_latitude, current_longitude)
    results=rg.search(coordinates, mode=1)
    city=results[0]["name"]
    state=results[0]["admin1"]
    country=results[0]["cc"]
    location=city + ", " + state + ", " + country
    geo_label['text']= location

def open_map():
    global current_latitude
    global current_longitude
    global current_heading
    google_url = "https://www.google.com/maps/@?api=1&map_action=map&center=" + str(current_latitude) + "%2C" + str(current_longitude) + "&zoom=13&basemap=satellite"
    bing_url = "https://bing.com/maps/default.aspx?cp=" + str(current_latitude) + "~" + str(current_longitude) + "&style=a&lvl=13"
    zoomearth_url = "https://zoom.earth/#view=" + str(current_latitude) + "," + str(current_longitude) + ",9z/overlays=crosshair"
    skyvector_url = "https://skyvector.com/?ll=" + str(current_latitude) + "," + str(current_longitude) + "&chart=301&zoom=1&fpl=%20KPMD%20undefined"
    if selected_map.get() == "Google Maps":
        webbrowser.open_new(google_url)
    elif selected_map.get() == "Zoom Earth":
        webbrowser.open_new(zoomearth_url)
    elif selected_map.get() == "SkyVector":
        webbrowser.open_new(skyvector_url)
    else:
        webbrowser.open_new(bing_url)

def on_closing():
    global user_has_quit
    user_has_quit = True

def kill_the_window():
    window.destroy()
    sys.exit()

def fsconnect():
    ### Connect to MSFS
    global sm
    global aq
    global ae
    sim_status_label['text'] = 'Connecting...'
    sim_status_label['fg'] = "red"
    connected_to_sim = False
    connection_attempts = 0
    while not connected_to_sim:
        connected_to_sim = True
        try:
            sm = SimConnect()
            aq = AircraftRequests(sm, _time=10)
            ae = AircraftEvents(sm)
        except:
            connected_to_sim = False
        connection_attempts = connection_attempts + 1
        if user_has_quit:
            kill_the_window()
        else:
            sim_status_label['text'] = 'Waiting to connect to sim: ' + str(connection_attempts) + ' attempts'
            soft_wait()
            window.update()
    sim_status_label['text'] = 'Connected to sim'
    sim_status_label['fg'] = 'green'

### Create window
window = tk.Tk()
window.title("MSFS Explorer")
window.resizable(True, True)
window.geometry("600x300")
window.configure(bg=bg_color)
window.protocol("WM_DELETE_WINDOW", on_closing)
window.columnconfigure(0, weight=1)
window.columnconfigure(1, weight=3)
### Set Options and variables
maps_optionlist = ['Google Maps', 'Bing Maps', 'Zoom Earth', "SkyVector"]
selected_map = tk.StringVar(window)
selected_map.set("Google Maps")
use_pb=tk.IntVar()
use_pb.set(use_parking_brake)
use_cp=tk.IntVar()
use_cp.set(use_copilot)
on_top=tk.IntVar()
on_top.set(stayontop)
### status line
sim_status_header = tk.Label (
    fg=fg_color,
    bg=bg_color,
    text="Status:"
)
sim_status_header.grid(column=0, row=0, sticky="w")
sim_status_label = tk.Label (
    fg=fg_color,
    bg=bg_color,
    text="Waiting to connect...",
)
sim_status_label.grid(column=1, row=0)
### latitude line
latitude_header = tk.Label (
    fg=fg_color,
    bg=bg_color,
    text="Latitude:"
)
latitude_header.grid(column=0, row=1, sticky="w")
latitude_label = tk.Label (
    fg=fg_color,
    bg=bg_color,
    text="Waiting for position..."
)
latitude_label.grid(column=1, row=1)
### longitude line
longitude_header = tk.Label(
    fg=fg_color,
    bg=bg_color,
    text = "Longitude:"
)
longitude_header.grid(column=0, row=2, sticky="w")
longitude_label = tk.Label (
    fg=fg_color,
    bg=bg_color,
    text="Waiting for position..."
)
longitude_label.grid(column=1, row=2)
### heading line
heading_header = tk.Label(
    fg=fg_color,
    bg=bg_color,
    text = "Heading:"
)
heading_header.grid(column=0, row=3, sticky="w")
heading_label = tk.Label (
    fg=fg_color,
    bg=bg_color,
    text="Waiting for heading..."
)
heading_label.grid(column=1, row=3)
### Geolocation line
geo_header = tk.Label(
    fg=fg_color,
    bg=bg_color,
    text = "Location:"
)
geo_header.grid(column=0, row=4, sticky="w")
geo_label = tk.Label (
    fg=fg_color,
    bg=bg_color,
    text="Waiting for location..."
)
geo_label.grid(column=1, row=4)
### altitude line
altitude_header = tk.Label(
    fg=fg_color,
    bg=bg_color,
    text = "Altitude:"
)
altitude_header.grid(column=0, row=5, sticky="w")
altitude_label = tk.Label (
    fg=fg_color,
    bg=bg_color,
    text="Waiting for altitude..."
)
altitude_label.grid(column=1, row=5)
### separator
sep = tk.ttk.Separator(master=window, orient="horizontal")
sep.grid(row=6, columnspan=99, sticky=("W","E"))
### google button
google_button = tk.Button (
    fg=fg_color,
    bg=bg_color,
    text = "Open Map",
    command = open_map
)
google_button.grid(column=0, row=7, columnspan=2)
### test button
test_button = tk.Button (
    fg=fg_color,
    bg=bg_color,
    text = "Test",
    command = test
)
test_button.grid(column=1, row=7, columnspan=2)
### separator
sep = tk.ttk.Separator(master=window, orient="horizontal")
sep.grid(row=8, columnspan=99, sticky=("W","E"))
### Map Selector Option
map_selector_header = tk.Label(
    fg=fg_color,
    bg=bg_color,
    text = "Default Map Service:"
)
map_selector_header.grid(column=0, row=9, sticky="w")
map_selector = tk.OptionMenu(window, selected_map, *maps_optionlist)
map_selector.grid(column=1, row=9)
map_selector.configure(bg=bg_color, fg=fg_color, activebackground=bg_color, activeforeground=fg_color)
map_selector["menu"].configure(bg=bg_color, fg=fg_color, activebackground=bg_color, activeforeground=fg_color)
### Parking Brake option
use_pb_check = tk.Checkbutton(window, text = "Use Parking Brake (over ground level +500)", variable=use_pb, onvalue=1, offvalue=0, bg=bg_color, fg=fg_color, activebackground=bg_color, activeforeground=fg_color, selectcolor=bg_color)
use_pb_check.grid(column=0, row=10, sticky=("W"))
### Stay on top option
stay_ontop_check = tk.Checkbutton(window, text = "Keep Window On Top", variable=on_top, onvalue=1, offvalue=0, bg=bg_color, fg=fg_color, activebackground=bg_color, activeforeground=fg_color, selectcolor=bg_color)
stay_ontop_check.grid(column=0, row=11, sticky=("W"))
### Copilot option
use_cp_check = tk.Checkbutton(window, text = "Use Copilot", variable=use_cp, onvalue=1, offvalue=0, bg=bg_color, fg=fg_color, activebackground=bg_color, activeforeground=fg_color, selectcolor=bg_color)
use_cp_check.grid(column=1, row=10, sticky=("W"))


### separator
sep = tk.ttk.Separator(master=window, orient="horizontal")
sep.grid(row=12, columnspan=99, sticky=("W","E"))
### Landing Lights
landing_lights_header = tk.Label(
    fg=fg_color,
    bg=bg_color,
    text = "Landing Lights:"
)
landing_lights_header.grid(column=0, row=13, sticky="w")
landing_lights_label = tk.Label (
    fg=fg_color,
    bg=bg_color,
    text="Waiting for status..."
)
landing_lights_label.grid(column=1, row=13)
### Notes
notes_header = tk.Label(
    fg=fg_color,
    bg=bg_color,
    text = "Notes:"
)
notes_header.grid(column=0, row=14, sticky="w")
notes_label = tk.Label (
    fg=fg_color,
    bg=bg_color,
    text="..."
)
notes_label.grid(column=1, row=14)
### Refresh window
window.update()

### ---------------------------------------------------------------------------
### Main Program component
fsconnect()
while not user_has_quit:
    soft_wait()
    window.update_idletasks()
    ###window.after(2000, update_window)
    update_window()
    window.update()
