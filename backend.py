import streamlit as st
import pickle

from json import load
from os import remove
from datetime import datetime

from process_forecast import *
from make_gis_map import *
from get_measured_data import get_wind_measurements

def load_points():
    with open("soar_points.json", "r") as f:
        st.session_state.soar_points = load(f)

def load_forecast():
    try:
        with st.spinner(text="Loading previous forecasts..."):
            with open("forecast.pkl", "rb") as f:
                st.session_state.forecast = pickle.load(f)
    except:
        remove("forecast.pkl")

def load_measurements():
    try:
        with st.spinner(text="Loading previous measurements..."):
            with open("measurements.pkl", "rb") as f:
                st.session_state.measurements = pickle.load(f)
    except:
        remove("measurements.pkl")

def make_forecast():
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

def make_measurements():
    st.session_state.update_measurements = False
    
    print("Getting measurements")
    with st.spinner("Fetching measurements..."):
        st.session_state.measurements = {}

        st.session_state.measurements = get_wind_measurements()
        st.session_state.measurements['time'] = datetime.now()
        
        with open("measurements.pkl", "wb") as f:
            pickle.dump(st.session_state.measurements, f, protocol=pickle.HIGHEST_PROTOCOL)

def make_disp_forecast():
    with st.spinner("Processing forecast..."):
        st.session_state.update_forecast = False
        st.session_state.update_disp_forecast = False
        st.session_state.disp_forecast = {}
    
        st.session_state.disp_forecast['soar_kmni'] = forecast_display_soar(st.session_state.forecast['soar_kmni'])
        st.session_state.disp_forecast['soar_ecmwf'] = forecast_display_soar(st.session_state.forecast['soar_ecmwf'])
        st.session_state.disp_forecast['therm'] = forecast_display_therm(st.session_state.forecast['therm'])


