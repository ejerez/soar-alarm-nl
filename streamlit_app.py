import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw, MeasureControl
import numpy as np
from math import cos, sin, radians
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go
import random
import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry

# Set page config
st.set_page_config(
    page_title="Wind Forecast Visualization",
    page_icon="🌬️",
    layout="wide"
)

# Title
st.title("Wind Forecast Visualization Tool")

# Initialize session state
if 'points' not in st.session_state:
    # Load preset points
    st.session_state.points = [
        {
            "id": 1,
            "lat": 51.4833,
            "lon": 3.6167,
            "min_heading": 180,
            "max_heading": 270,
            "name": "Zoutelande",
            "preset": True
        },
        {
            "id": 2,
            "lat": 52.4833,
            "lon": 4.6167,
            "name": "Wijk aan Zee",
            "min_heading": 0,
            "max_heading": 90,
            "preset": True
        }
    ]
if 'selected_point' not in st.session_state:
    st.session_state.selected_point = None
if 'current_time_idx' not in st.session_state:
    st.session_state.current_time_idx = 0

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
url = "https://api.open-meteo.com/v1/forecast"
params = {
	"latitude": 52.52,
	"longitude": 13.41,
	"daily": ["sunrise", "sunset"],
	"hourly": ["temperature_2m", "relative_humidity_2m", "precipitation", "cloud_cover", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "visibility"],
	"models": "knmi_seamless",
	"timezone": "Europe/Berlin",
	"past_days": 2,
	"forecast_days": 10,
}
responses = openmeteo.weather_api(url, params=params)

# Process first location. Add a for-loop for multiple locations or weather models
response = responses[0]
print(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
print(f"Elevation: {response.Elevation()} m asl")
print(f"Timezone: {response.Timezone()}{response.TimezoneAbbreviation()}")
print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")

# Process hourly data. The order of variables needs to be the same as requested.
hourly = response.Hourly()
hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
hourly_precipitation = hourly.Variables(2).ValuesAsNumpy()
hourly_cloud_cover = hourly.Variables(3).ValuesAsNumpy()
hourly_wind_speed_10m = hourly.Variables(4).ValuesAsNumpy()
hourly_wind_direction_10m = hourly.Variables(5).ValuesAsNumpy()
hourly_wind_gusts_10m = hourly.Variables(6).ValuesAsNumpy()
hourly_visibility = hourly.Variables(7).ValuesAsNumpy()

hourly_data = {"date": pd.date_range(
	start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
	end =  pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
	freq = pd.Timedelta(seconds = hourly.Interval()),
	inclusive = "left"
)}

hourly_data["temperature_2m"] = hourly_temperature_2m
hourly_data["relative_humidity_2m"] = hourly_relative_humidity_2m
hourly_data["precipitation"] = hourly_precipitation
hourly_data["cloud_cover"] = hourly_cloud_cover
hourly_data["wind_speed_10m"] = hourly_wind_speed_10m
hourly_data["wind_direction_10m"] = hourly_wind_direction_10m
hourly_data["wind_gusts_10m"] = hourly_wind_gusts_10m
hourly_data["visibility"] = hourly_visibility

hourly_dataframe = pd.DataFrame(data = hourly_data)
print("\nHourly data\n", hourly_dataframe)

# Process daily data. The order of variables needs to be the same as requested.
daily = response.Daily()
daily_sunrise = daily.Variables(0).ValuesInt64AsNumpy()
daily_sunset = daily.Variables(1).ValuesInt64AsNumpy()

daily_data = {"date": pd.date_range(
	start = pd.to_datetime(daily.Time(), unit = "s", utc = True),
	end =  pd.to_datetime(daily.TimeEnd(), unit = "s", utc = True),
	freq = pd.Timedelta(seconds = daily.Interval()),
	inclusive = "left"
)}

daily_data["sunrise"] = daily_sunrise
daily_data["sunset"] = daily_sunset

daily_dataframe = pd.DataFrame(data = daily_data)
print("\nDaily data\n", daily_dataframe)

# Function to generate mock wind forecast data
def generate_wind_forecast():
    """Generate mock wind forecast data for the next 24 hours"""
    timestamps = [datetime.now() + timedelta(hours=i) for i in range(25)]
    wind_data = []

    for i, ts in enumerate(timestamps):
        # Generate wind data for each point
        point_winds = []
        for point in st.session_state.points:
            # Base wind with some variation
            base_speed = 5 + 3 * np.sin(i * np.pi / 12)  # Varies throughout the day
            base_dir = 180 + 90 * np.sin(i * np.pi / 12)

            # Add some randomness
            speed = max(0, base_speed + np.random.normal(0, 0.5))
            direction = (base_dir + np.random.normal(0, 15)) % 360

            point_winds.append({
                "point_id": point["id"],
                "speed": speed,
                "direction": direction
            })

        wind_data.append({
            "time": ts,
            "winds": point_winds
        })

    return wind_data

# Generate wind forecast data
if 'wind_forecast' not in st.session_state:
    st.session_state.wind_forecast = generate_wind_forecast()

# Function to create heading lines with color based on wind suitability
def add_heading_lines(m, point, wind_dir=None, line_length=0.05):
    """Add lines showing min and max headings from a point with color coding"""
    lat = point['lat']
    lon = point['lon']
    min_heading = point['min_heading']
    max_heading = point['max_heading']

    # Convert to radians
    min_rad = radians(min_heading)
    max_rad = radians(max_heading)

    # Calculate line endpoints
    min_x = lon + 1.63*line_length * cos(min_rad)
    min_y = lat + line_length * sin(min_rad)
    x_1 = lon + 1.63*line_length * cos((3*min_rad+max_rad)/4)
    y_1 = lat + line_length * sin((3*min_rad+max_rad)/4)
    x_2 = lon + 1.63*line_length * cos((min_rad+max_rad)/2)
    y_2 = lat + line_length * sin((min_rad+max_rad)/2)
    x_3 = lon + 1.63*line_length * cos((min_rad+3*max_rad)/4)
    y_3 = lat + line_length * sin((min_rad+3*max_rad)/4)
    max_x = lon + 1.63*line_length * cos(max_rad)
    max_y = lat + line_length * sin(max_rad)

    # Determine color based on wind direction
    if wind_dir is not None:
        # Check if wind is within acceptable range
        if (min_heading <= wind_dir <= max_heading) or (max_heading <= wind_dir <= min_heading):
            color = "green"
            popup_text = f"Point {point['id']}: {point.get('name', 'Custom Point')}\nHeadings: {min_heading}° to {max_heading}°\nWind: {wind_dir:.0f}° (Suitable)"
        else:
            color = "red"
            popup_text = f"Point {point['id']}: {point.get('name', 'Custom Point')}\nHeadings: {min_heading}° to {max_heading}°\nWind: {wind_dir:.0f}° (Unsuitable)"
    else:
        color = "gray"
        popup_text = f"Point {point['id']}: {point.get('name', 'Custom Point')}\nHeadings: {min_heading}° to {max_heading}°"

    folium.Polygon(
        locations=[[lat, lon], [min_y, min_x], [y_1, x_1], [y_2, x_2], [y_3, x_3], [max_y, max_x]],
        color=color,
        weight=2,
        fill=True,
        fill_color=color,
        fill_opacity=0.5,
        popup=popup_text
    ).add_to(m)

    # Add center dot
    folium.CircleMarker(
        location=[lat, lon],
        radius=5,
        color="black",
        fill=True,
        fill_color="black",
        fill_opacity=1,
        popup=f"Point {point['id']}: {point.get('name', 'Custom Point')}"
    ).add_to(m)

# Function to create wind arrows
def add_wind_arrows(m, lat, lon, speed, direction, time_idx):
    """Add animated wind arrows to the map"""
    # Calculate arrow endpoint
    angle_rad = radians(direction)
    arrow_length = 0.01 * speed  # Scale with wind speed
    end_lat = lat + arrow_length * sin(angle_rad)
    end_lon = lon + arrow_length * cos(angle_rad)

    # Create arrow
    folium.PolyLine(
        locations=[[lat, lon], [end_lat, end_lon]],
        color="blue",
        weight=3,
        arrowheads={
            'size': '15%',
            'frequency': 'end'
        },
        popup=f"Wind: {speed:.1f} m/s, {direction:.0f}°"
    ).add_to(m)

# Create editing map (simple markers only)
def create_editing_map():
    netherlands_center = [52.1326, 5.2913]

    m = folium.Map(
        location=netherlands_center,
        zoom_start=7,
        tiles="OpenStreetMap",
        attr="OpenStreetMap contributors"
    )

    # Add measurement control
    MeasureControl().add_to(m)

    # Add draw control for creating points
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

    # Add existing points as simple markers
    for point in st.session_state.points:
        icon_color = "blue" if not point.get("preset", False) else "green"
        folium.Marker(
            location=[point['lat'], point['lon']],
            icon=folium.Icon(color=icon_color, icon="map-marker", prefix="fa"),
            popup=f"Point {point['id']}: {point.get('name', 'Custom Point')}"
        ).add_to(m)

    return m

# Create display map (with heading polygons and wind animations)
def create_display_map(time_idx=None):
    netherlands_center = [52.1326, 5.2913]

    m = folium.Map(
        location=netherlands_center,
        zoom_start=7,
        tiles="OpenStreetMap",
        attr="OpenStreetMap contributors"
    )

    # Add measurement control
    MeasureControl().add_to(m)

    # Get wind data for current time
    if time_idx is not None and time_idx < len(st.session_state.wind_forecast):
        current_wind_data = st.session_state.wind_forecast[time_idx]['winds']
        wind_dict = {wind['point_id']: wind for wind in current_wind_data}
    else:
        wind_dict = {}

    # Add existing points with heading polygons
    for point in st.session_state.points:
        wind_data = wind_dict.get(point['id'])
        wind_dir = wind_data['direction'] if wind_data else None
        add_heading_lines(
            m,
            point,
            wind_dir=wind_dir
        )

        # Add wind arrows if we have wind data
        if wind_data:
            add_wind_arrows(
                m,
                point['lat'],
                point['lon'],
                wind_data['speed'],
                wind_data['direction'],
                time_idx
            )

    return m

# Create tabs
tab1, tab2, tab3 = st.tabs(["Editing", "Visualization", "Information"])

with tab1:
    st.header("Edit Points")
    st.markdown("Add, delete, or modify points. Preset points are shown in green.")

    # Create and display editing map
    m_edit = create_editing_map()
    output = st_folium(m_edit, width=1000, height=600)

    # Handle new points
    if output.get("last_active_drawing"):
        drawn_feature = output["last_active_drawing"]
        if drawn_feature["geometry"]["type"] == "Point":
            lon, lat = drawn_feature["geometry"]["coordinates"]
            new_id = max([p['id'] for p in st.session_state.points]) + 1 if st.session_state.points else 1

            # Create form for point parameters
            with st.form(key=f"point_{new_id}_form"):
                st.subheader(f"Configure Point {new_id}")

                col1, col2 = st.columns(2)
                with col1:
                    min_heading = st.number_input(
                        "Minimum Heading (degrees)",
                        min_value=0,
                        max_value=360,
                        value=0,
                        step=1,
                        help="0° = North, 90° = East"
                    )
                with col2:
                    max_heading = st.number_input(
                        "Maximum Heading (degrees)",
                        min_value=0,
                        max_value=360,
                        value=90,
                        step=1,
                        help="0° = North, 90° = East"
                    )

                point_name = st.text_input("Point Name (optional)", "")

                submit_button = st.form_submit_button("Save Point")

                if submit_button:
                    # Add to session state
                    st.session_state.points.append({
                        "id": new_id,
                        "lat": lat,
                        "lon": lon,
                        "min_heading": min_heading,
                        "max_heading": max_heading,
                        "name": point_name if point_name else None,
                        "preset": False
                    })
                    st.success(f"Point {new_id} saved with headings {min_heading}° to {max_heading}°!")
                    st.rerun()

    # Add points management table
    st.subheader("Manage Points")
    if st.session_state.points:
        # Convert to DataFrame
        points_df = pd.DataFrame(st.session_state.points)

        # Add delete column (only for non-preset points)
        points_df['Delete'] = False
        points_df.loc[points_df['preset'] == True, 'Delete'] = None

        # Show editable table with delete option
        edited_df = st.data_editor(
            points_df,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "name": st.column_config.TextColumn("Name"),
                "lat": st.column_config.NumberColumn("Latitude", format="%.5f"),
                "lon": st.column_config.NumberColumn("Longitude", format="%.5f"),
                "min_heading": st.column_config.NumberColumn("Min Heading (°)", help="0° = North"),
                "max_heading": st.column_config.NumberColumn("Max Heading (°)", help="0° = North"),
                "preset": st.column_config.CheckboxColumn("Preset", disabled=True),
                "Delete": st.column_config.CheckboxColumn("Delete?")
            },
            num_rows="dynamic",
            hide_index=True,
            disabled=["preset"]
        )

        # Handle deletions (only for non-preset points)
        if edited_df['Delete'].any():
            # Get indices of points to delete (only non-preset)
            to_delete = edited_df[(edited_df['Delete'] == True) & (edited_df['preset'] == False)]['id'].tolist()

            if to_delete:
                # Filter out deleted points
                st.session_state.points = [
                    p for p in st.session_state.points if p['id'] not in to_delete
                ]
                st.success(f"Deleted {len(to_delete)} point(s)")
                st.rerun()

        # Handle edits (excluding the Delete column)
        editable_columns = ['name', 'lat', 'lon', 'min_heading', 'max_heading']
        if not edited_df[editable_columns].equals(points_df[editable_columns]):
            st.session_state.points = edited_df.drop('Delete', axis=1).to_dict('records')
            st.success("Points updated!")
            st.rerun()

        # Download options
        col1, col2 = st.columns(2)
        with col1:
            csv = points_df.drop('Delete', axis=1).to_csv(index=False)
            st.download_button(
                label="Download Points as CSV",
                data=csv,
                file_name="heading_points.csv",
                mime="text/csv"
            )
        with col2:
            geo_json = json.dumps({
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [p['lon'], p['lat']]
                    },
                    "properties": {
                        "id": p['id'],
                        "name": p.get('name'),
                        "min_heading": p['min_heading'],
                        "max_heading": p['max_heading'],
                        "preset": p.get('preset', False)
                    }
                } for p in st.session_state.points]
            })
            st.download_button(
                label="Download as GeoJSON",
                data=geo_json,
                file_name="heading_points.geojson",
                mime="application/json"
            )
    else:
        st.info("No points have been added yet. Click on the map to add a new point.")

with tab2:
    st.header("Visualization")
    st.markdown("View points with wind conditions. Click on points to see details in the Information tab.")

    # Time slider
    time_options = [f"{i}:00" for i in range(25)]
    selected_time = st.slider(
        "Select Time",
        min_value=0,
        max_value=23,
        value=st.session_state.current_time_idx,
        format="%d:00",
        help="Select the forecast time to visualize"
    )

    # Update current time in session state
    if selected_time != st.session_state.current_time_idx:
        st.session_state.current_time_idx = selected_time
        st.rerun()

    # Create and display display map
    m_display = create_display_map(time_idx=st.session_state.current_time_idx)
    output = st_folium(m_display, width=1000, height=600, returned_objects=["last_object_clicked"])

    # Handle point selection from map click
    if output.get("last_object_clicked"):
        # Try to extract point ID from popup
        popup = output["last_object_clicked"].get("popup")
        if popup:
            # Extract point ID from popup text
            popup_text = popup.get("content", "")
            if "Point " in popup_text:
                try:
                    point_id = int(popup_text.split("Point ")[1].split(":")[0].strip())
                    # Find the point in our list
                    for i, p in enumerate(st.session_state.points):
                        if p['id'] == point_id:
                            st.session_state.selected_point = i
                            st.switch_page("Information")
                            break
                except:
                    pass

    # Show current wind information
    if st.session_state.current_time_idx < len(st.session_state.wind_forecast):
        current_time = st.session_state.wind_forecast[st.session_state.current_time_idx]['time']
        st.write(f"**Current Time**: {current_time.strftime('%Y-%m-%d %H:%M')}")

        # Show wind summary
        wind_data = st.session_state.wind_forecast[st.session_state.current_time_idx]['winds']
        if wind_data:
            avg_speed = np.mean([w['speed'] for w in wind_data])
            st.write(f"**Average Wind Speed**: {avg_speed:.1f} m/s")

            # Count suitable winds
            suitable_count = 0
            for point in st.session_state.points:
                wind = next((w for w in wind_data if w['point_id'] == point['id']), None)
                if wind:
                    if (point['min_heading'] <= wind['direction'] <= point['max_heading']) or \
                       (point['max_heading'] <= wind['direction'] <= point['min_heading']):
                        suitable_count += 1

            st.write(f"**Suitable Wind Conditions**: {suitable_count}/{len(st.session_state.points)} points")

with tab3:
    st.header("Wind Information")
    st.markdown("View detailed wind information for selected points.")

    if st.session_state.points:
        # Create dropdown to select point
        point_options = {
            f"Point {p['id']} - {p.get('name', 'Custom Point')} ({p['lat']:.4f}, {p['lon']:.4f})": i
            for i, p in enumerate(st.session_state.points)
        }

        # Use selected point from session state or default to first
        default_idx = st.session_state.selected_point if st.session_state.selected_point is not None else 0
        selected_idx = st.selectbox(
            "Select a point:",
            options=list(point_options.keys()),
            index=default_idx
        )

        # Update selected point in session state
        st.session_state.selected_point = point_options[selected_idx]
        selected_point = st.session_state.points[st.session_state.selected_point]

        # Show point details
        st.subheader(f"Point {selected_point['id']} Details")
        st.write(f"**Name**: {selected_point.get('name', 'Custom Point')}")
        st.write(f"**Location**: {selected_point['lat']:.5f}, {selected_point['lon']:.5f}")
        st.write(f"**Heading Range**: {selected_point['min_heading']}° to {selected_point['max_heading']}°")

        # Show wind forecast charts
        st.subheader("Wind Forecast (Next 24 Hours)")

        # Prepare data for charts
        timestamps = [data['time'] for data in st.session_state.wind_forecast]
        speeds = []
        directions = []
        suitable = []

        for data in st.session_state.wind_forecast:
            wind = next((w for w in data['winds'] if w['point_id'] == selected_point['id']), None)
            if wind:
                speeds.append(wind['speed'])
                directions.append(wind['direction'])
                # Check if wind is suitable
                if (selected_point['min_heading'] <= wind['direction'] <= selected_point['max_heading']) or \
                   (selected_point['max_heading'] <= wind['direction'] <= selected_point['min_heading']):
                    suitable.append(True)
                else:
                    suitable.append(False)
            else:
                speeds.append(None)
                directions.append(None)
                suitable.append(None)

        # Create wind speed chart
        fig_speed = go.Figure()
        fig_speed.add_trace(go.Scatter(
            x=timestamps,
            y=speeds,
            mode='lines+markers',
            name='Wind Speed',
            line=dict(color='royalblue', width=2),
            marker=dict(size=6)
        ))
        fig_speed.update_layout(
            title='Wind Speed Forecast (m/s)',
            xaxis_title='Time',
            yaxis_title='Wind Speed (m/s)',
            hovermode='x unified'
        )
        st.plotly_chart(fig_speed, use_container_width=True)

        # Create wind direction chart
        fig_dir = go.Figure()
        fig_dir.add_trace(go.Scatterpolar(
            r=speeds,
            theta=directions,
            mode='markers',
            name='Wind Direction',
            marker=dict(
                color=speeds,
                colorscale='Viridis',
                size=10,
                colorbar=dict(title='Speed (m/s)')
            )
        ))
        fig_dir.update_layout(
            title='Wind Direction and Speed',
            polar=dict(
                radialaxis=dict(visible=True, range=[0, max(speeds)*1.2]),
                angularaxis=dict(direction='clockwise', rotation=90)
            )
        )
        st.plotly_chart(fig_dir, use_container_width=True)

        # Show wind suitability over time
        st.subheader("Wind Suitability Over Time")
        fig_suitable = go.Figure()
        fig_suitable.add_trace(go.Scatter(
            x=timestamps,
            y=[1 if s else 0 for s in suitable],
            mode='lines+markers',
            name='Suitable',
            line=dict(color='green', width=2),
            marker=dict(size=8)
        ))
        fig_suitable.update_layout(
            title='Wind Suitability (1 = Suitable, 0 = Unsuitable)',
            xaxis_title='Time',
            yaxis_title='Suitability',
            yaxis=dict(tickvals=[0, 1], ticktext=['Unsuitable', 'Suitable']),
            hovermode='x unified'
        )
        st.plotly_chart(fig_suitable, use_container_width=True)

        # Show detailed forecast table
        st.subheader("Detailed Forecast Data")
        forecast_df = pd.DataFrame({
            'Time': timestamps,
            'Wind Speed (m/s)': [f"{s:.1f}" if s is not None else "N/A" for s in speeds],
            'Wind Direction (°)': [f"{d:.0f}" if d is not None else "N/A" for d in directions],
            'Suitable': ['✅' if s else '❌' for s in suitable]
        })
        st.dataframe(forecast_df, use_container_width=True)

        # Show summary statistics
        st.subheader("Summary Statistics")
        valid_speeds = [s for s in speeds if s is not None]
        valid_directions = [d for d in directions if d is not None]
        suitable_winds = [s for s, suit in zip(valid_speeds, suitable) if suit and s is not None]

        if valid_speeds:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Avg Wind Speed", f"{np.mean(valid_speeds):.1f} m/s")
            with col2:
                st.metric("Max Wind Speed", f"{np.max(valid_speeds):.1f} m/s")
            with col3:
                st.metric("Min Wind Speed", f"{np.min(valid_speeds):.1f} m/s")

            if suitable_winds:
                st.success(f"✅ Suitable wind conditions found! Average speed: {np.mean(suitable_winds):.1f} m/s")
                st.write(f"Suitable periods: {sum(suitable)}/{len(suitable)} hours")
            else:
                st.warning("⚠️ No suitable wind conditions within the specified heading range.")
    else:
        st.info("No points available. Please add points in the Editing tab first.")

# Sidebar with instructions
with st.sidebar:
    st.header("How to Use")
    st.markdown("""
    **Editing Tab**:
    - Add points by clicking the marker icon then the map
    - Set heading ranges for each point
    - Edit point parameters in the table below
    - Check boxes to delete custom points (preset points cannot be deleted)
    - Download data as CSV or GeoJSON

    **Visualization Tab**:
    - View points with wind conditions
    - Use the time slider to see wind forecasts at different times
    - Green sectors = suitable wind, Red sectors = unsuitable wind
    - Click on points to view details in the Information tab

    **Information Tab**:
    - Select a point from the dropdown
    - View detailed wind forecast charts and data
    - Analyze wind suitability for your headings
    """)

    st.header("Heading Reference")
    st.markdown("""
    - **0°**: North (up)
    - **90°**: East (right)
    - **180°**: South (down)
    - **270°**: West (left)
    """)

    st.header("Map Controls")
    st.markdown("""
    - **Zoom**: Mouse wheel or +/- buttons
    - **Pan**: Click and drag
    - **Measure**: Ruler icon for distances
    """)

    st.header("Preset Points")
    st.markdown("""
    - **Zoutelande**: Southwest coast (180°-270°)
    - **Wijk aan Zee**: Northwest coast (0°-90°)
    """)