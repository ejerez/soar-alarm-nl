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

def create_soar_map_forecast(date_idx, model='kmni'):
    """Create a complete map with forecast data for the given date"""
    m = folium.Map(
        location=[52.038516, 4.388762],
        zoom_start=8,
        tiles="OpenStreetMap",
        attr="OpenStreetMap"
    )
    MeasureControl().add_to(m)

    display_forecast = st.session_state.disp_forecast[f"soar_{model}"][date_idx]
    for point_idx, pf in enumerate(display_forecast):
        point = st.session_state.soar_points[point_idx]
        lat, lon = point['lat'], point['lon']
        wind_pizza = pf["wind_pizza"]
        head = np.deg2rad(point['heading'])
        for i, slice in enumerate(wind_pizza):
            min_x = lon + 1.63*0.02*np.min([slice, 5]) * np.sin(head+np.deg2rad(22.5)*i)
            min_y = lat + 0.02*np.min([slice, 5]) * np.cos(head+np.deg2rad(22.5)*i)
            max_x = lon + 1.63*0.02*np.min([slice, 5]) * np.sin(head+np.deg2rad(22.5)*(i+1))
            max_y = lat + 0.02*np.min([slice, 5]) * np.cos(head+np.deg2rad(22.5)*(i+1))

            if i == 0 or i == 360/22.5 - 1:
                color = "green"
            elif i == 1 or i == 360/22.5 - 2:
                color = "orange"
            else:
                color = "red"

            folium.Polygon(
                locations=[[lat, lon], [min_y, min_x], [max_y, max_x]],
                color=color,
                weight=2,
                fill=True,
                fill_color=color,
                fill_opacity=0.5,
            ).add_to(m)

        # Add center marker with different colors for types
        if pf['good_hours'] >= 3:
            marker_color = "green"
        elif pf['good_hours'] > 0 and pf['good_hours'] + pf['marginal_hours'] >= 3:
            marker_color = "yellow"
        elif pf['good_hours'] + pf['marginal_hours'] > 0:
            marker_color = "orange"
        else:
            marker_color = "red"

        folium.CircleMarker(
            location=[lat, lon],
            radius=5,
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            fill_opacity=1,
            popup=f"{point['name']} \n {point['lat']}N°, {point['lon']}E°"
        ).add_to(m)

    return m

def create_therm_map_forecast(date_index):
    """Create a complete map with forecast data for the given date"""
    m = folium.Map(
        location=[52.3, 5.3],
        zoom_start=8,
        tiles="OpenStreetMap",
        attr="OpenStreetMap contributors"
    )
    MeasureControl().add_to(m)

    display_forecast = st.session_state.disp_forecast["therm"][date_index]
    for point_idx, pf in enumerate(display_forecast):
        point = st.session_state.soar_points[point_idx]
        lat, lon = point['lat'], point['lon']
        # Add center marker with different colors for types
        if pf['thermal_hours'] > 2:
            marker_color = "green"
        elif pf['flyable_hours'] > 2:
            marker_color = "orange"
        else:
            marker_color = "red"
        
        folium.CircleMarker(
            location=[lat, lon],
            radius=5,
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            fill_opacity=1,
            popup=f"{point['name']} \n {point['lat']}N°, {point['lon']}E°"
        ).add_to(m)

    return m

def create_editing_map(mode='soar'):
    m = folium.Map(
        location=[52.1326, 5.2913],
        zoom_start=7,
        tiles="OpenStreetMap",
        attr="OpenStreetMap contributors"
    )
    MeasureControl().add_to(m)

    draw = Draw(
        export=True,
        filename="heading_points.geojson",
        position="topleft",
        draw_options={
            "polyline": False,
            "polygon": False,
            "circle": False,
            "rectangle": False,
            "marker": True,
            "circlemarker": False
        }
    )
    draw.add_to(m)

    if mode == 'soar':
        points =st.session_state.soar_points
    else:
        points = st.session_state.therm_points

    for point in points:
        # Use different icons for different types
        icon_type = "wind" if mode == 'soar' else "dove"
        icon_color = "red" if not point.get("preset", False) else "blue"
        folium.Marker(
            location=[point['lat'], point['lon']],
            icon=folium.Icon(color=icon_color, icon=icon_type, prefix="fa"),
            popup=f"{point['name']} \n {point['lat']}N°, {point['lon']}E°"
        ).add_to(m)

    return m