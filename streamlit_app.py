import streamlit as st
import pandas as pd
import requests
from db import SessionLocal, Forecast, CleaningTask
from datetime import datetime
import altair as alt

st.set_page_config(page_title="CleanSweep AI Dashboard", layout="wide")

# Sidebar menu
page = st.sidebar.selectbox("Select Page", ["Dashboard", "History", "Task Report"])

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
        'time': task.time, 'task': task.task, 'priority': task.priority, 'location': 'Indoor'
    } for task in indoor_tasks])
    road_task_df = pd.DataFrame([{
        'time': task.time, 'task': task.task, 'priority': task.priority, 'location': 'Road'
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
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Indoor Traffic Forecast")
        indoor_chart = alt.Chart(indoor_df).mark_line(color='green').encode(
            x='ds:T', y='yhat:Q'
        ).properties(height=300)
        st.altair_chart(indoor_chart, use_container_width=True)

    with col2:
        st.markdown("#### Road Traffic Forecast")
        road_chart = alt.Chart(road_df).mark_line(color='orange').encode(
            x='ds:T', y='yhat:Q'
        ).properties(height=300)
        st.altair_chart(road_chart, use_container_width=True)

    st.subheader("🧼 Scheduled Cleaning Tasks")
    priority_filter = st.selectbox("Filter by Priority", ["All", "High", "Medium", "Low"])

    # Create copies of the dataframes to avoid modifying the originals
    filtered_indoor_tasks = indoor_task_df.copy()
    filtered_road_tasks = road_task_df.copy()

    if priority_filter != "All":
        filtered_indoor_tasks = filtered_indoor_tasks[filtered_indoor_tasks['priority'].str.lower() == priority_filter.lower()]
        filtered_road_tasks = filtered_road_tasks[filtered_road_tasks['priority'].str.lower() == priority_filter.lower()]

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("#### Indoor Cleaning Tasks")
        st.dataframe(filtered_indoor_tasks.sort_values('time'))

    with col4:
        st.markdown("#### Road Cleaning Tasks")
        st.dataframe(filtered_road_tasks.sort_values('time'))

elif page == "History":
    st.title("📜 History of Forecasts and Cleaning Tasks")

    indoor_df, road_df, indoor_task_df, road_task_df = load_data()

    # Date range selector in sidebar
    st.sidebar.subheader("Historical Trends Filter")
    min_date = min(indoor_df['ds'].min(), road_df['ds'].min())
    max_date = max(indoor_df['ds'].max(), road_df['ds'].max())
    start_date = st.sidebar.date_input("Start Date", min_date.date() if pd.notnull(min_date) else None)
    end_date = st.sidebar.date_input("End Date", max_date.date() if pd.notnull(max_date) else None)

    if start_date and end_date:
        # Filter data based on date range
        mask_indoor = (indoor_df['ds'] >= pd.Timestamp(start_date)) & (indoor_df['ds'] <= pd.Timestamp(end_date))
        mask_road = (road_df['ds'] >= pd.Timestamp(start_date)) & (road_df['ds'] <= pd.Timestamp(end_date))
        
        filtered_indoor = indoor_df[mask_indoor]
        filtered_road = road_df[mask_road]

        # Display historical trends
        st.subheader("📈 Historical Traffic Trends")
        
        # Indoor Traffic Chart
        st.markdown("### Indoor Footfall")
        indoor_chart = alt.Chart(filtered_indoor).mark_line(color='green').encode(
            x='ds:T',
            y='yhat:Q',
            tooltip=['ds:T', 'yhat:Q']
        ).properties(
            height=300,
            title='Indoor Footfall Over Time'
        )
        st.altair_chart(indoor_chart, use_container_width=True)

        # Road Traffic Chart
        st.markdown("### Road Traffic")
        road_chart = alt.Chart(filtered_road).mark_line(color='orange').encode(
            x='ds:T',
            y='yhat:Q',
            tooltip=['ds:T', 'yhat:Q']
        ).properties(
            height=300,
            title='Road Traffic Over Time'
        )
        st.altair_chart(road_chart, use_container_width=True)

        # Display historical data tables
        st.subheader("📊 Historical Data Tables")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Indoor Forecast History")
            st.dataframe(filtered_indoor)
        
        with col2:
            st.markdown("### Road Forecast History")
            st.dataframe(filtered_road)

        # Display task history
        st.subheader("🧹 Cleaning Task History")
        indoor_task_df_filtered = indoor_task_df[(indoor_task_df['time'] >= pd.Timestamp(start_date)) & 
                                               (indoor_task_df['time'] <= pd.Timestamp(end_date))]
        road_task_df_filtered = road_task_df[(road_task_df['time'] >= pd.Timestamp(start_date)) & 
                                           (road_task_df['time'] <= pd.Timestamp(end_date))]

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("### Indoor Cleaning Tasks")
            st.dataframe(indoor_task_df_filtered)
        
        with col4:
            st.markdown("### Road Cleaning Tasks")
            st.dataframe(road_task_df_filtered)
    else:
        st.info("Please select start and end dates to view historical data.")

elif page == "Task Report":
    st.title("📊 Downloadable Task Report")
    _, _, indoor_task_df, road_task_df = load_data()
    all_tasks = pd.concat([indoor_task_df, road_task_df], ignore_index=True)
    all_tasks = all_tasks.sort_values(by='time')
    st.dataframe(all_tasks)

    csv = all_tasks.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Task Report as CSV", data=csv, file_name="cleaning_tasks_report.csv", mime='text/csv')
    
    
    
    
    # After loading historical data dfs (indoor_df, road_df)...
def color_priority(val):
    color = ''
    if val == 'High':
        color = 'background-color: #FF4C4C'  # red
    elif val == 'Medium':
        color = 'background-color: #FFA500'  # orange
    elif val == 'Low':
        color = 'background-color: #90EE90'  # light green
    return color

# Assume cleaning_task_df with 'priority' column
st.subheader("Cleaning Tasks Schedule")

cleaning_task_df = pd.DataFrame([
    {'time': '2025-05-30 09:00', 'task': 'Clean indoor lobby', 'priority': 'High'},
    {'time': '2025-05-30 10:00', 'task': 'Clean road entrance', 'priority': 'Medium'},
    {'time': '2025-05-30 11:00', 'task': 'Clean parking area', 'priority': 'Low'},
])

styled_df = cleaning_task_df.style.applymap(color_priority, subset=['priority'])
st.dataframe(styled_df)    

