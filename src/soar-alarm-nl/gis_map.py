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

def create_map_with_forecast(date_index, model='kmni'):
    """Create a complete map with forecast data for the given date"""
    m = folium.Map(
        location=[52.3, 5.3],
        zoom_start=8,
        tiles="OpenStreetMap",
        attr="OpenStreetMap contributors"
    )
    MeasureControl().add_to(m)

    display_forecast = st.session_state.all_display_forecasts.get(date, [])
    for pf in display_forecast:
        point = st.session_state.points[next(i for i, p in enumerate(st.session_state.points) if p["id"] == pf["id"])]
        lat, lon = point['lat'], point['lon']

        if point["type"] == "Soaring":
            head = np.deg2rad(point['heading'])
            for i, slice in enumerate(pf["wind_pizza"]):
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
        else:  # Thermal
            start_heading = point.get("start_heading_range", 0)
            end_heading = point.get("end_heading_range", 360)

            # Convert to float if needed
            start_heading = float(start_heading)
            end_heading = float(end_heading)

            start_rad = np.deg2rad(start_heading)
            end_rad = np.deg2rad(end_heading)

            # Draw the acceptable range in green
            if start_heading <= end_heading:
                # Simple range (e.g., 90°-180°)
                for i in range(int(start_heading/22.5), int(end_heading/22.5)+1):
                    if i < len(pf["wind_pizza"]):
                        slice = pf["wind_pizza"][i]
                        min_x = lon + 1.63*0.02*np.min([slice, 5]) * np.sin(start_rad+np.deg2rad(22.5)*i)
                        min_y = lat + 0.02*np.min([slice, 5]) * np.cos(start_rad+np.deg2rad(22.5)*i)
                        max_x = lon + 1.63*0.02*np.min([slice, 5]) * np.sin(start_rad+np.deg2rad(22.5)*(i+1))
                        max_y = lat + 0.02*np.min([slice, 5]) * np.cos(start_rad+np.deg2rad(22.5)*(i+1))

                        color = "green" if pf["wind_pizza"][i] > 0 else "red"
                        folium.Polygon(
                            locations=[[lat, lon], [min_y, min_x], [max_y, max_x]],
                            color=color,
                            weight=2,
                            fill=True,
                            fill_color=color,
                            fill_opacity=0.5,
                        ).add_to(m)
            else:
                # Range crossing 0° (e.g., 270°-90°)
                # First part (270°-360°)
                for i in range(int(start_heading/22.5), 16):
                    if i < len(pf["wind_pizza"]):
                        slice = pf["wind_pizza"][i]
                        min_x = lon + 1.63*0.02*np.min([slice, 5]) * np.sin(start_rad+np.deg2rad(22.5)*i)
                        min_y = lat + 0.02*np.min([slice, 5]) * np.cos(start_rad+np.deg2rad(22.5)*i)
                        max_x = lon + 1.63*0.02*np.min([slice, 5]) * np.sin(start_rad+np.deg2rad(22.5)*(i+1))
                        max_y = lat + 0.02*np.min([slice, 5]) * np.cos(start_rad+np.deg2rad(22.5)*(i+1))

                        color = "green" if pf["wind_pizza"][i] > 0 else "red"
                        folium.Polygon(
                            locations=[[lat, lon], [min_y, min_x], [max_y, max_x]],
                            color=color,
                            weight=2,
                            fill=True,
                            fill_color=color,
                            fill_opacity=0.5,
                        ).add_to(m)

                # Second part (0°-90°)
                for i in range(0, int(end_heading/22.5)+1):
                    if i < len(pf["wind_pizza"]):
                        slice = pf["wind_pizza"][i]
                        min_x = lon + 1.63*0.02*np.min([slice, 5]) * np.sin(np.deg2rad(22.5)*i)
                        min_y = lat + 0.02*np.min([slice, 5]) * np.cos(np.deg2rad(22.5)*i)
                        max_x = lon + 1.63*0.02*np.min([slice, 5]) * np.sin(np.deg2rad(22.5)*(i+1))
                        max_y = lat + 0.02*np.min([slice, 5]) * np.cos(np.deg2rad(22.5)*(i+1))

                        color = "green" if pf["wind_pizza"][i] > 0 else "red"
                        folium.Polygon(
                            locations=[[lat, lon], [min_y, min_x], [max_y, max_x]],
                            color=color,
                            weight=2,
                            fill=True,
                            fill_color=color,
                            fill_opacity=0.5,
                        ).add_to(m)

        # Add center marker with different colors for types
        marker_color = "blue" if point["type"] == "Thermal" else "black"
        folium.CircleMarker(
            location=[lat, lon],
            radius=5,
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            fill_opacity=1,
            popup=f"{point['name']} ({point['type']})"
        ).add_to(m)

    return m

def create_editing_map():
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

    for point in st.session_state.points:
        # Use different icons for different types
        icon_type = "fire" if point["type"] == "Thermal" else "wind"
        icon_color = "red" if not point.get("preset", False) else ("blue" if point["type"] == "Thermal" else "black")
        folium.Marker(
            location=[point['lat'], point['lon']],
            icon=folium.Icon(color=icon_color, icon=icon_type, prefix="fa"),
            popup=f"{point['name']} ({point['type']}), {point['lat']}N°, {point['lon']}E°"
        ).add_to(m)

    return m