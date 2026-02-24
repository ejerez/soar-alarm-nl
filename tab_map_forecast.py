import streamlit as st
from streamlit_folium import st_folium
import plotly.graph_objects as go
import plotly.figure_factory as ff
import plotly.express as px

from process_forecast import *
from make_gis_map import *

def disp_map_forecast(session_state):
    # Create and display map with current date's forecast
    model = "soar_kmni" if session_state.user.model == "KNMI" else "soar_ecmwf"
    
    if session_state.user.mode == 'soar':
        current_map = create_soar_map_forecast(session_state.selected_date_idx, model=model)
    else:
        current_map = create_therm_map_forecast(session_state.selected_date_idx, model=model)

    st_folium(current_map, width=500, height=450, key=f"map_{session_state.selected_date_idx}")

    # Temperature and Precipitation Graph
    st.subheader("Flyable Hours Per Day")
    fig_flyable = go.Figure()

    forecast = session_state.disp_forecast[model]
    good_per_day = []
    marginal_per_day = []
    total_per_day = []
    best_per_day = []
    gantt_per_day = []
    for day, date_forecast in enumerate(forecast):
        points = []
        max_flyable = 0
        max_good = 0
        best = None
        best_flyable = None
        for index, point_forecast in enumerate(date_forecast):
            good = point_forecast['good_hours']
            marginal = point_forecast['cross_hours']
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
        gantt_raw = date_forecast[best]['gantt']

        for gantt in gantt_raw:
            gantt_per_day.append(
                dict(Wind='Not flyable' if gantt[0]=='no' else 'Good' if gantt[0]=='good' else 'Cross', 
                     Point=session_state.soar_points[best]['name'], Start=gantt[1][0], Finish=gantt[1][1], Day=session_state.day_list[day])
                )

    if session_state.user.mode == 'soar':
        best_point_list = [session_state.soar_points[idx]['name'] for idx in best_per_day]
    else:
        best_point_list = [session_state.therm_points[idx]['name'] for idx in best_per_day]

    gantt_flyable = pd.DataFrame(gantt_per_day)[::-1]
    
    flyable = px.timeline(
    gantt_flyable, 
    x_start="Start", 
    x_end="Finish", 
    y="Day",
    color="Wind",
    text="Point",
    color_discrete_map = {'Not flyable': '#000000' if st.session_state.dark_theme else '#FFFFFF', 'Good': '#1FD100', 'Cross': '#D68800'}
    )

    flyable.update_layout(showlegend=False)

    fig_flyable.add_trace(go.Bar(
        x=session_state.day_list,
        y=marginal_per_day,
        text=best_point_list,
        name="Crosswind",
        marker_color='orange',
        yaxis="y",
    ))

    fig_flyable.add_trace(go.Bar(
        x=session_state.day_list,
        y=good_per_day,
        text=best_point_list,
        name="Good",
        marker_color='green',
        yaxis="y",
    ))

    fig_flyable.update_layout(
        barmode='stack', 
        legend=dict(orientation="h"),
        xaxis=dict(title="Day", fixedrange=True),
        yaxis=dict(title="Hours", side="left", fixedrange=True)
        )
    st.plotly_chart(fig_flyable, width='stretch', on_select='ignore')

    st.plotly_chart(flyable, width='stretch', on_select='ignore')
