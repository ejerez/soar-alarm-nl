import streamlit as st
import numpy as np
import plotly.graph_objects as go

from process_forecast import *

def disp_point_forecast(session_state):

    # Point selection
    if session_state.user.mode == 'soar':
        point_options = [point['name'] for point in session_state.soar_points]
    else:
        point_options = [point['name'] for point in session_state.therm_points]
    
    select_point = st.selectbox(
        "Select Point",
        options=point_options,
        index=session_state.selected_point_idx,
        key="point_selector"
    )

    selected_point_idx = point_options.index(select_point)

    if session_state.selected_point_idx != selected_point_idx:
        session_state.selected_point_idx = selected_point_idx

    model = "soar_kmni" if session_state.user.model == "KNMI" else "soar_ecmwf"

    # Get forecast data
    if session_state.user.mode == 'soar':
        selected_point = session_state.soar_points[session_state.selected_point_idx]
        day_forecast = session_state.forecast[model][session_state.selected_date_idx][session_state.selected_point_idx]
    else:
        selected_point = session_state.therm_points[session_state.selected_point_idx]
        day_forecast = session_state.forecast["therm"][session_state.selected_date_idx][session_state.selected_point_idx]

    button_location = st.link_button(f'How to get to {select_point} (Google Maps)', rf"https://www.google.com/maps/place/{selected_point['lat']}N+{selected_point['lon']}E")

    if day_forecast["time"]:
        # Wind Speed and Gust Speed Graph
        st.subheader("Wind Speed and Gusts")
        fig_wind = go.Figure()

        fig_wind.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["wind_speed"],
            name="Wind Speed",
            line=dict(color='blue', width=0),
            line_shape='spline',
            fill='tonexty',
            fillcolor="blue",
            yaxis="y1",
            opacity=0,
            mode="lines"
        ))

        fig_wind.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["wind_gusts"],
            name="Gust Speed",
            line=dict(color='orange', width=0),
            line_shape='spline',
            fill='tonexty',
            fillcolor="orange",
            yaxis="y1",
            opacity=0,
            mode="lines"
        ))

        fig_wind.add_trace(go.Scatter(
            x=day_forecast["time"],
            y=day_forecast["precipitation"],
            name="Precipitation",
            line=dict(color='lightblue', width=0),
            line_shape='spline',
            fill='tonexty',
            fillcolor='lightblue',
            mode="lines",
            yaxis="y2",
            opacity=0
        ))

        if session_state.user.mode == 'soar':
            fig_wind.add_hrect(y0=selected_point['wind_range'][0], y1=selected_point['wind_range'][1],
                                fillcolor="rgba(153,255,51,0.7)", opacity=0.5, line_width=0)
        else:  # Thermal
            max_wind = selected_point.get("max_wind_speed", 30)
            fig_wind.add_hrect(y0=0, y1=max_wind, fillcolor="rgba(153,255,51,0.7)", opacity=0.5, line_width=0)

        fig_wind.update_layout(
            title="Wind Speed and Gusts",
            xaxis=dict(title="Time", fixedrange=True),
            yaxis=dict(title="Speed (km/h)", side="left", fixedrange=True),
            yaxis2=dict(title="Precipitation (mm)", overlaying="y", side="right", fixedrange=True),
            hovermode="x unified",
            height=400,
            legend=dict(orientation="h")
        )

        st.plotly_chart(fig_wind, width='stretch', on_select='ignore')

        # Wind Direction Graph
        st.subheader("Wind Direction")
        fig_dir = go.Figure()

        if session_state.user.mode == 'soar':
            lower_bound = selected_point["heading"] + selected_point["head_range"][0]
            lower_ideal = selected_point["heading"] - 22.5
            upper_ideal = selected_point["heading"] + 22.5
            upper_bound = selected_point["heading"] + selected_point["head_range"][1]

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
            line_shape='spline',
            mode="lines"
        ))

        if session_state.user.mode == 'soar':
            fig_dir.add_hline(y=selected_point["heading"], line_dash="dot", line_color="grey",
                            annotation_text=f"Ideal ({selected_point['heading']}°)")

        fig_dir.update_layout(
            title=f"Wind Direction (Acceptable Range)",
            xaxis=dict(title="Time", fixedrange=True),
            yaxis=dict(title="Direction (°)", fixedrange=True),
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
            line_shape='spline',
            mode="lines"
        ))

        fig_temp_precip.add_trace(go.Bar(
            x=day_forecast["time"],
            y=day_forecast["precipitation"],
            name="Precipitation",
            marker_color='lightblue',
            yaxis="y2",
            opacity=0.5
        ))

        # Add visibility threshold line
        visibility_threshold = 0.1 if session_state.user.mode == 'soar' else 0.5
        fig_temp_precip.add_hline(y=visibility_threshold, line_dash="dot", line_color="red",
                                annotation_text=f"Min Visibility: {visibility_threshold}")

        fig_temp_precip.update_layout(
            title="Temperature, Precipitation and Visibility",
            xaxis=dict(title="Time", fixedrange=True),
            yaxis=dict(title="Temperature (°C)", side="left", fixedrange=True),
            yaxis2=dict(title="Precipitation (mm)", overlaying="y", side="right", fixedrange=True),
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