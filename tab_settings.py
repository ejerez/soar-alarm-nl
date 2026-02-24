import streamlit as st

from datetime import datetime, timedelta
from time import sleep
from streamlit_cookies_controller import CookieController
from json import dumps

from json_datetime_encoder import DateTimeEncoder

def disp_settings(session_state):
    model = st.selectbox(
            "Select Model for Soar Forecast (ECMWF may pick points onshore)",
            options=["KNMI", "ECMWF"],
            index=0 if session_state.user.model == 'KNMI' else 1
            )
    
    if model != session_state.user.model:
        session_state.user.model = model
    
    mode_index = 0 if st.session_state.user.mode == 'soar' else 1

    time_range = st.slider(
    "Adjust time range (Affects flyable hours graph)", value=session_state.user.time_range
    )
    
    if time_range != session_state.user.time_range:
        session_state.user.time_range = time_range
    
    #st.header("Mode")
    selected_mode = st.selectbox(
        "Select Mode (not working yet)",
        options=["Soar", "Thermal"],
        index=mode_index,
    )

    st.session_state.user.mode = 'soar' if selected_mode == 'Soar' else 'thermal'

    if st.button("Save Settings"):
        with st.spinner(text="Saving settings..."):
            cookies = CookieController()

            user_data = st.session_state.user.toDict()
            for key in user_data.keys():
                cookies.set(name=f"user_{key}", value=dumps(user_data[key], cls=DateTimeEncoder), expires=datetime.now()+timedelta(days=360))

            st.session_state.update_disp_forecast = True
        
        with st.spinner(text="Reloading app..."):
            sleep(2)
            st.rerun(scope='app')