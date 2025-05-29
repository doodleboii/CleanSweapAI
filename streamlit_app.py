import streamlit as st
import pandas as pd
import requests
from db import SessionLocal, Forecast, CleaningTask
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
    indoor_task_df = pd.DataFrame([{'time': task.time, 'task': task.task, 'priority': task.priority, 'location': 'Indoor'} for task in indoor_tasks])
    road_task_df = pd.DataFrame([{'time': task.time, 'task': task.task, 'priority': task.priority, 'location': 'Road'} for task in road_tasks])

    return indoor_df, road_df, indoor_task_df, road_task_df

# Color map for priority levels
def priority_color(priority):
    colors = {"High": "#FF4C4C", "Medium": "#FFA500", "Low": "#90EE90"}
    return colors.get(priority, "white")

def style_priority(df):
    return df.style.applymap(lambda v: f"background-color: {priority_color(v)}", subset=['priority'])

if page == "Dashboard":
    st.title("🧹 CleanSweep AI – Predictive Cleaning Dashboard")

    if st.button("🔄 Refresh Predictions"):
        with st.spinner("Updating predictions..."):
            try:
                response = requests.get("http://127.0.0.1:5000/predict-cleaning")
                if response.status_code == 200:
                    st.success("✅ Predictions updated successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to update. Check if Flask server is running.")
            except Exception as e:
                st.error(f"Error connecting to prediction API: {e}")

    indoor_df, road_df, indoor_task_df, road_task_df = load_data()

    # KPI summary cards
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Indoor Next Task",
                indoor_task_df['task'].iloc[0] if not indoor_task_df.empty else "No task",
                indoor_task_df['priority'].iloc[0] if not indoor_task_df.empty else "")

    col2.metric("Road Next Task",
                road_task_df['task'].iloc[0] if not road_task_df.empty else "No task",
                road_task_df['priority'].iloc[0] if not road_task_df.empty else "")

    col3.metric("Indoor Peak Footfall",
                int(indoor_df['yhat'].max()) if not indoor_df.empty else 0)

    col4.metric("Road Peak Traffic",
                int(road_df['yhat'].max()) if not road_df.empty else 0)

    st.markdown("---")

    # Footfall Forecast Charts
    st.subheader("📈 Footfall Forecast")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### Indoor Traffic Forecast")
        if not indoor_df.empty:
            indoor_chart = alt.Chart(indoor_df).mark_line(point=True, color='green').encode(
                x='ds:T',
                y='yhat:Q',
                tooltip=['ds:T', 'yhat:Q']
            ).interactive().properties(height=300)
            st.altair_chart(indoor_chart, use_container_width=True)
        else:
            st.write("No indoor forecast data.")

    with c2:
        st.markdown("### Road Traffic Forecast")
        if not road_df.empty:
            road_chart = alt.Chart(road_df).mark_line(point=True, color='orange').encode(
                x='ds:T',
                y='yhat:Q',
                tooltip=['ds:T', 'yhat:Q']
            ).interactive().properties(height=300)
            st.altair_chart(road_chart, use_container_width=True)
        else:
            st.write("No road forecast data.")

    st.markdown("---")

    # Scheduled Cleaning Tasks with priority filter
    st.subheader("🧼 Scheduled Cleaning Tasks")
    priority_filter = st.selectbox("Filter by Priority", ["All", "High", "Medium", "Low"])

    filtered_indoor = indoor_task_df if priority_filter == "All" else indoor_task_df[indoor_task_df['priority'] == priority_filter]
    filtered_road = road_task_df if priority_filter == "All" else road_task_df[road_task_df['priority'] == priority_filter]

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("### Indoor Cleaning Tasks")
        if not filtered_indoor.empty:
            st.dataframe(style_priority(filtered_indoor.sort_values('time')))
        else:
            st.write("No indoor cleaning tasks matching filter.")

    with col4:
        st.markdown("### Road Cleaning Tasks")
        if not filtered_road.empty:
            st.dataframe(style_priority(filtered_road.sort_values('time')))
        else:
            st.write("No road cleaning tasks matching filter.")

elif page == "History":
    st.title("📜 History of Forecasts and Cleaning Tasks")

    indoor_df, road_df, indoor_task_df, road_task_df = load_data()

    st.sidebar.subheader("Historical Trends Filter")

    min_date = min(indoor_df['ds'].min() if not indoor_df.empty else None, road_df['ds'].min() if not road_df.empty else None)
    max_date = max(indoor_df['ds'].max() if not indoor_df.empty else None, road_df['ds'].max() if not road_df.empty else None)

    if min_date is None or max_date is None:
        st.info("No forecast data available to filter.")
    else:
        start_date = st.sidebar.date_input("Start Date", min_date.date())
        end_date = st.sidebar.date_input("End Date", max_date.date())

        if start_date > end_date:
            st.error("Error: Start date must be before end date.")
        else:
            mask_indoor = (indoor_df['ds'] >= pd.Timestamp(start_date)) & (indoor_df['ds'] <= pd.Timestamp(end_date))
            mask_road = (road_df['ds'] >= pd.Timestamp(start_date)) & (road_df['ds'] <= pd.Timestamp(end_date))

            filtered_indoor = indoor_df[mask_indoor]
            filtered_road = road_df[mask_road]

            st.subheader("📈 Historical Traffic Trends")

            if not filtered_indoor.empty:
                indoor_chart = alt.Chart(filtered_indoor).mark_line(color='green').encode(
                    x='ds:T',
                    y='yhat:Q',
                    tooltip=['ds:T', 'yhat:Q']
                ).interactive().properties(height=300, title="Indoor Footfall Over Time")
                st.altair_chart(indoor_chart, use_container_width=True)
            else:
                st.write("No indoor forecast data in selected range.")

            if not filtered_road.empty:
                road_chart = alt.Chart(filtered_road).mark_line(color='orange').encode(
                    x='ds:T',
                    y='yhat:Q',
                    tooltip=['ds:T', 'yhat:Q']
                ).interactive().properties(height=300, title="Road Traffic Over Time")
                st.altair_chart(road_chart, use_container_width=True)
            else:
                st.write("No road forecast data in selected range.")

            st.subheader("📊 Historical Data Tables")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### Indoor Forecast History")
                st.dataframe(filtered_indoor)

            with col2:
                st.markdown("### Road Forecast History")
                st.dataframe(filtered_road)

            st.subheader("🧹 Cleaning Task History")

            indoor_tasks_filtered = indoor_task_df[(indoor_task_df['time'] >= pd.Timestamp(start_date)) & (indoor_task_df['time'] <= pd.Timestamp(end_date))]
            road_tasks_filtered = road_task_df[(road_task_df['time'] >= pd.Timestamp(start_date)) & (road_task_df['time'] <= pd.Timestamp(end_date))]

            col3, col4 = st.columns(2)

            with col3:
                st.markdown("### Indoor Cleaning Tasks")
                if not indoor_tasks_filtered.empty:
                    st.dataframe(style_priority(indoor_tasks_filtered))
                else:
                    st.write("No indoor cleaning tasks in this date range.")

            with col4:
                st.markdown("### Road Cleaning Tasks")
                if not road_tasks_filtered.empty:
                    st.dataframe(style_priority(road_tasks_filtered))
                else:
                    st.write("No road cleaning tasks in this date range.")

elif page == "Task Report":
    st.title("📊 Downloadable Task Report")
    _, _, indoor_task_df, road_task_df = load_data()

    all_tasks = pd.concat([indoor_task_df, road_task_df], ignore_index=True)
    all_tasks = all_tasks.sort_values(by='time')

    if all_tasks.empty:
        st.info("No cleaning tasks data available.")
    else:
        st.dataframe(style_priority(all_tasks))

        csv = all_tasks.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Task Report as CSV",
            data=csv,
            file_name="cleaning_tasks_report.csv",
            mime='text/csv'
        )
