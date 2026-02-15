import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw, MeasureControl
import numpy as np
from datetime import datetime
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
import plotly.graph_objects as go
from scipy.spatial.transform import Rotation as R

from forecast import *
from gis_map import *

# Set page config
st.set_page_config(
    page_title="Soaralarm NL",
    page_icon="wind",
    layout="wide"
)

if 'mode' not in st.session_state:
    st.session_state.mode = 'soar'
if 'min_speed' not in st.session_state:
    st.session_state.min_speed = 20
if 'max_speed' not in st.session_state:
    st.session_state.max_speed = 60
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
if 'current_date' not in st.session_state:
    st.session_state.current_date = datetime.now().date()
if 'selected_date_idx' not in st.session_state:
    st.session_state.selected_date_idx = 1
if 'map_key' not in st.session_state:
    st.session_state.map_key = 0

# Main app
st.title("Soaralarm NL")

# Date selector at the top
if 'day_list' not in st.session_state:
    week_day = datetime.today().weekday()
    week_days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    st.session_state.day_list = ["Yesterday", "Today", "Tomorrow", week_days_list[week_day+2], week_days_list[week_day+3], week_days_list[week_day+4], week_days_list[week_day+5], week_days_list[week_day+6]]

st.header("Date Selection")
selected_date_idx = st.selectbox(
    "Select Date",
    options=st.session_state.day_list,
    index=st.session_state.selected_date_idx,
)

if selected_date_idx != st.session_state.selected_date_idx:
    st.session_state.selected_date_idx = selected_date_idx

# Initialize forecast data if not already loaded
if 'forecast' not in st.session_state:
    st.session_state.forecast = {}
    with st.spinner("Fetching forecast..."):
        st.session_state.forecast['soar_kmni'] = process_soar_forecast(get_forecast_soar_kmni())
        st.session_state.forecast['soar_ecmwf'] = process_soar_forecast(get_forecast_soar_ecmwf())
        st.session_state.forecast['therm'] = process_therm_forecast(get_forecast_therm())

if 'disp_forecast' not in st.session_state:
    st.session_state.disp_forecast = {}
    with st.spinner("Processing forecast..."):
        st.session_state.disp_forecast['soar_kmni'] = forecast_display_soar(st.session_state.forecast['soar_kmni'])
        st.session_state.disp_forecast['soar_ecmwf'] = forecast_display_soar(st.session_state.forecast['soar_ecmwf'])
        st.session_state.disp_forecast['therm'] = forecast_display_therm(st.session_state.forecast['therm'])

# Create tabs
tab1, tab2, tab3 = st.tabs(["Map Forecast", "Point Forecast", "Edit Points"])

with tab1:
    # Create and display map with current date's forecast
    if st.session_state.mode == 'soar':
        current_map = create_soar_map_forecast(st.session_state.current_date_idx)
    else:
        current_map = create_therm_map_forecast(st.session_state.current_date_idx)

    st_folium(current_map, width=1000, height=600, key=f"map_{st.session_state.current_date_idx}")

with tab2:
    # Point selection
    if st.session_state.mode == 'soar':
        point_options = [point['name'] for point in st.session_state.soar_points]
    else:
        point_options = [point['name'] for point in st.session_state.therm_points]
    selected_point_idx = st.selectbox(
        "Select Point",
        options=point_options,
        index=st.session_state.selected_point,
        key="point_selector"
    )

    if st.session_state.selected_point_idx != selected_point_idx:
        st.session_state.selected_point_idx = selected_point_idx

    # Get forecast data
    if st.session_state.mode == 'soar':
        selected_point = st.session_state.soar_points[st.session_state.selected_point_idx]
        day_forecast = st.session_state.forecast["soar_kmni"][st.session_state.selected_date_idx][st.session_state.selected_point_idx]
    else:
        selected_point = st.session_state.therm_points[st.session_state.selected_point_idx]
        day_forecast = st.session_state.forecast["therm"][st.session_state.selected_date_idx][st.session_state.selected_point_idx]

    if day_forecast["time"]:
        # Wind Speed and Gust Speed Graph
        st.subheader("Wind Speed and Gusts")
        fig_wind = go.Figure()

        fig_wind.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["wind_speed"],
            name="Wind Speed",
            line=dict(color='blue', width=4),
            line_shape='spline',
            fill='tonexty',
            fillcolor='blue'
        ))

        fig_wind.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["wind_gusts"],
            name="Gust Speed",
            line=dict(color='orange', width=4),
            line_shape='spline',
            fill='tonexty',
            fillcolor='orange'
        ))

        if st.session_state_mode == 'soar':
            fig_wind.add_hrect(y0=st.session_state.min_speed, y1=st.session_state.max_speed,
                             fillcolor="rgba(153,255,51,0.7)", opacity=0.5, line_width=0)
        else:  # Thermal
            max_wind = selected_point.get("max_wind_speed", 30)
            fig_wind.add_hrect(y0=0, y1=max_wind, fillcolor="rgba(153,255,51,0.7)", opacity=0.5, line_width=0)

        fig_wind.update_layout(
            title="Wind Speed and Gusts",
            xaxis_title="Time",
            yaxis_title="Speed (km/h)",
            hovermode="x unified",
            height=400
        )

        st.plotly_chart(fig_wind, width='stretch')

        # Wind Direction Graph
        st.subheader("Wind Direction")
        fig_dir = go.Figure()

        if selected_point["type"] == "Soaring":
            lower_bound = selected_point["heading"] - 45
            lower_ideal = selected_point["heading"] - 22.5
            upper_ideal = selected_point["heading"] + 22.5
            upper_bound = selected_point["heading"] + 45

            fig_dir.add_hrect(y0=lower_ideal, y1=upper_ideal, fillcolor="rgba(153,255,51,0.7)", opacity=0.5, line_width=0)
            fig_dir.add_hrect(y0=lower_bound, y1=lower_ideal, fillcolor="rgba(255,153,51,0.7)", opacity=0.5, line_width=0)
            fig_dir.add_hrect(y0=upper_ideal, y1=upper_bound, fillcolor="rgba(255,153,51,0.7)", opacity=0.5, line_width=0)
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
            line=dict(color='black', width=2),
            line_shape='spline'
        ))

        if selected_point["type"] == "Soaring":
            fig_dir.add_hline(y=selected_point["heading"], line_dash="dot", line_color="grey",
                            annotation_text=f"Ideal ({selected_point['heading']}°)")

        fig_dir.update_layout(
            title=f"Wind Direction (Acceptable Range)",
            xaxis_title="Time",
            yaxis_title="Direction (°)",
            hovermode="x unified",
            height=400
        )

        st.plotly_chart(fig_dir, width='stretch')

        # Temperature and Precipitation Graph
        st.subheader("Temperature and Precipitation")
        fig_temp_precip = go.Figure()

        fig_temp_precip.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["temperature"],
            name="Temperature",
            line=dict(color='orange', width=2),
            yaxis="y1",
            line_shape='spline'
        ))

        fig_temp_precip.add_trace(go.Bar(
            x=day_forecast["time"],
            y=day_forecast["precipitation"],
            name="Precipitation",
            marker_color='lightblue',
            yaxis="y2",
        ))

        # Add visibility threshold line
        visibility_threshold = 0.5 if selected_point["type"] == "Thermal" else 0.1
        fig_temp_precip.add_hline(y=visibility_threshold, line_dash="dot", line_color="red",
                                annotation_text=f"Min Visibility: {visibility_threshold}")

        fig_temp_precip.update_layout(
            title="Temperature, Precipitation and Visibility",
            xaxis_title="Time",
            yaxis=dict(title="Temperature (°C)", side="left"),
            yaxis2=dict(title="Precipitation (mm)", overlaying="y", side="right"),
            hovermode="x unified",
            height=400
        )

        st.plotly_chart(fig_temp_precip, width='stretch')

        # Summary metrics
        st.subheader("General Forecast Data")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Sunrise", day_forecast["sunrise"].strftime('%H:%M'))
        with col2:
            st.metric("Sunset", day_forecast["sunset"].strftime('%H:%M'))
        with col3:
            avg_wind = np.mean(day_forecast["wind_speed"])
            st.metric("Avg Wind Speed", f"{avg_wind:.1f} km/h")

with tab3:
    m_edit = create_editing_map()
    output = st_folium(m_edit, width=1000, height=600)

    if output.get("last_active_drawing"):
        drawn_feature = output["last_active_drawing"]
        if drawn_feature["geometry"]["type"] == "Point":
            lon, lat = drawn_feature["geometry"]["coordinates"]
            new_id = max([p['id'] for p in st.session_state.points]) + 1 if st.session_state.points else 1

            with st.form(key=f"point_{new_id}_form"):
                st.subheader(f"Configure Point {new_id}")

                col1, col2 = st.columns(2)
                with col1:
                    point_type = st.selectbox("Point Type", ["Soaring", "Thermal"], index=0)
                    name = st.text_input("Name of location")

                if point_type == "Soaring":
                    with col2:
                        heading = st.number_input("Best wind heading in degrees", min_value=0, max_value=360, value=0, step=1)
                        steepness = st.number_input("Steepness of the slope in degrees", min_value=0, max_value=90, value=0, step=1)
                else:  # Thermal
                    with col2:
                        col2a, col2b = st.columns(2)
                        with col2a:
                            start_heading = st.number_input("Start Heading", min_value=0, max_value=360, value=0, step=1)
                        with col2b:
                            end_heading = st.number_input("End Heading", min_value=0, max_value=360, value=360, step=1)
                        max_wind_speed = st.number_input("Max Wind Speed (km/h)", min_value=0, max_value=100, value=30, step=1)

                if st.form_submit_button("Save Point"):
                    new_point = {
                        "id": new_id,
                        "lat": lat,
                        "lon": lon,
                        "name": name,
                        "type": point_type,
                        "preset": False
                    }

                    if point_type == "Soaring":
                        new_point.update({
                            "heading": float(heading),
                            "steepness": float(steepness)
                        })
                    else:
                        new_point.update({
                            "start_heading_range": float(start_heading),
                            "end_heading_range": float(end_heading),
                            "max_wind_speed": float(max_wind_speed)
                        })

                    st.session_state.points.append(new_point)
                    st.success(f"{name} ({point_type}) saved!")
                    # Clear cached forecasts since points changed
                    st.session_state.forecast = None
                    st.session_state.all_day_forecasts = {}
                    st.session_state.all_display_forecasts = {}
                    st.rerun()

    st.subheader("Manage Points")
    if st.session_state.points:
        points_df = pd.DataFrame(st.session_state.points)
        points_df['Delete'] = False
        points_df.loc[points_df['preset'] == True, 'Delete'] = None

        # Custom column config based on point type
        column_config = {
            "name": st.column_config.TextColumn("Name"),
            "type": st.column_config.TextColumn("Type", disabled=True),
            "lat": st.column_config.NumberColumn("Latitude", format="%.5f"),
            "lon": st.column_config.NumberColumn("Longitude", format="%.5f"),
            "preset": st.column_config.CheckboxColumn("Preset", disabled=True),
            "Delete": st.column_config.CheckboxColumn("Delete?")
        }

        # Add type-specific columns
        if any(p["type"] == "Soaring" for p in st.session_state.points):
            column_config.update({
                "heading": st.column_config.NumberColumn("Heading (°)"),
                "steepness": st.column_config.NumberColumn("Steepness")
            })

        if any(p["type"] == "Thermal" for p in st.session_state.points):
            column_config.update({
                "start_heading_range": st.column_config.NumberColumn("Start Heading (°)"),
                "end_heading_range": st.column_config.NumberColumn("End Heading (°)"),
                "max_wind_speed": st.column_config.NumberColumn("Max Wind Speed")
            })

        edited_df = st.data_editor(
            points_df,
            column_config=column_config,
            num_rows="dynamic",
            hide_index=True,
            disabled=["preset", "type"]
        )

        if edited_df['Delete'].any():
            to_delete = edited_df[(edited_df['Delete'] == True) & (edited_df['preset'] == False)]['id'].tolist()
            if to_delete:
                st.session_state.points = [p for p in st.session_state.points if p['id'] not in to_delete]
                st.success(f"Deleted {len(to_delete)} point(s)")
                # Clear cached forecasts since points changed
                st.session_state.forecast = None
                st.session_state.all_day_forecasts = {}
                st.session_state.all_display_forecasts = {}
                st.rerun()

        # Handle edits for type-specific columns
        editable_columns = ['name', 'lat', 'lon']
        if any(p["type"] == "Soaring" for p in st.session_state.points):
            editable_columns.extend(['heading', 'steepness'])
        if any(p["type"] == "Thermal" for p in st.session_state.points):
            editable_columns.extend(['start_heading_range', 'end_heading_range', 'max_wind_speed'])

        if not edited_df[editable_columns].equals(points_df[editable_columns]):
            st.session_state.points = edited_df.drop('Delete', axis=1).to_dict('records')
            st.success("Points updated!")
            # Clear cached forecasts since points changed
            st.session_state.forecast = None
            st.session_state.all_day_forecasts = {}
            st.session_state.all_display_forecasts = {}
            st.rerun()