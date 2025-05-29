import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

st.set_page_config(page_title="CleanSweep AI", layout="wide")

# --- Load Data ---
def load_data():
    conn = sqlite3.connect("cleansweep.db")
    indoor_df = pd.read_sql_query("SELECT * FROM TrafficData WHERE location_type='indoor'", conn)
    road_df = pd.read_sql_query("SELECT * FROM TrafficData WHERE location_type='road'", conn)
    forecast_df = pd.read_sql_query("SELECT * FROM Forecast", conn)
    task_df = pd.read_sql_query("SELECT * FROM CleaningTask", conn)
    conn.close()
    return indoor_df, road_df, forecast_df, task_df

# --- Display Header ---
st.title("🧼 CleanSweep AI: Smart Facility Cleaning Dashboard")

# --- Load Data ---
indoor, road, forecast, tasks = load_data()

# --- Tabs for Indoor and Road ---
tab1, tab2 = st.tabs(["🏢 Indoor", "🛣️ Road"])

with tab1:
    st.subheader("📊 Indoor Footfall")
    fig = px.line(indoor, x="timestamp", y="value", title="Indoor Foot Traffic")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🔮 Forecasted Indoor Usage (Next 24h)")
    indoor_forecast = forecast[forecast["location_type"] == "indoor"]
    fig2 = px.line(indoor_forecast, x="timestamp", y="predicted_value", title="Indoor Forecast")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("🧹 Cleaning Tasks - Indoor")
    indoor_tasks = tasks[tasks["location_type"] == "indoor"]
    st.dataframe(indoor_tasks)

with tab2:
    st.subheader("📊 Road Foot Traffic")
    fig3 = px.line(road, x="timestamp", y="value", title="Road Traffic")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("🔮 Forecasted Road Usage (Next 24h)")
    road_forecast = forecast[forecast["location_type"] == "road"]
    fig4 = px.line(road_forecast, x="timestamp", y="predicted_value", title="Road Forecast")
    st.plotly_chart(fig4, use_container_width=True)

    st.subheader("🧹 Cleaning Tasks - Road")
    road_tasks = tasks[tasks["location_type"] == "road"]
    st.dataframe(road_tasks)

# --- Refresh Button ---
if st.button("🔄 Refresh Data"):
    st.experimental_rerun()
