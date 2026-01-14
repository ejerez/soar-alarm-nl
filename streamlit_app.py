import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
import geopandas as gpd
import json
import pandas as pd

# Set page config
st.set_page_config(
    page_title="Netherlands GIS Map",
    page_icon="🗺️",
    layout="wide"
)

# Title
st.title("Netherlands GIS Map with Point Selection")

# Initialize session state for storing points
if 'points' not in st.session_state:
    st.session_state.points = []

# Create a base map centered on the Netherlands
def create_base_map():
    # Coordinates for Netherlands center
    netherlands_center = [52.1326, 5.2913]

    # Create map with OpenStreetMap tiles
    m = folium.Map(
        location=netherlands_center,
        zoom_start=7,
        tiles="OpenStreetMap",
        attr="OpenStreetMap contributors"
    )

    # Add draw control for creating points
    draw = Draw(
        export=True,
        filename="netherlands_points.geojson",
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

    # Add existing points from session state
    for point in st.session_state.points:
        folium.Marker(
            location=[point['lat'], point['lon']],
            popup=f"Point {point['id']}",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)

    return m

# Create the map
m = create_base_map()

# Display the map in Streamlit
output = st_folium(m, width=1000, height=600)

# Check if any features were drawn
if output.get("last_active_drawing"):
    # Get the last drawn feature
    drawn_feature = output["last_active_drawing"]

    # Extract coordinates
    if drawn_feature["geometry"]["type"] == "Point":
        coords = drawn_feature["geometry"]["coordinates"]
        lon, lat = coords[0], coords[1]

        # Create a new point ID
        new_id = len(st.session_state.points) + 1

        # Add to session state
        st.session_state.points.append({
            "id": new_id,
            "lat": lat,
            "lon": lon
        })

        # Show success message
        st.success(f"Point {new_id} added at ({lat:.4f}, {lon:.4f})")

# Display current points in a table
if st.session_state.points:
    st.subheader("Current Points")
    points_df = pd.DataFrame(st.session_state.points)
    st.dataframe(points_df, use_container_width=True)

    # Option to download points as CSV
    csv = points_df.to_csv(index=False)
    st.download_button(
        label="Download Points as CSV",
        data=csv,
        file_name="netherlands_points.csv",
        mime="text/csv"
    )

    # Option to clear all points
    if st.button("Clear All Points"):
        st.session_state.points = []
        st.rerun()
else:
    st.info("No points have been added yet. Click on the map to add points.")

# Sidebar with instructions
with st.sidebar:
    st.header("Instructions")
    st.markdown("""
    1. **Add Points**: Click the marker icon in the top-left corner, then click on the map to place points.
    2. **View Points**: Added points will appear in the table below the map.
    3. **Download**: Export your points as a CSV file.
    4. **Clear**: Remove all points with the "Clear All Points" button.
    """)

    st.header("About")
    st.markdown("""
    This app uses:
    - **Streamlit** for the web interface
    - **Folium** for interactive maps
    - **OpenStreetMap** for map tiles
    - **GeoPandas** for geospatial operations
    """)