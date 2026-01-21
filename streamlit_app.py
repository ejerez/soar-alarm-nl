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

# Set page config
st.set_page_config(
    page_title="Soaralarm NL",
    page_icon="🌬️",
    layout="wide"
)

# Initialize session state
if 'min_speed' not in st.session_state:
    st.session_state.min_speed = 20
if 'max_speed' not in st.session_state:
    st.session_state.max_speed = 60
if 'points' not in st.session_state:
    st.session_state.points = [
        {"id": 0, "lat": 51.508907, "lon": 3.462018, "heading": 215, "steepness": 45, "name": "Zoutelande (Main Dune)", "preset": True},
        {"id": 1, "lat": 52.502193, "lon": 4.589126, "name": "Wijk aan Zee (North)", "heading": 284, "steepness": 30, "preset": True},
        {"id": 2, "lat": 52.564313, "lon": 4.608334, "name": "Castricum aan Zee", "heading": 279, "steepness": 30, "preset": True},
        {"id": 3, "lat": 52.302953, "lon": 4.475574, "name": "Langevelderslag (Noordwijk)", "heading": 295, "steepness": 30, "preset": True},
        {"id": 4, "lat": 51.740870, "lon": 3.810101, "name": "Renesse (East)", "heading": 13, "steepness": 20, "preset": True},
        {"id": 5, "lat": 51.741337, "lon": 3.760768, "name": "Renesse (West)", "heading": 340, "steepness": 20, "preset": True}
    ]
if 'selected_point' not in st.session_state:
    st.session_state.selected_point = 0
if 'current_date' not in st.session_state:
    st.session_state.current_date = datetime.now().date()
if 'forecast' not in st.session_state:
    st.session_state.forecast = None
if 'all_day_forecasts' not in st.session_state:
    st.session_state.all_day_forecasts = {}
if 'all_display_forecasts' not in st.session_state:
    st.session_state.all_display_forecasts = {}
if 'map_key' not in st.session_state:
    st.session_state.map_key = 0

# Setup the Open-Meteo API client with cache
@st.cache_data(ttl=3600, show_spinner=False)
def get_forecast():
    forecast = []
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": [point["lat"] for point in st.session_state.points],
        "longitude": [point["lon"] for point in st.session_state.points],
        "daily": ["sunrise", "sunset"],
        "hourly": ["temperature_2m", "visibility", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "precipitation"],
        "models": "knmi_seamless",
        "timezone": "Europe/Berlin",
        "past_days": 2,
        "forecast_days": 10,
    }

    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    responses = openmeteo.weather_api(url, params=params)

    for id, response in enumerate(responses):
        hourly = response.Hourly()
        hourly_data = {
            "date": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            ),
            "temperature": hourly.Variables(0).ValuesAsNumpy(),
            "visibility": hourly.Variables(1).ValuesAsNumpy(),
            "wind_speed": hourly.Variables(2).ValuesAsNumpy(),
            "wind_direction": hourly.Variables(3).ValuesAsNumpy(),
            "wind_gusts": hourly.Variables(4).ValuesAsNumpy(),
            "precipitation": hourly.Variables(5).ValuesAsNumpy()
        }

        daily = response.Daily()
        daily_data = {
            "date": pd.date_range(
                start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=daily.Interval()),
                inclusive="left"
            ),
            "sunrise": pd.to_datetime(daily.Variables(0).ValuesInt64AsNumpy(), unit="s", utc=True),
            "sunset": pd.to_datetime(daily.Variables(1).ValuesInt64AsNumpy(), unit="s", utc=True)
        }

        forecast.append({"id": id, "daily_data": daily_data, "hourly_data": hourly_data})
    return forecast

@st.cache_data(show_spinner=False)
def calculate_day_forecast(date):
    daily = [{
        "sunrise": next(data for i, data in enumerate(point_forecast["daily_data"]["sunrise"])
                       if point_forecast["daily_data"]["date"][i].date() == date),
        "sunset": next(data for i, data in enumerate(point_forecast["daily_data"]["sunset"])
                      if point_forecast["daily_data"]["date"][i].date() == date)
    } for point_forecast in st.session_state.forecast]

    forecast = [{
        "id": point_forecast["id"],
        "sunrise": daily[point]["sunrise"],
        "sunset": daily[point]["sunset"],
        "time": [time for time in point_forecast["hourly_data"]["date"]
                if (time >= daily[point]["sunrise"] and time <= daily[point]["sunset"])],
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
    } for point, point_forecast in enumerate(st.session_state.forecast)]
    return forecast

@st.cache_data(show_spinner=False)
def calculate_display_forecast(forecast):
    disp_forecast = []
    for point_forecast in forecast:
        point = st.session_state.points[next(i for i, p in enumerate(st.session_state.points) if p["id"] == point_forecast["id"])]
        wind_pizza = np.zeros(int(360/22.5))

        for i, time in enumerate(point_forecast["time"]):
            if (point_forecast["precipitation"][i] < 0.1
            and point_forecast["visibility"][i] > 0.1
            and point_forecast["wind_speed"][i] > st.session_state.min_speed):
                rel_head = point_forecast["wind_direction"][i] - point["heading"]
                wind_pizza[int(np.floor(rel_head/22.5))] += 1

        disp_forecast.append({"id": point_forecast["id"], "wind_pizza": wind_pizza})
    return disp_forecast

def create_map_with_forecast(date):
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
        lat, lon, head = point['lat'], point['lon'], np.deg2rad(point['heading'])

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

        folium.CircleMarker(
            location=[lat, lon],
            radius=5,
            color="black",
            fill=True,
            fill_color="black",
            fill_opacity=1,
            popup=f"{point['name']}. google.com/maps/place/{lat}°N+{lon}°E"
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
        folium.Marker(
            location=[point['lat'], point['lon']],
            icon=folium.Icon(color="red" if not point.get("preset", False) else "black", icon="wind", prefix="fa"),
            popup=f"{point['name']}, {point['lat']}N°, {point['lon']}E°"
        ).add_to(m)

    return m

# Main app
st.title("Soaralarm NL")

# Initialize forecast data if not already loaded
if st.session_state.forecast is None:
    with st.spinner("Loading weather data..."):
        st.session_state.forecast = get_forecast()
        # Pre-compute forecasts for all dates
        st.session_state.dates = list(set([date.date() for date in st.session_state.forecast[0]["daily_data"]["date"]]))
        st.session_state.dates.sort()
        for date in st.session_state.dates:
            st.session_state.all_day_forecasts[date] = calculate_day_forecast(date)
            st.session_state.all_display_forecasts[date] = calculate_display_forecast(st.session_state.all_day_forecasts[date])

# Date selector at the top
st.header("Date Selection")
selected_date = st.select_slider(
    "Select Date",
    options=st.session_state.dates,
    value=st.session_state.current_date,
    key="shared_date_slider"
)

if selected_date != st.session_state.current_date:
    st.session_state.current_date = selected_date

# Create tabs
tab1, tab2, tab3 = st.tabs(["Map Forecast", "Point Forecast", "Edit Points"])

with tab1:
    # Create and display map with current date's forecast
    current_map = create_map_with_forecast(st.session_state.current_date)
    st_folium(current_map, width=1000, height=600, key=f"map_{st.session_state.current_date}")

with tab2:
    # Point selection
    point_options = {f"{point['name']}": i for i, point in enumerate(st.session_state.points)}
    selected_point_idx = st.selectbox(
        "Select Point",
        options=list(point_options.keys()),
        index=st.session_state.selected_point,
        key="point_selector"
    )
    st.session_state.selected_point = point_options[selected_point_idx]

    # Get forecast data
    selected_point = st.session_state.points[st.session_state.selected_point]
    day_forecast = st.session_state.all_day_forecasts[st.session_state.current_date][st.session_state.selected_point]

    if day_forecast["time"]:
        # Wind Speed and Gust Speed Graph
        st.subheader("Wind Speed and Gusts")
        fig_wind = go.Figure()

        fig_wind.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["wind_speed"],
            name="Wind Speed",
            line=dict(color='blue', width=4),
            #fill='tonexty',
            line_shape='spline'
        ))

        fig_wind.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["wind_gusts"],
            name="Gust Speed",
            line=dict(color='orange', width=4),
            #fill='tonexty',
            line_shape='spline'
        ))

        fig_wind.add_hrect(y0=st.session_state.min_speed, y1=st.session_state.max_speed, fillcolor="rgba(153,255,51,0.7)", opacity=0.5, line_width=0)

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

        lower_bound = selected_point["heading"] - 45
        lower_ideal = selected_point["heading"] - 22.5
        upper_ideal = selected_point["heading"] + 22.5
        upper_bound = selected_point["heading"] + 45

        fig_dir.add_hrect(y0=lower_ideal, y1=upper_ideal, fillcolor="rgba(153,255,51,0.7)", opacity=0.5, line_width=0)
        fig_dir.add_hrect(y0=lower_bound, y1=lower_ideal, fillcolor="rgba(255,153,51,0.7)", opacity=0.5, line_width=0)
        fig_dir.add_hrect(y0=upper_ideal, y1=upper_bound, fillcolor="rgba(255,153,51,0.7)", opacity=0.5, line_width=0)

        fig_dir.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["wind_direction"],
            name="Wind Direction",
            line=dict(color='black', width=2),
            line_shape='spline'
        ))

        fig_dir.add_hline(y=selected_point["heading"], line_dash="dot", line_color="grey",
                        annotation_text=f"Ideal ({selected_point['heading']}°)")

        fig_dir.update_layout(
            title=f"Wind Direction (Ideal: {selected_point['heading']}° ±45°)",
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

        fig_temp_precip.update_layout(
            title="Temperature and Precipitation",
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

                col1, col2, col3 = st.columns(3)
                with col1:
                    name = st.text_input("Name of location")
                with col2:
                    heading = st.number_input("Best wind heading in degrees", min_value=0, max_value=360, value=0, step=1)
                with col3:
                    steepness = st.number_input("Steepness of the slope in degrees", min_value=0, max_value=90, value=0, step=1)

                if st.form_submit_button("Save Point"):
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

        edited_df = st.data_editor(
            points_df,
            column_config={
                "name": st.column_config.TextColumn("Name"),
                "lat": st.column_config.NumberColumn("Latitude", format="%.5f"),
                "lon": st.column_config.NumberColumn("Longitude", format="%.5f"),
                "heading": st.column_config.NumberColumn("Heading (°)"),
                "steepness": st.column_config.NumberColumn("Steepness"),
                "preset": st.column_config.CheckboxColumn("Preset", disabled=True),
                "Delete": st.column_config.CheckboxColumn("Delete?")
            },
            num_rows="dynamic",
            hide_index=True,
            disabled=["preset"]
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

        editable_columns = ['name', 'lat', 'lon', 'heading', 'steepness']
        if not edited_df[editable_columns].equals(points_df[editable_columns]):
            st.session_state.points = edited_df.drop('Delete', axis=1).to_dict('records')
            st.success("Points updated!")
            # Clear cached forecasts since points changed
            st.session_state.forecast = None
            st.session_state.all_day_forecasts = {}
            st.session_state.all_display_forecasts = {}
            st.rerun()

# Sidebar
with st.sidebar:
    st.header("How to Use")
    st.markdown("""
    **Map Forecast Tab**: View points with wind conditions using the date slider.

    **Point Forecast Tab**: Select a date and point to view detailed weather forecasts.

    **Edit Points Tab**: Add, modify, or delete points.
    """)

    st.header("Preset Points")
    st.markdown("""
    - Zoutelande (215°)
    - Wijk aan Zee (284°)
    - Castricum aan Zee (279°)
    - Langevelderslag (295°)
    - Renesse (East) (13°)
    - Renesse (West) (340°)
    """)