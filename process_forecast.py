import streamlit as st
import numpy as np
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from datetime import timedelta

from get_measured_data import get_wind_measurements

async def get_forecast_soar(model = "knmi_seamless"):
    forecast = []
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": [point["lat"] for point in st.session_state.soar_points],
        "longitude": [point["lon"] for point in st.session_state.soar_points],
        "daily": ["sunrise", "sunset"],
        "hourly": ["temperature_2m", "visibility", "precipitation"],
        "models": model,
        "timezone": "Europe/Berlin",
        "past_days": 1,
        "forecast_days": 7,
    }

    offshore_params = {
        "latitude": [point["offshore_lat"] for point in st.session_state.soar_points],
        "longitude": [point["offshore_lon"] for point in st.session_state.soar_points],
        "hourly": ["wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"],
        "models": model,
        "timezone": "Europe/Berlin",
        "past_days": 1,
        "forecast_days": 7,
    }

    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    responses = openmeteo.weather_api(url, params=params)
    offshore_responses = openmeteo.weather_api(url, params=offshore_params)

    for id, response in enumerate(responses):
        hourly = response.Hourly()
        offshore_hourly = offshore_responses[id].Hourly()

        hourly_data = {
            "date": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            ),
            "temperature": hourly.Variables(0).ValuesAsNumpy(),
            "visibility": hourly.Variables(1).ValuesAsNumpy(),
            "wind_speed": offshore_hourly.Variables(0).ValuesAsNumpy(),
            "wind_direction": offshore_hourly.Variables(1).ValuesAsNumpy(),
            "wind_gusts": offshore_hourly.Variables(2).ValuesAsNumpy(),
            "precipitation": hourly.Variables(2).ValuesAsNumpy()
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
    if model == "knmi_seamless":
        st.session_state.raw_forecast['soar_knmi'] = forecast
    else:
        st.session_state.raw_forecast['soar_ecmwf'] = forecast

async def get_forecast_therm():
    forecast = []
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": [point["lat"] for point in st.session_state.therm_points],
        "longitude": [point["lon"] for point in st.session_state.therm_points],
        "daily": ["sunrise", "sunset"],
        "hourly": ["temperature_2m", "visibility", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "precipitation", "temperature_1000hPa", "temperature_925hPa", "temperature_850hPa", "temperature_700hPa", "direct_radiation"],
        "models": "ecmwf_ifs",
        "timezone": "Europe/Berlin",
        "past_days": 1,
        "forecast_days": 7,
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
            "precipitation": hourly.Variables(5).ValuesAsNumpy(),
            "temperature_110m": hourly.Variables(6).ValuesAsNumpy(),
            "temperature_800m": hourly.Variables(7).ValuesAsNumpy(),
            "temperature_1500m": hourly.Variables(8).ValuesAsNumpy(),
            "temperature_3000m": hourly.Variables(9).ValuesAsNumpy(),
            "solar_irradiation": hourly.Variables(10).ValuesAsNumpy()
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

async def process_soar_forecast(model="soar_knmi"):
    dates = list(set([date.date() for date in st.session_state.raw_forecast[model][0]["daily_data"]["date"]]))
    dates.sort()

    if 'date_list' not in st.session_state:
        st.session_state.date_list = dates

    forecast = []
    for date in dates:
        daily = [{
            "sunrise": next(data for i, data in enumerate(point_forecast["daily_data"]["sunrise"])
                        if point_forecast["daily_data"]["date"][i].date() == date),
            "sunset": next(data for i, data in enumerate(point_forecast["daily_data"]["sunset"])
                        if point_forecast["daily_data"]["date"][i].date() == date)
        } for point_forecast in st.session_state.raw_forecast[model]]

        day_forecast = [{
            "sunrise": daily[point]["sunrise"],
            "sunset": daily[point]["sunset"],
            "time": [time for time in point_forecast["hourly_data"]["date"]
                    if (time >= start_day(daily, point) and time <= end_day(daily, point))],
            "temperature": [data for i, data in enumerate(point_forecast["hourly_data"]["temperature"])
                        if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                            and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))],
            "precipitation": [data for i, data in enumerate(point_forecast["hourly_data"]["precipitation"])
                            if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                                and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))],
            "visibility": [data for i, data in enumerate(point_forecast["hourly_data"]["visibility"])
                        if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                            and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))],
            "wind_speed": [data for i, data in enumerate(point_forecast["hourly_data"]["wind_speed"])
                        if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                            and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))],
            "wind_speed_measured": [data for i, data in enumerate(point_forecast["hourly_data"]["wind_speed"])
                        if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                            and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))],
            "wind_direction": [data for i, data in enumerate(point_forecast["hourly_data"]["wind_direction"])
                            if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                                and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))],
            "wind_gusts": [data for i, data in enumerate(point_forecast["hourly_data"]["wind_gusts"])
                        if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                            and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))]
        } for point, point_forecast in enumerate(st.session_state.raw_forecast[model])]
        forecast.append(day_forecast)
    
    st.session_state.forecast[model] = forecast


async def process_therm_forecast():
    dates = list(set([date.date() for date in st.session_state.raw_forecast[0]["daily_data"]["date"]]))
    dates.sort()

    if 'date_list' not in st.session_state:
        st.session_state.date_list = dates

    forecast = []
    for date in dates:
        daily = [{
            "sunrise": next(data for i, data in enumerate(point_forecast["daily_data"]["sunrise"])
                        if point_forecast["daily_data"]["date"][i].date() == date),
            "sunset": next(data for i, data in enumerate(point_forecast["daily_data"]["sunset"])
                        if point_forecast["daily_data"]["date"][i].date() == date)
        } for point_forecast in st.session_state.raw_forecast]

        day_forecast = [{
            "sunrise": daily[point]["sunrise"],
            "sunset": daily[point]["sunset"],
            "time": [time for time in point_forecast["hourly_data"]["date"]
                    if (time >= start_day(daily, point) and time <= end_day(daily, point))],
            "temperature": [data for i, data in enumerate(point_forecast["hourly_data"]["temperature"])
                        if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                            and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))],
            "temperature_110m": [data for i, data in enumerate(point_forecast["hourly_data"]["temperature_110m"])
                        if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                            and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))],
            "temperature_800m": [data for i, data in enumerate(point_forecast["hourly_data"]["temperature_800m"])
                        if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                            and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))],
            "temperature_1500m": [data for i, data in enumerate(point_forecast["hourly_data"]["temperature_1500m"])
                        if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                            and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))],
            "temperature_3000m": [data for i, data in enumerate(point_forecast["hourly_data"]["temperature_3000m"])
                        if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                            and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))],
            "solar_irradiation": [data for i, data in enumerate(point_forecast["hourly_data"]["solar_irradiation"])
                        if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                            and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))],
            "precipitation": [data for i, data in enumerate(point_forecast["hourly_data"]["precipitation"])
                            if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                                and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))],
            "visibility": [data for i, data in enumerate(point_forecast["hourly_data"]["visibility"])
                        if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                            and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))],
            "wind_speed": [data for i, data in enumerate(point_forecast["hourly_data"]["wind_speed"])
                        if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                            and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))],
            "wind_direction": [data for i, data in enumerate(point_forecast["hourly_data"]["wind_direction"])
                            if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                                and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))],
            "wind_gusts": [data for i, data in enumerate(point_forecast["hourly_data"]["wind_gusts"])
                        if (point_forecast["hourly_data"]["date"][i] >= start_day(daily, point)
                            and point_forecast["hourly_data"]["date"][i] <= end_day(daily, point))]
        } for point, point_forecast in enumerate(st.session_state.raw_forecast)]
        forecast.append(day_forecast)
    return forecast

def forecast_display_soar(forecast):
    disp_forecast = []
    for day_idx, day in enumerate(forecast):
        day_forecast = []
        for i, point_forecast in enumerate(day):
            point = st.session_state.soar_points[i]
            wind_pizza = np.zeros(3)
            start = None
            prev = None
            gantt = []
            last_time = None
            for i, time in enumerate(point_forecast["time"]):
                
                # Check basic conditions
                if start_window(time) < time < end_window(time) \
                and point_forecast["precipitation"][i] < 0.01 \
                and point_forecast["visibility"][i] > 99 \
                and point_forecast["wind_speed"][i] > point['wind_range'][0] \
                and point_forecast["wind_gusts"][i] < point['wind_range'][1]:
                    rel_head = point_forecast["wind_direction"][i] - point["heading"]
                    if point['head_range'][0] < rel_head < -22.5:
                        if prev != 'cross':
                            if prev is not None:
                                gantt.append([prev, (start, time+timedelta(days=-day_idx))])
                            start = time+timedelta(days=-day_idx)
                        wind_pizza[0] += 1
                        prev = 'cross'
                    elif -22.5 < rel_head < 22.5:
                        if prev != 'good':
                            if prev is not None:
                                gantt.append([prev, (start, time+timedelta(days=-day_idx))])
                            start = time+timedelta(days=-day_idx)
                        wind_pizza[1] += 1
                        prev = 'good'
                    elif  22.5 < rel_head < point['head_range'][1]:
                        if prev != 'cross':
                            if prev is not None:
                                gantt.append([prev, (start, time+timedelta(days=-day_idx))])
                            start = time+timedelta(days=-day_idx)
                        wind_pizza[2] += 1
                        prev = 'cross'
                    else:
                        if prev != 'no':
                            if prev is not None:
                                gantt.append([prev, (start, time+timedelta(days=-day_idx))])
                            start = time+timedelta(days=-day_idx)
                        prev = 'no' 
                else:
                    if prev != 'no':
                        if prev is not None:
                            gantt.append([prev, (start, time+timedelta(days=-day_idx))])
                        start = time+timedelta(days=-day_idx)
                    prev = 'no' 
                last_time = time
            gantt.append([prev, (start, last_time+timedelta(days=-day_idx))])         

            good_hours = wind_pizza[1]
            cross_hours = wind_pizza[0] + wind_pizza[2]
            day_forecast.append({"gantt": gantt, "wind_pizza": wind_pizza, "good_hours": good_hours, "cross_hours": cross_hours})
        disp_forecast.append(day_forecast)
    return disp_forecast

def forecast_display_therm(forecast):
    disp_forecast = []
    for day in forecast:
        day_forecast = []
        for i, point_forecast in enumerate(day):
            point = st.session_state.soar_points[i]
            for i, time in enumerate(point_forecast["time"]):
                flyable_hours = 0
                thermal_hours = 0
                # Check basic conditions
                if point_forecast["precipitation"][i] < 0.01 and point_forecast["visibility"][i] > 0.5 and point_forecast["wind_speed"][i] < point['wind_range'][1]:
                    # Check if wind direction is within acceptable range
                    start_heading = point.get("start_heading_range", 0)
                    end_heading = point.get("end_heading_range", 360)

                    wind_dir = point_forecast["wind_direction"][i]
                    wind_ok = False

                    # Handle heading range that crosses 0° (e.g., 270°-90°)
                    if start_heading > end_heading:
                        if wind_dir >= start_heading or wind_dir <= end_heading:
                            wind_ok = True
                    else:
                        if start_heading <= wind_dir and  wind_dir <= end_heading:
                            wind_ok = True
                    if wind_ok:
                        flyable_hours += 1
                        env_lapse_rate = (point_forecast["temperature"][i] - point_forecast["temperature_800m"][i])/0.8
                        irradiation = point_forecast["solar_irradiation"][i]
                        
                        if env_lapse_rate >= 7 and irradiation >= 200:
                            thermal_hours += 1
                        
            day_forecast.append({"flyable_hours": flyable_hours, "thermal_hours": thermal_hours})
        disp_forecast.append(day_forecast)
    return disp_forecast

def start_day(daily, point):
    return daily[point]["sunrise"]+timedelta(hours=-1)

def end_day(daily, point):
    return daily[point]["sunset"]+timedelta(hours=2)

def start_window(time):
    return time.replace(hour=st.session_state.user.time_range[0].hour, minute=st.session_state.user.time_range[0].minute)

def end_window(time):
    return time.replace(hour=st.session_state.user.time_range[1].hour, minute=st.session_state.user.time_range[1].minute)
