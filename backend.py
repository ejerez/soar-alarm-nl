import streamlit as st
import pickle
import asyncio

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
        #with st.spinner(text="Loading previous forecasts..."):
        with open("forecast.pkl", "rb") as f:
            st.session_state.forecast = pickle.load(f)
    except:
        pass
        #remove("forecast.pkl")

def load_measurements():
    try:
        #with st.spinner(text="Loading previous measurements..."):
        with open("measurements.pkl", "rb") as f:
            st.session_state.measurements = pickle.load(f)
    except:
        pass
        #remove("measurements.pkl")

async def make_forecast():
    print("Getting forecasts")
    st.session_state.update_forecast = False
    
    #with st.spinner("Fetching forecast..."):
    st.session_state.raw_forecast = {}
    st.session_state.forecast = {}

    getting_forecast_knmi = asyncio.create_task(get_forecast_soar(model="knmi_seamless"))
    getting_forecast_ecmwf = asyncio.create_task(get_forecast_soar(model="ecmwf_ifs"))
    
    await getting_forecast_knmi
    await getting_forecast_ecmwf

    processing_forecast_knmi = asyncio.create_task(process_soar_forecast(model="soar_knmi"))
    processing_forecast_ecmwf = asyncio.create_task(process_soar_forecast(model="soar_ecmwf"))

    await processing_forecast_knmi
    await processing_forecast_ecmwf

    #st.session_state.forecast['therm'] = process_therm_forecast(get_forecast_therm())
    
    st.session_state.forecast['time'] = datetime.now()

    with open("forecast.pkl", "wb") as f:
        pickle.dump(st.session_state.forecast, f, protocol=pickle.HIGHEST_PROTOCOL)

async def make_measurements():
    st.session_state.update_measurements = False
    
    #with st.spinner("Fetching measurements..."):
    st.session_state.measurements = {}

    getting_measurements = asyncio.create_task(get_wind_measurements())
    await getting_measurements

    st.session_state.measurements['time'] = datetime.now()
    with open("measurements.pkl", "wb") as f:
        pickle.dump(st.session_state.measurements, f, protocol=pickle.HIGHEST_PROTOCOL)

def make_disp_forecast():
    #if 'soar_knmi' in st.session_state.forecast and 'soar_ecmwf' in st.session_state.forecast:
    #with st.spinner("Processing forecast..."):
    st.session_state.update_forecast = False
    st.session_state.update_disp_forecast = False
    st.session_state.disp_forecast = {}

    st.session_state.disp_forecast['soar_knmi'] = forecast_display_soar(st.session_state.forecast['soar_knmi'])
    st.session_state.disp_forecast['soar_ecmwf'] = forecast_display_soar(st.session_state.forecast['soar_ecmwf'])
    #st.session_state.disp_forecast['therm'] = forecast_display_therm(st.session_state.forecast['therm'])


