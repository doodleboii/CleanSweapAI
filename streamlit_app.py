import streamlit as st
import pandas as pd
import requests
from db import SessionLocal, Forecast, CleaningTask
from datetime import datetime

st.set_page_config(page_title="CleanSweep AI Dashboard", layout="wide")

# Sidebar menu
page = st.sidebar.selectbox("Select Page", ["Dashboard", "History"])

# Function to load data from DB
def load_data():
    session = SessionLocal()

    indoor_forecast = session.query(Forecast).filter(Forecast.location_type == 'indoor').all()
    road_forecast = session.query(Forecast).filter(Forecast.location_type == 'road').all()
    indoor_tasks = session.query(CleaningTask).filter(CleaningTask.location_type == 'indoor').all()
    road_tasks = session.query(CleaningTask).filter(CleaningTask.location_type == 'road').all()

    session.close()

    indoor_df = pd.DataFrame([{'ds': row.timestamp, 'yhat': row.predicted_value} for row in indoor_forecast])
    road_df = pd.DataFrame([{'ds': row.timestamp, 'yhat': row.predicted_value} for row in road_forecast])
    indoor_task_df = pd.DataFrame([{
        'time': task.time, 'task': task.task, 'priority': task.priority
    } for task in indoor_tasks])
    road_task_df = pd.DataFrame([{
        'time': task.time, 'task': task.task, 'priority': task.priority
    } for task in road_tasks])

    return indoor_df, road_df, indoor_task_df, road_task_df

if page == "Dashboard":
    st.title("🧹 CleanSweep AI – Predictive Cleaning Dashboard")

    if st.button("🔄 Refresh Predictions"):
        response = requests.get("http://127.0.0.1:5000/predict-cleaning")
        if response.status_code == 200:
            st.success("Predictions updated successfully!")
            st.rerun()

        else:
            st.error("Failed to update. Check if Flask server is running.")

    indoor_df, road_df, indoor_task_df, road_task_df = load_data()

    st.subheader("📈 Footfall Forecast")
    st.write("### Indoor")
    st.line_chart(indoor_df.set_index('ds')['yhat'])
    st.write("### Roads")
    st.line_chart(road_df.set_index('ds')['yhat'])

    st.subheader("🧼 Scheduled Cleaning Tasks")
    st.write("### Indoor Tasks")
    st.dataframe(indoor_task_df)
    st.write("### Road Tasks")
    st.dataframe(road_task_df)

elif page == "History":
    st.title("📜 History of Forecasts and Cleaning Tasks")

    indoor_df, road_df, indoor_task_df, road_task_df = load_data()

    # Date filter
    min_date = min(indoor_df['ds'].min(), road_df['ds'].min())
    max_date = max(indoor_df['ds'].max(), road_df['ds'].max())
    start_date = st.date_input("Start Date", min_date.date() if pd.notnull(min_date) else None)
    end_date = st.date_input("End Date", max_date.date() if pd.notnull(max_date) else None)

    if start_date and end_date:
        mask_indoor = (indoor_df['ds'] >= pd.Timestamp(start_date)) & (indoor_df['ds'] <= pd.Timestamp(end_date))
        mask_road = (road_df['ds'] >= pd.Timestamp(start_date)) & (road_df['ds'] <= pd.Timestamp(end_date))
        indoor_df_filtered = indoor_df[mask_indoor]
        road_df_filtered = road_df[mask_road]

        mask_task_indoor = (indoor_task_df['time'] >= pd.Timestamp(start_date)) & (indoor_task_df['time'] <= pd.Timestamp(end_date))
        mask_task_road = (road_task_df['time'] >= pd.Timestamp(start_date)) & (road_task_df['time'] <= pd.Timestamp(end_date))
        indoor_task_df_filtered = indoor_task_df[mask_task_indoor]
        road_task_df_filtered = road_task_df[mask_task_road]

        st.write("### Indoor Forecast History")
        st.dataframe(indoor_df_filtered)

        st.write("### Road Forecast History")
        st.dataframe(road_df_filtered)

        st.write("### Indoor Cleaning Task History")
        st.dataframe(indoor_task_df_filtered)

        st.write("### Road Cleaning Task History")
        st.dataframe(road_task_df_filtered)
    else:
        st.info("Please select start and end dates to filter the history.")
