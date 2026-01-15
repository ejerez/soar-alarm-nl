import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw, MeasureControl
import pandas as pd
import numpy as np
from math import cos, sin, radians
import json

# Set page config
st.set_page_config(
    page_title="OpenStreetMap with Heading Lines",
    page_icon="🗺️",
    layout="wide"
)

# Title
st.title("OpenStreetMap with Heading Lines")

# Initialize session state
if 'points' not in st.session_state:
    st.session_state.points = []

# Function to create heading lines
def add_heading_lines(m, lat, lon, min_heading, max_heading, line_length=0.05):
    """Add lines showing min and max headings from a point"""
    # Convert to radians
    min_rad = radians(min_heading)
    max_rad = radians(max_heading)

    # Calculate line endpoints
    min_x = lon + 1.8*line_length * cos(min_rad)
    min_y = lat + line_length * sin(min_rad)
    x_1 = lon + 1.8*line_length * cos((3*min_rad+max_rad)/4)
    y_1 = lat + line_length * sin((3*min_rad+max_rad)/4)
    x_2 = lon + 1.8*line_length * cos((min_rad+max_rad)/2)
    y_2 = lat + line_length * sin((min_rad+max_rad)/2)
    x_3 = lon + 1.8*line_length * cos((min_rad+3*max_rad)/4)
    y_3 = lat + line_length * sin((min_rad+3*max_rad)/4)
    max_x = lon + 1.8*line_length * cos(max_rad)
    max_y = lat + line_length * sin(max_rad)

    folium.Polygon(
    locations=[[lat, lon], [min_y, min_x], [y_1, x_1], [y_2, x_2], [y_3, x_3], [max_y, max_x]],
    color="green",
    weight=1,
    fill_color="green",
    fill_opacity=0.5,
    fill=True,
    popup="Tokyo, Japan",
    tooltip="Click me!",
    ).add_to(m)

    # Add center dot (black)
    folium.CircleMarker(
        location=[lat, lon],
        radius=5,
        color="black",
        fill=True,
        fill_color="black",
        fill_opacity=1,
        popup=f"Point"
    ).add_to(m)

# Create the map with OpenStreetMap
def create_osm_map():
    # Center on Netherlands
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

    # Add existing points with their heading lines
    for point in st.session_state.points:
        add_heading_lines(
            m,
            point['lat'],
            point['lon'],
            point['min_heading'],
            point['max_heading']
        )

    return m

# Create the map
m = create_osm_map()

# Display the map
output = st_folium(m, width=1000, height=600)

# Handle new points
if output.get("last_active_drawing"):
    drawn_feature = output["last_active_drawing"]
    if drawn_feature["geometry"]["type"] == "Point":
        lon, lat = drawn_feature["geometry"]["coordinates"]
        new_id = len(st.session_state.points) + 1

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

            submit_button = st.form_submit_button("Save Point")

            if submit_button:
                # Add to session state
                st.session_state.points.append({
                    "id": new_id,
                    "lat": lat,
                    "lon": lon,
                    "min_heading": min_heading,
                    "max_heading": max_heading
                })
                st.success(f"Point {new_id} saved with headings {min_heading}° to {max_heading}°!")
                st.rerun()

# Display points table with edit functionality
if st.session_state.points:
    st.subheader("Current Points")

    # Convert to DataFrame
    points_df = pd.DataFrame(st.session_state.points)

    # Show editable table
    edited_df = st.data_editor(
        points_df,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "lat": st.column_config.NumberColumn("Latitude", format="%.5f"),
            "lon": st.column_config.NumberColumn("Longitude", format="%.5f"),
            "min_heading": st.column_config.NumberColumn("Min Heading (°)", help="0° = North"),
            "max_heading": st.column_config.NumberColumn("Max Heading (°)", help="0° = North")
        },
        num_rows="dynamic"
    )

    # Update session state if table was edited
    if not edited_df.equals(points_df):
        st.session_state.points = edited_df.to_dict('records')
        st.success("Points updated!")
        st.rerun()

    # Download options
    col1, col2 = st.columns(2)
    with col1:
        csv = points_df.to_csv(index=False)
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
                    "min_heading": p['min_heading'],
                    "max_heading": p['max_heading']
                }
            } for p in st.session_state.points]
        })
        st.download_button(
            label="Download as GeoJSON",
            data=geo_json,
            file_name="heading_points.geojson",
            mime="application/json"
        )

    # Clear points button
    if st.button("Clear All Points"):
        st.session_state.points = []
        st.rerun()
else:
    st.info("Click on the map to add a new point with heading lines.")

# Sidebar with instructions
with st.sidebar:
    st.header("How to Use")
    st.markdown("""
    1. **Add Points**: Click the marker icon then click on the map
    2. **Set Headings**: Enter min/max headings in degrees
    3. **Edit Points**: Modify values in the table below
    4. **Visualization**:
       - Black dot = point location
       - Red line = minimum heading
       - Blue line = maximum heading
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
