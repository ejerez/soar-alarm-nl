import streamlit as st
import numpy as np
import plotly.graph_objects as go

from streamlit_javascript import st_javascript
from datetime import timedelta

from process_forecast import *

def disp_point_forecast(session_state):

    st_theme = st_javascript("""window.getComputedStyle(window.parent.document.getElementsByClassName("stApp")[0]).getPropertyValue("color-scheme")""")
    if st_theme == "dark":
        dark_theme = True
    else:
        dark_theme = False

    # Point selection
    if session_state.user.mode == 'soar':
        point_options = [point['name'] for point in session_state.soar_points]
    else:
        point_options = [point['name'] for point in session_state.therm_points]
    
    select_point = st.selectbox(
        "Select Point",
        options=point_options,
        index=session_state.selected_point_idx,
        key="point_selector"
    )

    selected_point_idx = point_options.index(select_point)

    if session_state.selected_point_idx != selected_point_idx:
        session_state.selected_point_idx = selected_point_idx

    model = "soar_kmni" if session_state.user.model == "KNMI" else "soar_ecmwf"

    # Get forecast data
    if session_state.user.mode == 'soar':
        selected_point = session_state.soar_points[session_state.selected_point_idx]
        day_forecast = session_state.forecast[model][session_state.selected_date_idx][session_state.selected_point_idx]
    else:
        selected_point = session_state.therm_points[session_state.selected_point_idx]
        day_forecast = session_state.forecast["therm"][session_state.selected_date_idx][session_state.selected_point_idx]

    button_location = st.link_button('Directions (Google Maps)', rf"https://www.google.com/maps/place/{selected_point['lat']}N+{selected_point['lon']}E")

    if day_forecast["time"]:
    
        # Wind Speed and Gust Speed Graph
        st.subheader("Wind Speed and Gusts")
        fig_wind = go.Figure()

        fig_wind.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["wind_speed"],
            name="Wind Speed",
            line=dict(color='blue', width=0),
            line_shape='spline',
            fill='tonexty',
            fillcolor="blue",
            yaxis="y1",
            opacity=0,
            mode="lines"
        ))

        fig_wind.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["wind_gusts"],
            name="Gust Speed",
            line=dict(color='orange', width=0),
            line_shape='spline',
            fill='tonexty',
            fillcolor="orange",
            yaxis="y1",
            opacity=0,
            mode="lines"
        ))

        fig_wind.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["precipitation"],
            name="Precipitation",
            line=dict(color='lightblue', width=0),
            line_shape='spline',
            fill='tonexty',
            fillcolor='lightblue',
            mode="lines",
            yaxis="y2",
            opacity=0
        ))

        #Get measurements
        sunrise = (day_forecast["sunrise"]).replace(minute=0, second=0, microsecond=0)+timedelta(hours=-1)
        sunset = (day_forecast["sunset"]).replace(minute=0, second=0, microsecond=0)+timedelta(hours=1)

        wind_meas = session_state.measurements[selected_point["station"]]["WINDSHD"].truncate(before=sunrise, after=sunset)

        fig_wind.add_trace(go.Scatter(
            x=wind_meas.index.to_pydatetime(), 
            y=np.asarray(wind_meas['Meetwaarde.Waarde_Numeriek'].values.tolist())*3.6,
            name="Measured Windspeed",
            line=dict(color='white' if dark_theme else 'black', width=0.5),
            line_shape='linear',
            yaxis="y1",
            opacity=1,
            mode="markers"
        ))

        if session_state.user.mode == 'soar':
            fig_wind.add_hrect(y0=selected_point['wind_range'][0], y1=selected_point['wind_range'][1],
                                fillcolor="rgba(153,255,51,0.7)", opacity=0.5, line_width=0)
        else:  # Thermal
            max_wind = selected_point.get("max_wind_speed", 30)
            fig_wind.add_hrect(y0=0, y1=max_wind, fillcolor="rgba(153,255,51,0.7)", opacity=0.5, line_width=0)

        fig_wind.update_xaxes(range=[sunrise+timedelta(hours=1), sunset+timedelta(hours=1)])

        fig_wind.update_layout(
            title="Wind Speed and Gusts",
            xaxis=dict(title="Time", fixedrange=True),
            yaxis=dict(title="Speed (km/h)", side="left", fixedrange=True),
            yaxis2=dict(title="Precipitation (mm)", overlaying="y", side="right", fixedrange=True),
            hovermode="x unified",
            height=400,
            legend=dict(orientation="h")
        )

        st.plotly_chart(fig_wind, width='stretch', on_select='ignore')

        # Wind Direction Graph
        st.subheader("Wind Direction")
        fig_dir = go.Figure()

        if session_state.user.mode == 'soar':
            lower_bound = selected_point["heading"] + selected_point["head_range"][0]
            lower_ideal = selected_point["heading"] - 22.5
            upper_ideal = selected_point["heading"] + 22.5
            upper_bound = selected_point["heading"] + selected_point["head_range"][1]

            fig_dir.add_hrect(y0=lower_ideal, y1=upper_ideal, fillcolor="rgba(153,255,51,0.7)", opacity=0.8 if dark_theme else 0.5, line_width=0)
            fig_dir.add_hrect(y0=lower_bound, y1=lower_ideal, fillcolor="rgba(255,153,51,0.7)", opacity=0.8 if dark_theme else 0.5, line_width=0)
            fig_dir.add_hrect(y0=upper_ideal, y1=upper_bound, fillcolor="rgba(255,153,51,0.7)", opacity=0.8 if dark_theme else 0.5, line_width=0)
        else:  # Thermal
            start_heading = selected_point.get("start_heading_range", 0)
            end_heading = selected_point.get("end_heading_range", 360)
            if start_heading <= end_heading:
                fig_dir.add_hrect(y0=start_heading, y1=end_heading,
                                fillcolor="rgba(153,255,51,0.7)", opacity=0.5, line_width=0)
            else:
                fig_dir.add_hrect(y0=start_heading, y1=360,
                                fillcolor="rgba(153,255,51,0.7)", opacity=0.5, line_width=0)
                fig_dir.add_hrect(y0=0, y1=end_heading,
                                fillcolor="rgba(153,255,51,0.7)", opacity=0.5, line_width=0)

        fig_dir.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["wind_direction"],
            name="Wind Direction",
            line=dict(color='white' if dark_theme else 'black', width=2, dash='dash'),
            line_shape='spline',
            yaxis="y1",
            mode="lines"
        ))

        #get measurements
        head_meas = session_state.measurements[selected_point["station"]]["WINDRTG"].truncate(before=sunrise, after=sunset)

        fig_dir.add_trace(go.Scatter(
            x=head_meas.index.to_pydatetime(),
            y=np.asarray(head_meas['Meetwaarde.Waarde_Numeriek'].values.tolist()),
            name="Wind Direction",
            line=dict(color='white' if dark_theme else 'black', width=1),
            line_shape='linear',
            yaxis="y1",
            mode="lines"
        ))

        if session_state.user.mode == 'soar':
            fig_dir.add_hline(y=selected_point["heading"], line_dash="dot", line_color="grey",
                            annotation_text=f"Ideal ({selected_point['heading']}°)")

        fig_dir.update_layout(
            title=f"Wind Direction (Acceptable Range)",
            xaxis=dict(title="Time", fixedrange=True),
            yaxis=dict(title="Direction (°)", fixedrange=True),
            hovermode="x unified",
            height=400,
            legend=dict(orientation="h")
        )

        st.plotly_chart(fig_dir, width='stretch', on_select='ignore')

        # Temperature and Precipitation Graph
        st.subheader("Temperature and Visibility")
        fig_temp_precip = go.Figure()

        fig_temp_precip.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["temperature"],
            name="Temperature",
            line=dict(color='orange', width=2),
            yaxis="y1",
            line_shape='spline',
            mode="lines"
        ))

        fig_temp_precip.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["visibility"],
            name="Visibility",
            line=dict(color='white' if dark_theme else 'black', width=2),
            yaxis="y2",
            line_shape='spline',
            mode="lines"
        ))

        # Add visibility threshold line
        visibility_threshold = 100 if session_state.user.mode == 'soar' else 0.5
        fig_temp_precip.add_hline(y=visibility_threshold, line_dash="dot", line_color="red",
                                annotation_text=f"Min Visibility: {visibility_threshold}", yref="y2")

        fig_temp_precip.update_layout(
            title="Temperature and Visibility",
            xaxis=dict(title="Time", fixedrange=True),
            yaxis=dict(title="Temperature (°C)", side="left", fixedrange=True),
            yaxis2=dict(title="Visibility (m)", overlaying="y", side="right", fixedrange=True),
            hovermode="x unified",
            height=400,
            legend=dict(orientation="h")
        )

        st.plotly_chart(fig_temp_precip, width='stretch', on_select='ignore')

        st.write(f"Weather station {selected_point['station']} used for measured data at {selected_point['name']}:",
                 f"\n{session_state.measurements[selected_point['station']]['lat']}°N, {session_state.measurements[selected_point['station']]['lon']}°E",
                 "\n\nForecast point requested offshore:",
                 f"\n{selected_point['lat']}°N, {selected_point['lon']}°E")


        