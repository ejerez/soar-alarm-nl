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

st.session_state.time = datetime.now()

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

mode_index = 0 if st.session_state.mode == 'soar' else 1

st.header("Mode")
selected_mode = st.selectbox(
    "Select Mode",
    options=["Soar", "Thermal"],
    index=mode_index,
)

st.session_state.mode = 'soar' if selected_mode == 'Soar' else 'thermal'

st.header("Date Selection")
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
        st.session_state.forecast['soar_kmni'] = process_soar_forecast(get_forecast_soar_kmni())
        st.session_state.forecast['soar_ecmwf'] = process_soar_forecast(get_forecast_soar_ecmwf())
        st.session_state.forecast['therm'] = process_therm_forecast(get_forecast_therm())

if 'disp_forecast' not in st.session_state or update_forecast:
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
        current_map = create_soar_map_forecast(st.session_state.selected_date_idx)
    else:
        current_map = create_therm_map_forecast(st.session_state.selected_date_idx)

    st_folium(current_map, width=1000, height=600, key=f"map_{st.session_state.selected_date_idx}")

    # Temperature and Precipitation Graph
    st.subheader("Flyable Hours Per Day")
    fig_flyable = go.Figure()


    forecast = st.session_state.disp_forecast['soar_kmni']
    good_per_day = []
    marginal_per_day = []
    total_per_day = []
    best_per_day = []
    for date_forecast in forecast:
        points = []
        max_flyable = 0
        max_good = 0
        best = 0
        for index, point_forecast in enumerate(date_forecast):
            good = point_forecast['good_hours']
            marginal = point_forecast['marginal_hours']
            flyable = good+marginal
            if flyable == max_flyable and good > max_good:
                max_good = good
                best = index
            if flyable > max_flyable:
                max_flyable = flyable
                max_good = good
                best = index
            points.append([good, marginal])
        good_per_day.append(points[best][0])
        marginal_per_day.append(points[best][1])
        total_per_day.append(points[best][0]+points[best][1])
        best_per_day.append(best)

    if st.session_state.mode == 'soar':
        best_point_list = [st.session_state.soar_points[idx]['name'] for idx in best_per_day]
    else:
        best_point_list = [st.session_state.therm_points[idx]['name'] for idx in best_per_day]

    fig_flyable.add_trace(go.Bar(
        x=st.session_state.day_list,
        y=marginal_per_day,
        text=best_point_list,
        name="Marginal hours per day",
        marker_color='orange',
        yaxis="y",
    ))

    fig_flyable.add_trace(go.Bar(
        x=st.session_state.day_list,
        y=good_per_day,
        text=best_point_list,
        name="Good hours per day",
        marker_color='green',
        yaxis="y",
    ))

    fig_flyable.update_layout(barmode='stack', legend=dict(orientation="h"))
    st.plotly_chart(fig_flyable, width='stretch', on_select='ignore')

with tab2:
    # Point selection
    if st.session_state.mode == 'soar':
        point_options = [point['name'] for point in st.session_state.soar_points]
    else:
        point_options = [point['name'] for point in st.session_state.therm_points]
    selected_point = st.selectbox(
        "Select Point",
        options=point_options,
        index=st.session_state.selected_point_idx,
        key="point_selector"
    )

    selected_point_idx = point_options.index(selected_point)

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
            line_shape='spline'
        ))

        fig_wind.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["wind_gusts"],
            name="Gust Speed",
            line=dict(color='orange', width=4),
            line_shape='spline'
        ))

        if st.session_state.mode == 'soar':
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
            height=400,
            legend=dict(orientation="h")
        )

        st.plotly_chart(fig_wind, width='stretch', on_select='ignore')

        # Wind Direction Graph
        st.subheader("Wind Direction")
        fig_dir = go.Figure()

        if st.session_state.mode == 'soar':
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

        if st.session_state.mode == 'soar':
            fig_dir.add_hline(y=selected_point["heading"], line_dash="dot", line_color="grey",
                            annotation_text=f"Ideal ({selected_point['heading']}°)")

        fig_dir.update_layout(
            title=f"Wind Direction (Acceptable Range)",
            xaxis_title="Time",
            yaxis_title="Direction (°)",
            hovermode="x unified",
            height=400,
            legend=dict(orientation="h")
        )

        st.plotly_chart(fig_dir, width='stretch', on_select='ignore')

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
        visibility_threshold = 0.1 if st.session_state.mode == 'soar' else 0.5
        fig_temp_precip.add_hline(y=visibility_threshold, line_dash="dot", line_color="red",
                                annotation_text=f"Min Visibility: {visibility_threshold}")

        fig_temp_precip.update_layout(
            title="Temperature, Precipitation and Visibility",
            xaxis_title="Time",
            yaxis=dict(title="Temperature (°C)", side="left"),
            yaxis2=dict(title="Precipitation (mm)", overlaying="y", side="right"),
            hovermode="x unified",
            height=400,
            legend=dict(orientation="h")
        )

        st.plotly_chart(fig_temp_precip, width='stretch', on_select='ignore')

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

            with st.form(key=f"new_point"):
                st.subheader(f"Create Point")

                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Name of location")

                if st.session_state.mode == "soar":
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
                        "lat": lat,
                        "lon": lon,
                        "name": name,
                        "preset": False
                    }

                    if st.session_state.mode == "soar":
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

                    if st.session_state.mode == "soar":
                        st.session_state.soar_points.append(new_point)
                    else:
                        st.session_state.therm_points.append(new_point)
                    st.success(f"{name} saved!")
                    # Clear cached forecasts since points changed
                    st.session_state.forecast = None
                    st.session_state.all_day_forecasts = {}
                    st.session_state.all_display_forecasts = {}
                    st.rerun()

    st.subheader("Manage Points")
    if st.session_state.mode == "soar":
        points_df = pd.DataFrame(st.session_state.soar_points)
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
        if st.session_state.mode == "soar":
            column_config.update({
                "heading": st.column_config.NumberColumn("Heading (°)"),
                "steepness": st.column_config.NumberColumn("Steepness")
            })
        else:
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
                if st.session_state.mode == "soar":
                    st.session_state.soar_points = [p for p in st.session_state.soar_points if p['id'] not in to_delete]
                else:
                    st.session_state.therm_points = [p for p in st.session_state.therm_points if p['id'] not in to_delete]
                st.success(f"Deleted {len(to_delete)} point(s)")
                # Clear cached forecasts since points changed
                st.session_state.forecast = None
                st.session_state.all_day_forecasts = {}
                st.session_state.all_display_forecasts = {}
                st.rerun()

        # Handle edits for type-specific columns
        editable_columns = ['name', 'lat', 'lon']
        if st.session_state.mode == "soar":
            editable_columns.extend(['heading', 'steepness'])
        else:
            editable_columns.extend(['start_heading_range', 'end_heading_range', 'max_wind_speed'])

        if not edited_df[editable_columns].equals(points_df[editable_columns]):
            if st.session_state.mode == "soar":
                st.session_state.soar_points = edited_df.drop('Delete', axis=1).to_dict('records')
            else:
                st.session_state.therm_points = edited_df.drop('Delete', axis=1).to_dict('records')
            st.success("Points updated!")
            # Clear cached forecasts since points changed
            st.session_state.forecast = None
            st.session_state.all_day_forecasts = {}
            st.session_state.all_display_forecasts = {}
            st.rerun()