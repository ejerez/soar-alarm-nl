import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw, MeasureControl, AntPath
import numpy as np
from datetime import datetime, timedelta
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
import plotly.graph_objects as go
import plotly.express as px

# Set page config
st.set_page_config(
    page_title="Soaralarm NL",
    page_icon="🌬️",
    layout="wide"
)

st.session_state.min_sink = 1.2
st.session_state.max_speed = 100

# Title
st.title("Soaralarm NL")

# Initialize session state
if 'points' not in st.session_state:
    # Load preset points
    st.session_state.points = [
        {
            "id": 0,
            "lat": 51.508907,
            "lon": 3.462018,
            "heading": 215,
            "steepness": 45,
            "name": "Zoutelande (Main Dune)",
            "preset": True
        },
        {
            "id": 1,
            "lat": 52.502193, 
            "lon": 4.589126,
            "name": "Wijk aan Zee (North)",
            "heading": 284,
            "steepness": 30,
            "preset": True
        },
        {
            "id": 2,
            "lat": 52.564313, 
            "lon": 4.608334 ,
            "name": "Castricum aan Zee",
            "heading": 279,
            "steepness": 30,
            "preset": True
        },
        {
            "id": 3,
            "lat": 52.302953,  
            "lon": 4.475574,
            "name": "Langevelderslag (Noordwijk)",
            "heading": 295,
            "steepness": 30,
            "preset": True
        },
        {
            "id": 4,
            "lat": 51.740870,
            "lon": 3.810101,
            "name": "Renesse (East)",
            "heading": 13,
            "steepness": 20,
            "preset": True
        },
        {
            "id": 5,
            "lat": 51.741337, 
            "lon": 3.760768,
            "name": "Renesse (West)",
            "heading": 340,
            "steepness": 20,
            "preset": True
        }
    ]
if 'selected_point' not in st.session_state:
    st.session_state.selected_point = None
if 'current_time' not in st.session_state:
    st.session_state.current_time = datetime.now()

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

def get_forecast():

    forecast = []

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": [point["lat"] for point in st.session_state.points],
        "longitude": [point["lon"] for point in st.session_state.points],
        "daily": ["sunrise", "sunset"],
        "hourly": ["temperature_2m", "precipitation", "cloud_cover", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "visibility"],
        "models": "knmi_seamless",
        "timezone": "Europe/Berlin",
        "past_days": 2,
        "forecast_days": 10,
        "temporal_resolution": "native",
        "wind_speed_unit": "ms"
    }

    responses = openmeteo.weather_api(url, params=params)

        # Process first location. Add a for-loop for multiple locations or weather models
    for id, response in enumerate(responses):
        # Process hourly data. The order of variables needs to be the same as requested.
        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_precipitation = hourly.Variables(1).ValuesAsNumpy()
        hourly_wind_speed_10m = hourly.Variables(2).ValuesAsNumpy()
        hourly_wind_direction_10m = hourly.Variables(3).ValuesAsNumpy()
        hourly_wind_gusts_10m = hourly.Variables(4).ValuesAsNumpy()
        hourly_visibility = hourly.Variables(5).ValuesAsNumpy()

        hourly_data = {"date": pd.date_range(
            start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
            end =  pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
            freq = pd.Timedelta(seconds = hourly.Interval()),
            inclusive = "left"
        )}

        hourly_data["temperature"] = hourly_temperature_2m
        hourly_data["precipitation"] = hourly_precipitation
        hourly_data["wind_speed"] = hourly_wind_speed_10m
        hourly_data["wind_direction"] = hourly_wind_direction_10m
        hourly_data["wind_gusts"] = hourly_wind_gusts_10m
        hourly_data["visibility"] = hourly_visibility


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

        daily_data["sunrise"] = pd.to_datetime(daily_sunrise, unit = "s", utc = True)
        daily_data["sunset"] = pd.to_datetime(daily_sunset, unit = "s", utc = True)

        forecast.append({"id": id, "daily_data": daily_data, "hourly_data": hourly_data})
    return forecast

def calculate_day_forecast(date):
    daily = [{  "sunrise": next(data for i, data in enumerate(point_forecast["daily_data"]["sunrise"])
                                if point_forecast["daily_data"]["date"][i].date() == date),
                "sunset": next(data for i, data in enumerate(point_forecast["daily_data"]["sunset"]) 
                               if point_forecast["daily_data"]["date"][i].date() == date)
                }
                for point_forecast in st.session_state.forecast] 
    
    forecast = [{"id": point_forecast["id"], 
                 
                "sunrise": daily[point]["sunrise"],

                "sunset": daily[point]["sunset"],

                "time": [time for time in point_forecast["hourly_data"]["date"]
                         if (time >= daily[point]["sunrise"]
                             and time <= daily[point]["sunset"])],

                "temperature": [data for i, data in enumerate(point_forecast["hourly_data"]["temperature"]) 
                             if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                                 and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],

                "precipitation": [data for i, data in enumerate(point_forecast["hourly_data"]["precipitation"]) 
                             if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                                 and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],

                "visibility": [data for i, data in enumerate(point_forecast["hourly_data"]["visibility"]) 
                             if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                                 and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],

                "wind_speed": [data for i, data in enumerate(point_forecast["hourly_data"]["wind_speed"]) 
                             if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                                 and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],

                "wind_direction": [data for i, data in enumerate(point_forecast["hourly_data"]["wind_direction"]) 
                             if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                                 and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],

                "wind_gusts": [data for i, data in enumerate(point_forecast["hourly_data"]["wind_gusts"]) 
                             if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                                 and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])]
                }
                for point, point_forecast in enumerate(st.session_state.forecast)] 
    return forecast

def calculate_display_forecast(forecast):
    disp_forecast = []

    for point_forecast in forecast:
        id = point_forecast["id"]
        point = st.session_state.points[next(i for i, p in enumerate(st.session_state.points) if p["id"] == id)]
        wind_pizza = np.zeros(int(360/22.5))

        for i, time in enumerate(point_forecast["time"]):
            if (point_forecast["precipitation"][i] < 0.1
            and point_forecast["visibility"][i] > 0.1
            and point_forecast["wind_speed"][i]*np.sin(np.deg2rad(point["steepness"])) > st.session_state.min_sink
            and point_forecast["wind_speed"][i] < st.session_state.max_speed):
                rel_head = point_forecast["wind_direction"][i] - point["heading"]
                wind_pizza[int(np.floor(rel_head/22.5))] += 1
        
        disp_forecast.append({"id":id,
                               "wind_pizza":wind_pizza})
    return disp_forecast

# Function to create heading lines with color based on wind suitability
def draw_points_pizza(m, point_forecast, line_length=0.02):
    for pf in point_forecast:
        id = pf["id"]
        point = st.session_state.points[next(i for i, p in enumerate(st.session_state.points) if p["id"] == id)]
        lat = point['lat']
        lon = point['lon']
        head = np.deg2rad(point['heading'])

        for i, slice in enumerate(pf["wind_pizza"]):
            min_x = lon + 1.63*line_length*np.min([slice, 5]) * np.sin(head+np.deg2rad(22.5)*i)
            min_y = lat + line_length*np.min([slice, 5]) * np.cos(head+np.deg2rad(22.5)*i)
            max_x = lon + 1.63*line_length*np.min([slice, 5]) * np.sin(head+np.deg2rad(22.5)*(i+1))
            max_y = lat + line_length*np.min([slice, 5]) * np.cos(head+np.deg2rad(22.5)*(i+1))

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

        name = point["name"]
        lat = point["lat"]
        lon = point["lon"]
        # Add center dot
        folium.CircleMarker(
            location=[lat, lon],
            radius=5,
            color="black",
            fill=True,
            fill_color="black",
            fill_opacity=1,
            popup=f"{name}. google.com/maps/place/{lat}°N+{lon}°E"
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
        icon_color = "red" if not point.get("preset", False) else "black"
        name = point["name"]
        lat = point["lat"]
        lon = point["lon"]
        folium.Marker(
            location=[point['lat'], point['lon']],
            icon=folium.Icon(color=icon_color, icon="wind", prefix="fa"),
            popup=f"{name}, {lat}N°, {lon}E°"
        ).add_to(m)

    return m

# Create display map (with heading polygons and wind animations)
def create_display_map(date=datetime.now()):
    netherlands_center = [52.5, 5.2913]

    m = folium.Map(
        location=netherlands_center,
        zoom_start=8,
        tiles="OpenStreetMap",
        attr="OpenStreetMap contributors"
    )

    # Add measurement control
    MeasureControl().add_to(m)

    # Get wind data for current time
    if 'forecast' not in st.session_state:
        st.session_state.forecast = get_forecast()
    
    st.session_state.day_forecast = calculate_day_forecast(date)
    display_forecast = calculate_display_forecast(st.session_state.day_forecast)

    # Add existing points with heading polygons
    draw_points_pizza(m, display_forecast)

    return m

# Create tabs
tab1, tab2, tab3 = st.tabs(["Edit Points", "Map Forecast", "Point Forecast"])

if 'forecast' not in st.session_state:
    st.session_state.forecast = get_forecast()


with tab1:
    st.header("Edit Points")
    st.markdown("Add, delete, or modify points. Preset points are shown in black.")

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

                col1, col2, col3 = st.columns(3)
                with col1:
                    name = st.text_input(
                        "Name of location"
                    )
                with col2:
                    heading = st.number_input(
                        "Best wind heading in degrees",
                        min_value=0,
                        max_value=360,
                        value=0,
                        step=1,
                        help="0 is north, 90 is east, 180 is south and 270 is west."
                    )
                with col3:
                    steepness = st.number_input(
                        "Steepness of the slope in degrees",
                        min_value=0,
                        max_value=90,
                        value=0,
                        step=1,
                        help="0 is flat, 90 is a vertical wall."
                    )

                submit_button = st.form_submit_button("Save Point")

                if submit_button:
                    # Add to session state
                    st.session_state.points.append({
                        "id": new_id,
                        "lat": lat,
                        "lon": lon,
                        "name": name,
                        "heading": heading,
                        "steepness": steepness,
                        "preset": False
                    })
                    st.success(f"{name} saved with heading {heading}° and steepness of {steepness}°!")
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
                "name": st.column_config.TextColumn("Name"),
                "lat": st.column_config.NumberColumn("Latitude", format="%.5f"),
                "lon": st.column_config.NumberColumn("Longitude", format="%.5f"),
                "heading": st.column_config.NumberColumn("Heading (°)", help="0° is North"),
                "steepness": st.column_config.NumberColumn("Steepness", help="0° is flat"),
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
        editable_columns = ['name', 'lat', 'lon', 'heading', 'steepness']
        if not edited_df[editable_columns].equals(points_df[editable_columns]):
            st.session_state.points = edited_df.drop('Delete', axis=1).to_dict('records')
            st.success("Points updated!")
            st.rerun()

with tab2:
    st.header("Visualization")
    st.markdown("View points with wind conditions. Click on points to see details in the Information tab.")

    # Time slider
    if 'dates' not in st.session_state:
        st.session_state.dates = list(set([date.date() for date in st.session_state.forecast[0]["daily_data"]["date"]]))
        st.session_state.dates.sort()
    if 'current_date' not in st.session_state:
        st.session_state.current_date = datetime.now().date()

    selected_date = st.select_slider(
        "Select Date",
        options=st.session_state.dates,
        value=st.session_state.current_date
    )

    # Update current date in session state
    if selected_date != st.session_state.current_date:
        st.session_state.current_date = selected_date
        st.rerun()


    # Create and display display map
    m_display = create_display_map(date=st.session_state.current_date)
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

with tab3:
    st.header("Point Forecast")
    st.markdown("View detailed weather forecasts for selected points.")

    # Date selection slider (same as tab 2)
    if 'dates' not in st.session_state:
        st.session_state.dates = list(set([date.date() for date in st.session_state.forecast[0]["daily_data"]["date"]]))
        st.session_state.dates.sort()
    if 'current_date' not in st.session_state:
        st.session_state.current_date = datetime.now().date()

    selected_date = st.select_slider(
        "Select Date",
        options=st.session_state.dates,
        value=st.session_state.current_date,
        key="tab3_date_slider"
    )

    if selected_date != st.session_state.current_date:
        st.session_state.current_date = selected_date
        st.rerun()

    # Point selection dropdown - ensure we always have a valid selection
    point_options = {f"{point['name']}": i for i, point in enumerate(st.session_state.points)}

    # Initialize selected_point if not set
    if 'selected_point' not in st.session_state or st.session_state.selected_point is None:
        st.session_state.selected_point = 0  # Default to first point

    selected_point_idx = st.selectbox(
        "Select Point",
        options=list(point_options.keys()),
        index=st.session_state.selected_point,
        key="point_selector"
    )

    # Update selected point in session state
    st.session_state.selected_point = point_options[selected_point_idx]

    # Get the selected point data
    selected_point = st.session_state.points[st.session_state.selected_point]
    day_forecast = calculate_day_forecast(st.session_state.current_date)[st.session_state.selected_point]

    # Create separate graphs
    if day_forecast["time"]:
        # 1. Wind Speed and Gust Speed Graph
        st.subheader("Wind Speed and Gusts")
        fig_wind = go.Figure()

        fig_wind.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["wind_speed"],
            name="Wind Speed",
            line=dict(color='blue', width=2),
            fill='tonexty'
        ))

        fig_wind.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["wind_gusts"],
            name="Gust Speed",
            line=dict(color='red', width=2, dash='dash')
        ))

        fig_wind.update_layout(
            title="Wind Speed and Gusts",
            xaxis_title="Time",
            yaxis_title="Speed (km/h)",
            hovermode="x unified",
            height=400
        )

        st.plotly_chart(fig_wind, use_container_width=True)

        # 2. Wind Direction Graph with Boundaries
        st.subheader("Wind Direction")
        fig_dir = go.Figure()

        lower_bound = selected_point["heading"] - 45
        upper_bound = selected_point["heading"] + 45

        # Add boundaries as horizontal lines
        fig_dir.add_hline(y=lower_bound, line_dash="dot", line_color="green",
                         annotation_text=f"Lower Bound ({lower_bound}°)")
        fig_dir.add_hline(y=upper_bound, line_dash="dot", line_color="green",
                         annotation_text=f"Upper Bound ({upper_bound}°)")

        # Add ideal range fill
        fig_dir.add_hrect(y0=lower_bound, y1=upper_bound,
                         fillcolor="rgba(0,255,0,0.1)", opacity=0.2,
                         line_width=0)

        # Add wind direction trace
        fig_dir.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["wind_direction"],
            name="Wind Direction",
            line=dict(color='purple', width=2)
        ))

        # Add heading line
        fig_dir.add_hline(y=selected_point["heading"], line_dash="solid", line_color="black",
                         annotation_text=f"Ideal Heading ({selected_point['heading']}°)")

        fig_dir.update_layout(
            title=f"Wind Direction (Ideal: {selected_point['heading']}° ±45°)",
            xaxis_title="Time",
            yaxis_title="Direction (°)",
            hovermode="x unified",
            height=400
        )

        st.plotly_chart(fig_dir, use_container_width=True)

        # 3. Temperature and Precipitation Graph
        st.subheader("Temperature and Precipitation")
        fig_temp_precip = go.Figure()

        # Temperature on primary y-axis
        fig_temp_precip.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["temperature"],
            name="Temperature",
            line=dict(color='orange', width=2),
            yaxis="y1"
        ))

        # Precipitation on secondary y-axis
        fig_temp_precip.add_trace(go.Bar(
            x=day_forecast["time"],
            y=day_forecast["precipitation"],
            name="Precipitation",
            marker_color='lightblue',
            yaxis="y2"
        ))

        fig_temp_precip.update_layout(
            title="Temperature and Precipitation",
            xaxis_title="Time",
            yaxis=dict(
                title="Temperature (°C)",
                side="left"
            ),
            yaxis2=dict(
                title="Precipitation (mm)",
                overlaying="y",
                side="right"
            ),
            hovermode="x unified",
            height=400
        )

        st.plotly_chart(fig_temp_precip, use_container_width=True)

        # Additional information
        st.subheader("Forecast Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Sunrise", day_forecast["sunrise"].strftime('%H:%M'))
        with col2:
            st.metric("Sunset", day_forecast["sunset"].strftime('%H:%M'))
        with col3:
            avg_wind = np.mean(day_forecast["wind_speed"])
            st.metric("Avg Wind Speed", f"{avg_wind:.1f} km/h")

        # Wind direction analysis
        st.subheader("Wind Direction Analysis")
        within_bounds = sum(1 for dir in day_forecast["wind_direction"]
                           if lower_bound <= dir <= upper_bound)
        total_hours = len(day_forecast["wind_direction"])
        percentage = (within_bounds / total_hours) * 100 if total_hours > 0 else 0

        st.write(f"**Wind within ideal range ({lower_bound}°-{upper_bound}°)**: {within_bounds}/{total_hours} hours ({percentage:.1f}%)")

        # Create a wind direction distribution chart
        fig_dir_dist = go.Figure()
        fig_dir_dist.add_trace(go.Histogram(
            x=day_forecast["wind_direction"],
            nbinsx=36,
            marker_color='lightblue',
            name='Wind Direction'
        ))

        # Add boundaries to the histogram
        fig_dir_dist.add_vline(x=lower_bound, line_dash="dash", line_color="green")
        fig_dir_dist.add_vline(x=upper_bound, line_dash="dash", line_color="green")
        fig_dir_dist.add_vline(x=selected_point["heading"], line_dash="solid", line_color="black")

        fig_dir_dist.update_layout(
            title="Wind Direction Distribution",
            xaxis_title="Direction (°)",
            yaxis_title="Frequency",
            bargap=0.1,
            height=400
        )

        st.plotly_chart(fig_dir_dist, use_container_width=True)

    else:
        st.warning("No forecast data available for the selected date.")

# Sidebar with instructions
with st.sidebar:
    st.header("How to Use")
    st.markdown("""
    **Editing Tab**:
    - Add points by clicking the marker icon then the map
    - Set heading ranges for each point
    - Edit point parameters in the table below
    - Check boxes to delete custom points (preset points cannot be deleted)

    **Map Forecast Tab**:
    - View points with wind conditions
    - Use the date slider to see wind forecasts for different days
    - Green sectors = suitable wind, Orange = marginal, Red = unsuitable

    **Point Forecast Tab**:
    - Select a date using the slider
    - Choose a point from the dropdown
    - View detailed weather forecasts including:
      - Wind speed and gusts
      - Temperature
      - Precipitation
      - Wind direction with ideal range boundaries
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
    - **Zoutelande**: Southwest coast (215°)
    - **Wijk aan Zee**: Northwest coast (284°)
    - **Castricum aan Zee**: Northwest coast (279°)
    - **Langevelderslag**: Northwest coast (295°)
    - **Renesse (East)**: Southwest coast (13°)
    - **Renesse (West)**: Southwest coast (340°)
    """)