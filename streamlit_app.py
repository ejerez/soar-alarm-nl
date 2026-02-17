import streamlit as st
from time import sleep

from forecast import *
from gis_map import *
from tab_map_forecast import disp_map_forecast
from tab_edit_points import disp_edit_points
from tab_point_forecast import disp_point_forecast
from tab_settings import disp_settings

from pickle import dump, load, HIGHEST_PROTOCOL

# Set page config
st.set_page_config(
    page_title="Soaralarm NL",
    page_icon="wind",
    layout="wide"
)

if 'forecast' not in st.session_state:
    try:
        with open("session_state.pkl", "rb") as f:
            session_state = load(f)
            for key in session_state:
                st.session_state[key] = session_state[key]
    except:
        pass

st.session_state.time = datetime.now()

if 'model' not in st.session_state:
    st.session_state.model = "KNMI"
if 'min_speed' not in st.session_state:
    st.session_state.min_speed = 18
if 'max_speed' not in st.session_state:
    st.session_state.max_speed = 50
if 'soar_points' not in st.session_state:
    st.session_state.soar_points = [
        {"lat": 51.508907, "lon": 3.462018, "heading": 215, "steepness": 45, "name": "Zoutelande (Main Dune)", "preset": True},
        {"lat": 52.502193, "lon": 4.589126, "name": "Wijk aan Zee (North)", "heading": 284, "steepness": 30, "preset": True},
        {"lat": 52.564313, "lon": 4.608334, "name": "Castricum aan Zee", "heading": 279, "steepness": 30, "preset": True},
        {"lat": 52.302953, "lon": 4.475574, "name": "Langevelderslag (Noordwijk)", "heading": 295, "steepness": 30, "preset": True},
        {"lat": 51.740870, "lon": 3.810101, "name": "Renesse (East)", "heading": 13, "steepness": 20, "preset": True},
        {"lat": 51.741337, "lon": 3.760768, "name": "Renesse (West)", "heading": 340, "steepness": 20, "preset": True}
    ]
st.session_state.therm_points = [
        {"lat": 50.398975, "lon": 5.887711, "name": "Coo (West)", "start_heading_range": 270.0, "end_heading_range": 90.0, "max_wind_speed": 30.0, "preset": True}
    ]
if 'selected_point_idx' not in st.session_state:
    st.session_state.selected_point_idx = 0
if 'last_update' not in st.session_state:
    st.session_state.last_update = st.session_state.time    
if 'selected_date_idx' not in st.session_state:
    st.session_state.selected_date_idx = 1
if 'map_key' not in st.session_state:
    st.session_state.map_key = 0

since_update = st.session_state.time - st.session_state.last_update
update_forecast = False
if since_update.total_seconds() >= 3600:
    update_forecast = True
    st.session_state.last_update = st.session_state.time

if 'current_date' not in st.session_state or update_forecast:
    st.session_state.current_date = datetime.now().date()

# Main app
st.title("Soaralarm NL")

# Date selector at the top
if 'day_list' not in st.session_state or update_forecast:
    week_day = datetime.today().weekday()
    week_days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    st.session_state.day_list = ["Yesterday", "Today", "Tomorrow", week_days_list[(week_day+2)%7], week_days_list[(week_day+3)%7], week_days_list[(week_day+4)%7], week_days_list[(week_day+5)%7], week_days_list[(week_day+6)%7]]

if 'mode' not in st.session_state:
    st.session_state.mode = 'soar'

#st.header("Date Selection")
selected_date = st.selectbox(
    "Select Date",
    options=st.session_state.day_list,
    index=st.session_state.selected_date_idx,
)

selected_date_idx = st.session_state.day_list.index(selected_date)

if selected_date_idx != st.session_state.selected_date_idx:
    st.session_state.selected_date_idx = selected_date_idx

# Initialize forecast data if not already loaded
if 'forecast' not in st.session_state or update_forecast:
    st.session_state.forecast = {}
    with st.spinner("Fetching forecast..."):
        st.session_state.forecast['soar_kmni'] = process_soar_forecast(get_forecast_soar(model="knmi_seamless"))
        st.session_state.forecast['soar_ecmwf'] = process_soar_forecast(get_forecast_soar(model="ecmwf_ifs"))
        st.session_state.forecast['therm'] = process_therm_forecast(get_forecast_therm())

if 'disp_forecast' not in st.session_state or update_forecast:
    st.session_state.disp_forecast = {}
    with st.spinner("Processing forecast..."):
        st.session_state.disp_forecast['soar_kmni'] = forecast_display_soar(st.session_state.forecast['soar_kmni'])
        st.session_state.disp_forecast['soar_ecmwf'] = forecast_display_soar(st.session_state.forecast['soar_ecmwf'])
        st.session_state.disp_forecast['therm'] = forecast_display_therm(st.session_state.forecast['therm'])

# Create tabs
tabs=["Map Forecast", "Point Forecast", "Edit Points", "Settings"]

tab = st.segmented_control(
    'Tabs',
    options=tabs,
    selection_mode="single",
    default=tabs[0]
)

if tab == tabs[0]:
    disp_map_forecast(st.session_state)
if tab == tabs[1]:
    disp_point_forecast(st.session_state)
if tab == tabs[2]:
    disp_edit_points(st.session_state)
if tab == tabs[3]:
    disp_settings(st.session_state)

with open("session_state.pkl", "wb") as f:
    dump({key: st.session_state[key] for key in st.session_state if len(key) < 40}, f, protocol=HIGHEST_PROTOCOL)


