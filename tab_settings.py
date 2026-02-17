import streamlit as st

def disp_settings(session_state):
    model = st.selectbox(
            "Select Model for Soar Forecast",
            options=["KNMI", "ECMWF"],
            index=0 if session_state.model == 'KNMI' else 1
            )
    
    if model != session_state.model:
        session_state.model = model
        st.rerun(scope='app')
    
    mode_index = 0 if st.session_state.mode == 'soar' else 1

    #st.header("Mode")
    selected_mode = st.selectbox(
        "Select Mode (not working yet)",
        options=["Soar", "Thermal"],
        index=mode_index,
    )

    st.session_state.mode = 'soar' if selected_mode == 'Soar' else 'thermal'