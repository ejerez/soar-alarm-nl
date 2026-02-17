import streamlit as st
from streamlit_folium import st_folium

from make_gis_map import *

def disp_edit_points(session_state):

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

                if session_state.mode == "soar":
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

                    if session_state.mode == "soar":
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

                    if session_state.mode == "soar":
                        session_state.soar_points.append(new_point)
                    else:
                        session_state.therm_points.append(new_point)
                    st.success(f"{name} saved!")
                    # Clear cached forecasts since points changed
                    session_state.forecast = None
                    session_state.all_day_forecasts = {}
                    session_state.all_display_forecasts = {}
                    st.rerun()

    st.subheader("Manage Points")
    if session_state.mode == "soar":
        points_df = pd.DataFrame(session_state.soar_points)
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
        if session_state.mode == "soar":
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
                if session_state.mode == "soar":
                    session_state.soar_points = [p for p in session_state.soar_points if p['id'] not in to_delete]
                else:
                    session_state.therm_points = [p for p in session_state.therm_points if p['id'] not in to_delete]
                st.success(f"Deleted {len(to_delete)} point(s)")
                # Clear cached forecasts since points changed
                session_state.forecast = None
                session_state.all_day_forecasts = {}
                session_state.all_display_forecasts = {}
                st.rerun()

        # Handle edits for type-specific columns
        editable_columns = ['name', 'lat', 'lon']
        if session_state.mode == "soar":
            editable_columns.extend(['heading', 'steepness'])
        else:
            editable_columns.extend(['start_heading_range', 'end_heading_range', 'max_wind_speed'])

        if not edited_df[editable_columns].equals(points_df[editable_columns]):
            if session_state.mode == "soar":
                session_state.soar_points = edited_df.drop('Delete', axis=1).to_dict('records')
            else:
                session_state.therm_points = edited_df.drop('Delete', axis=1).to_dict('records')
            st.success("Points updated!")
            # Clear cached forecasts since points changed
            session_state.forecast = None
            session_state.all_day_forecasts = {}
            session_state.all_display_forecasts = {}
            st.rerun(scope="app")
