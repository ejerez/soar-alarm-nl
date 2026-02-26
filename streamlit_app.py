import streamlit as st
import asyncio
import nest_asyncio
import traceback

from datetime import datetime, time
from os import path
from streamlit_cookies_controller import CookieController
from dotmap import DotMap
from time import sleep
from streamlit_javascript import st_javascript

from backend import *
from tab_map_forecast import disp_map_forecast
from tab_edit_points import disp_edit_points
from tab_point_forecast import disp_point_forecast
from tab_settings import disp_settings

# Monkey patch Streamlit's internal event loop
nest_asyncio.apply()

# Set page config
st.set_page_config(
    page_title="Soaralarm NL",
    page_icon="wind",
    layout="wide"
)

# Main app
st.title("Soaralarm NL")

st_theme = st_javascript("""window.getComputedStyle(window.parent.document.getElementsByClassName("stApp")[0]).getPropertyValue("color-scheme")""")
if st_theme == "dark":
    st.session_state.dark_theme = True
else:
    st.session_state.dark_theme = False

cookies = CookieController()

if 'user' not in st.session_state:
    try:
        user_data_cookies = {cookie: cookies.get(cookie) for cookie in ["user_model", "user_time_range"]}
        sleep(0.7)
    except:
        user_data_cookies = {}
    
    user_data = {}

    for key in user_data_cookies:
        if key.startswith("user_"):
            user_data[key.lstrip("user_")] = user_data_cookies[key]
    
    if 'time_range' in user_data and user_data['time_range'] is not None:
        user_data['time_range'] = (time.fromisoformat(user_data['time_range'][0]), time.fromisoformat(user_data['time_range'][1]))
        st.session_state.user = DotMap(user_data)
    else:
        st.session_state.user = DotMap()

st.session_state.time = datetime.now()

if 'remove_forecast' not in st.session_state:
    st.session_state.remove_forecast = False

if 'forecast' not in st.session_state and path.isfile("forecast.pkl"):
    load_forecast()

if st.session_state.remove_forecast:
    try:
        remove("forecast.pkl")
        st.session_state.remove_forecast = False
    except:
        pass

if 'remove_measurements' not in st.session_state:
    st.session_state.remove_measurements = False

if 'measurements' not in st.session_state and path.isfile("measurements.pkl"):
    load_measurements()

if st.session_state.remove_measurements:
    try:
        remove("measurements.pkl")
        st.session_state.remove_measurements = False
    except:
        pass

if 'soar_points' not in st.session_state:
    load_points()

st.session_state.therm_points = [
        {"lat": 50.398975, "lon": 5.887711, "name": "Coo (West)", "start_heading_range": 270.0, "end_heading_range": 90.0, "max_wind_speed": 30.0, "preset": True}
    ]

if 'user' not in st.session_state:
    st.session_state.user = DotMap()
if 'model' not in st.session_state.user or st.session_state.user.model == None:
    st.session_state.user.model = "KNMI"
if 'time_range' not in st.session_state.user or st.session_state.user.time_range == None:
    st.session_state.user.time_range = (time(00, 00), time(23, 59))

if 'selected_point_idx' not in st.session_state:
    st.session_state.selected_point_idx = 0
if 'selected_date_idx' not in st.session_state:
    st.session_state.selected_date_idx = 1
if 'update_forecast' not in st.session_state:
    st.session_state.update_forecast = False
if 'update_measurements' not in st.session_state:
    st.session_state.update_measurements = False
if 'updating_forecast' not in st.session_state:
    st.session_state.updating_forecast = False
if 'updating_measurements' not in st.session_state:
    st.session_state.updating_measurements = False
if 'update_disp_forecast' not in st.session_state:
    st.session_state.update_disp_forecast = False

if 'forecast' in st.session_state and 'time' in st.session_state.forecast:
    if (st.session_state.time - st.session_state.forecast['time']).total_seconds() >= 3600:
        print("update forecast")
        st.session_state.update_forecast = True
    else:
        st.session_state.update_forecast = False

if 'measurements' in st.session_state and 'time' in st.session_state.measurements:
    if (st.session_state.time - st.session_state.measurements['time']).total_seconds() >= 900:
        print("update_measurements")
        st.session_state.update_measurements = True
    else:
        st.session_state.update_measurements = False

if 'current_date' not in st.session_state or st.session_state.update_forecast:
    st.session_state.current_date = datetime.now().date()

# Date selector at the top
if 'day_list' not in st.session_state or st.session_state.update_forecast:
    week_day = datetime.today().weekday()
    week_days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    st.session_state.day_list = ["Yesterday", "Today", "Tomorrow", week_days_list[(week_day+2)%7], week_days_list[(week_day+3)%7], week_days_list[(week_day+4)%7], week_days_list[(week_day+5)%7], week_days_list[(week_day+6)%7]]

if 'mode' not in st.session_state.user:
    st.session_state.user.mode = 'soar'

# Initialize forecast data if not already loaded
if 'forecast' not in st.session_state or len(st.session_state.forecast) == 0:
    st.session_state.update_forecast = True

if 'measurements' not in st.session_state or len(st.session_state.measurements) == 0:
    st.session_state.update_measurements = True  

if 'disp_forecast' not in st.session_state or len(st.session_state.disp_forecast) == 0:
    st.session_state.update_disp_forecast = True

# Create tabs
tabs=["Map Forecast", "Point Forecast", "Settings"] #"Edit Points (not working yet)", 

tab = st.segmented_control(
    'Tabs',
    options=tabs,
    selection_mode="single",
    default=tabs[0]
)

#st.header("Date Selection")
selected_date = st.selectbox(
    "Select Date",
    options=st.session_state.day_list,
    index=st.session_state.selected_date_idx,
    key="selected_date"
)

selected_date_idx = st.session_state.day_list.index(selected_date)

if selected_date_idx != st.session_state.selected_date_idx:
    st.session_state.selected_date_idx = selected_date_idx

#Update forecasts
if st.session_state.update_forecast and not st.session_state.updating_forecast:
    st.session_state.update_forecast = False
    st.session_state.updating_forecast = True
    print("updating forecast")
    asyncio.run(make_forecast())

if st.session_state.update_measurements and not st.session_state.updating_measurements:
    st.session_state.update_measurements = False
    st.session_state.updating_measurements = True
    print("updating measurements")
    asyncio.run(make_measurements())

if 'forecast' in st.session_state and st.session_state.update_disp_forecast:
    make_disp_forecast()

if tab == tabs[0]:
    if 'disp_forecast' in st.session_state:
        try:
            disp_map_forecast(st.session_state)
        except Exception:
            print("Map Forecast Tab \n")
            traceback.print_exc()
if tab == tabs[1]:
    if 'forecast' in st.session_state:
        try:
            disp_point_forecast(st.session_state)
        except Exception:
            print("Point Forecast Tab \n")
            traceback.print_exc()
#if tab == tabs[2]:
    #disp_edit_points(st.session_state)
    #st.write("Feature under development!")
if tab == tabs[2]:
    try:
        disp_settings(st.session_state)
    except Exception:
        print("Settings Tab \n")
        traceback.print_exc()

