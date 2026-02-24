import streamlit as st
from streamlit_folium import st_folium

from make_gis_map import *

def disp_edit_points(session_state):

    st.subheader("Manage Points")
    if session_state.user.mode == "soar":
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
        if session_state.user.mode == "soar":
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
                if session_state.user.mode == "soar":
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
        if session_state.user.mode == "soar":
            editable_columns.extend(['heading', 'steepness'])
        else:
            editable_columns.extend(['start_heading_range', 'end_heading_range', 'max_wind_speed'])

        if not edited_df[editable_columns].equals(points_df[editable_columns]):
            if session_state.user.mode == "soar":
                session_state.soar_points = edited_df.drop('Delete', axis=1).to_dict('records')
            else:
                session_state.therm_points = edited_df.drop('Delete', axis=1).to_dict('records')
            st.success("Points updated!")
            # Clear cached forecasts since points changed
            session_state.forecast = None
            session_state.all_day_forecasts = {}
            session_state.all_display_forecasts = {}
            st.rerun(scope="app")
