import streamlit as st
from streamlit_folium import st_folium
import plotly.graph_objects as go

from process_forecast import *
from make_gis_map import *

def disp_map_forecast(session_state):
    # Create and display map with current date's forecast
    if session_state.mode == 'soar':
        current_map = create_soar_map_forecast(session_state.selected_date_idx)
    else:
        current_map = create_therm_map_forecast(session_state.selected_date_idx)

    st_folium(current_map, width=1000, height=600, key=f"map_{session_state.selected_date_idx}")

    # Temperature and Precipitation Graph
    st.subheader("Flyable Hours Per Day")
    fig_flyable = go.Figure()

    model = "soar_kmni" if session_state.model == "KNMI" else "soar_ecmwf"
    forecast = session_state.disp_forecast[model]
    good_per_day = []
    marginal_per_day = []
    total_per_day = []
    best_per_day = []
    for date_forecast in forecast:
        points = []
        max_flyable = 0
        max_good = 0
        best = None
        best_flyable = None
        for index, point_forecast in enumerate(date_forecast):
            good = point_forecast['good_hours']
            marginal = point_forecast['marginal_hours']
            flyable = good+marginal
            if good > max_good:
                max_good = good
                best = index
            if flyable > max_flyable:
                max_flyable = flyable
                best_flyable = index
            points.append([good, marginal])
        if best == None:
            best = best_flyable
        if best == None:
            best = 0
        good_per_day.append(points[best][0])
        marginal_per_day.append(points[best][1])
        total_per_day.append(points[best][0]+points[best][1])
        best_per_day.append(best)

    if session_state.mode == 'soar':
        best_point_list = [session_state.soar_points[idx]['name'] for idx in best_per_day]
    else:
        best_point_list = [session_state.therm_points[idx]['name'] for idx in best_per_day]

    fig_flyable.add_trace(go.Bar(
        x=session_state.day_list,
        y=marginal_per_day,
        text=best_point_list,
        name="Marginal hours per day",
        marker_color='orange',
        yaxis="y",
    ))

    fig_flyable.add_trace(go.Bar(
        x=session_state.day_list,
        y=good_per_day,
        text=best_point_list,
        name="Good hours per day",
        marker_color='green',
        yaxis="y",
    ))

    fig_flyable.update_layout(barmode='stack', legend=dict(orientation="h"))
    st.plotly_chart(fig_flyable, width='stretch', on_select='ignore')
