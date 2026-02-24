import streamlit as st

from streamlit_cookies_controller import CookieController
from datetime import datetime, timedelta, time
from os import path, remove
from json import loads, dumps, load, dump
from dotmap import DotMap
from time import sleep
import pickle

from process_forecast import *
from make_gis_map import *
from get_measured_data import get_wind_measurements
from tab_map_forecast import disp_map_forecast
from tab_edit_points import disp_edit_points
from tab_point_forecast import disp_point_forecast
from tab_settings import disp_settings

# Set page config
st.set_page_config(
    page_title="Soaralarm NL",
    page_icon="wind",
    layout="wide"
)

# Main app
st.title("Soaralarm NL")

cookies = CookieController()

st.session_state.time = datetime.now()

if 'forecast' not in st.session_state and path.isfile("forecast.pkl"):
    try:
        with st.spinner(text="Loading previous forecasts..."):
            with open("forecast.pkl", "rb") as f:
                st.session_state.forecast = pickle.load(f)
    except:
        remove("forecast.pkl")

if 'measurements' not in st.session_state and path.isfile("measurements.pkl"):
    try:
        with st.spinner(text="Loading previous measurements..."):
            with open("measurements.pkl", "rb") as f:
                st.session_state.measurements = pickle.load(f)
    except:
        remove("measurements.pkl")

if 'user' not in st.session_state:
    with st.spinner(text="Loading data from previous session..."):
        user_data_cookies = cookies.getAll()
        sleep(3)
        
        user_data = {}

        for key in user_data_cookies:
            if key.startswith("user_"):
                user_data[key.lstrip("user_")] = user_data_cookies[key]
        
        if 'time_range'in user_data:
            user_data['time_range'] = (time.fromisoformat(user_data['time_range'][0]), time.fromisoformat(user_data['time_range'][1]))

        if len(user_data) > 0:
            st.session_state.user = DotMap(user_data)
        else:
            st.session_state.user = DotMap()

if 'soar_points' not in st.session_state:
    st.session_state.soar_points = [
        {"lat": 51.492894, "lon": 3.499841, "offshore_lat": 51.486225, "offshore_lon": 3.415339, "name": "Zoutelande (Main Dune)", "station": "cadzand.1", "heading": 222, "head_range": [-55, 45], "wind_range": [18, 50], "preset": True},
        {"lat": 52.502193, "lon": 4.589126, "offshore_lat": 52.503636, "offshore_lon": 4.528322, "name": "Wijk aan Zee (North)", "station": "ijmuiden.buitenhaven", "heading": 284, "head_range": [-45, 45], "wind_range": [20, 50], "preset": True},
        {"lat": 52.564313, "lon": 4.608334, "offshore_lat": 52.564746, "offshore_lon": 4.538524, "name": "Castricum aan Zee", "station": "ijmuiden.buitenhaven", "heading": 279, "head_range": [-45, 45], "wind_range": [20, 50], "preset": True},
        {"lat": 52.302953, "lon": 4.475574, "offshore_lat": 52.319222, "offshore_lon": 4.421669, "name": "Langevelderslag (Noordwijk)", "station": "ijmuiden.buitenhaven", "heading": 295, "head_range": [-45, 45], "wind_range": [20, 50], "preset": True},
        {"lat": 51.866840, "lon": 4.052526, "offshore_lat": 51.885594, "offshore_lon": 3.946932, "name": "Rockanje (South)", "station": "stellendam.haringvlietsluizen.schuif1", "heading": 213, "head_range": [-45, 45], "wind_range": [20, 50], "preset": True},
        {"lat": 51.740870, "lon": 3.810101, "offshore_lat": 51.778656, "offshore_lon": 3.777647, "name": "Renesse (East)", "station": "brouwersdam.brouwershavensegat.2", "heading": 13, "head_range": [-45, 45], "wind_range": [25, 50], "preset": True},
        {"lat": 51.741337, "lon": 3.760768, "offshore_lat": 51.778656, "offshore_lon": 3.777647, "name": "Renesse (West)", "station": "brouwersdam.brouwershavensegat.2", "heading": 340, "head_range": [-45, 45], "wind_range": [25, 50], "preset": True}
    ]
st.session_state.therm_points = [
        {"lat": 50.398975, "lon": 5.887711, "name": "Coo (West)", "start_heading_range": 270.0, "end_heading_range": 90.0, "max_wind_speed": 30.0, "preset": True}
    ]
    
if 'model' not in st.session_state.user:
    st.session_state.user.model = "KNMI"
if 'time_range' not in st.session_state.user:
    st.session_state.user.time_range = (time(00, 00), time(23, 59))

if 'selected_point_idx' not in st.session_state:
    st.session_state.selected_point_idx = 0
if 'selected_date_idx' not in st.session_state:
    st.session_state.selected_date_idx = 1
if 'update_forecast' not in st.session_state:
    st.session_state.update_forecast = False
if 'update_measurements' not in st.session_state:
    st.session_state.update_measurements = False
if 'update_disp_forecast' not in st.session_state:
    st.session_state.update_disp_forecast = False

if 'forecast' in st.session_state and 'time' in st.session_state.forecast \
    and (st.session_state.time - st.session_state.forecast['time']).total_seconds() >= 3600:
    st.session_state.update_forecast = True

if 'measurements' in st.session_state and 'time' in st.session_state.measurements \
    and (st.session_state.time - st.session_state.measurements['time']).total_seconds() >= 900:
    print("Measurements outdated")
    st.session_state.update_measurements = True

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
if 'forecast' not in st.session_state or st.session_state.update_forecast:
    print("Getting forecasts")
    st.session_state.update_forecast = False
    
    with st.spinner("Fetching forecast..."):
        st.session_state.forecast = {}

        st.session_state.forecast['soar_kmni'] = process_soar_forecast(get_forecast_soar(model="knmi_seamless"))
        st.session_state.forecast['soar_ecmwf'] = process_soar_forecast(get_forecast_soar(model="ecmwf_ifs"))
        st.session_state.forecast['therm'] = process_therm_forecast(get_forecast_therm())
        st.session_state.forecast['time'] = datetime.now()

        with open("forecast.pkl", "wb") as f:
            pickle.dump(st.session_state.forecast, f, protocol=pickle.HIGHEST_PROTOCOL)
            sleep(2)

if 'measurements' not in st.session_state or st.session_state.update_measurements:
    st.session_state.update_measurements = False
    
    print("Getting measurements")
    with st.spinner("Fetching measurements..."):
        st.session_state.measurements = {}

        st.session_state.measurements = get_wind_measurements()
        st.session_state.measurements['time'] = datetime.now()
        
        with open("measurements.pkl", "wb") as f:
            pickle.dump(st.session_state.measurements, f, protocol=pickle.HIGHEST_PROTOCOL)
            sleep(2)

if 'disp_forecast' not in st.session_state or st.session_state.update_forecast or st.session_state.update_disp_forecast:
    with st.spinner("Processing forecast..."):
        st.session_state.update_forecast = False
        st.session_state.update_disp_forecast = False
        st.session_state.disp_forecast = {}
    
        st.session_state.disp_forecast['soar_kmni'] = forecast_display_soar(st.session_state.forecast['soar_kmni'])
        st.session_state.disp_forecast['soar_ecmwf'] = forecast_display_soar(st.session_state.forecast['soar_ecmwf'])
        st.session_state.disp_forecast['therm'] = forecast_display_therm(st.session_state.forecast['therm'])

# Create tabs
tabs=["Map Forecast", "Point Forecast", "Edit Points (not working yet)", "Settings"]

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
)

selected_date_idx = st.session_state.day_list.index(selected_date)

if selected_date_idx != st.session_state.selected_date_idx:
    st.session_state.selected_date_idx = selected_date_idx

if tab == tabs[0]:
    disp_map_forecast(st.session_state)
if tab == tabs[1]:
    disp_point_forecast(st.session_state)
if tab == tabs[2]:
    #disp_edit_points(st.session_state)
    st.write("Feature under development!")
if tab == tabs[3]:
    disp_settings(st.session_state)




