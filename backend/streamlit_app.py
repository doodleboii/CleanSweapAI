# streamlit_app.py

import streamlit as st
import pandas as pd
import requests
from db import SessionLocal, Forecast, CleaningTask
from datetime import datetime
import altair as alt
from streamlit_echarts import st_echarts

# Page Setup
st.set_page_config(page_title="CleanSweep AI Dashboard", layout="wide")
page = st.sidebar.selectbox("Select Page", ["Dashboard", "History", "Task Report"])

# Load data from the database
@st.cache_data
def load_data():
    try:
        session = SessionLocal()

        indoor_forecast = session.query(Forecast).filter(Forecast.location_type == 'indoor').all()
        road_forecast = session.query(Forecast).filter(Forecast.location_type == 'road').all()
        indoor_tasks = session.query(CleaningTask).filter(CleaningTask.location_type == 'indoor').all()
        road_tasks = session.query(CleaningTask).filter(CleaningTask.location_type == 'road').all()

        session.close()

        indoor_df = pd.DataFrame([{
            'ds': pd.to_datetime(row.timestamp),
            'yhat': float(row.predicted_value)
        } for row in indoor_forecast])

        road_df = pd.DataFrame([{
            'ds': pd.to_datetime(row.timestamp),
            'yhat': float(row.predicted_value)
        } for row in road_forecast])

        indoor_task_df = pd.DataFrame([{
            'time': pd.to_datetime(task.time),
            'task': task.task,
            'priority': task.priority,
            'location': 'Indoor'
        } for task in indoor_tasks])

        road_task_df = pd.DataFrame([{
            'time': pd.to_datetime(task.time),
            'task': task.task,
            'priority': task.priority,
            'location': 'Road'
        } for task in road_tasks])

        return indoor_df, road_df, indoor_task_df, road_task_df

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Helper for colored priority display
def priority_color(priority):
    return {"High": "#FF4C4C", "Medium": "#FFA500", "Low": "#90EE90"}.get(priority, "white")

def style_priority(df):
    return df.style.map(lambda v: f"background-color: {priority_color(v)}", subset=['priority'])
# ----------------- Dashboard Page --------------------
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

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Indoor Next Task", indoor_task_df['task'].iloc[0] if not indoor_task_df.empty else "No task", indoor_task_df['priority'].iloc[0] if not indoor_task_df.empty else "")
    col2.metric("Road Next Task", road_task_df['task'].iloc[0] if not road_task_df.empty else "No task", road_task_df['priority'].iloc[0] if not road_task_df.empty else "")
    col3.metric("Indoor Peak Footfall", int(indoor_df['yhat'].max()) if not indoor_df.empty else 0)
    col4.metric("Road Peak Traffic", int(road_df['yhat'].max()) if not road_df.empty else 0)

    st.markdown("---")

    # Charts
    st.subheader("📈 Footfall Forecast")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### Indoor Traffic Forecast")
        if not indoor_df.empty:
            chart = alt.Chart(indoor_df).mark_line(point=True, color='green').encode(x='ds:T', y='yhat:Q').interactive()
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No indoor forecast data.")

    with c2:
        st.markdown("### Road Traffic Forecast")
        if not road_df.empty:
            chart = alt.Chart(road_df).mark_line(point=True, color='orange').encode(x='ds:T', y='yhat:Q').interactive()
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No road forecast data.")

    st.markdown("---")

    # Task Display
    st.subheader("🧼 Scheduled Cleaning Tasks")
    priority_filter = st.selectbox("Filter by Priority", ["All", "High", "Medium", "Low"])

    filtered_indoor = indoor_task_df if priority_filter == "All" else indoor_task_df[indoor_task_df['priority'] == priority_filter]
    filtered_road = road_task_df if priority_filter == "All" else road_task_df[road_task_df['priority'] == priority_filter]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Indoor Cleaning Tasks")
        st.dataframe(style_priority(filtered_indoor.sort_values('time')) if not filtered_indoor.empty else "No tasks")

    with col2:
        st.markdown("### Road Cleaning Tasks")
        st.dataframe(style_priority(filtered_road.sort_values('time')) if not filtered_road.empty else "No tasks")

# ----------------- History Page --------------------
elif page == "History":
    st.title("📜 History of Forecasts and Cleaning Tasks")

    indoor_df, road_df, indoor_task_df, road_task_df = load_data()

    st.sidebar.subheader("📅 Filter Historical Data")
    min_date = min(indoor_df['ds'].min(), road_df['ds'].min()) if not indoor_df.empty and not road_df.empty else datetime.now()
    max_date = max(indoor_df['ds'].max(), road_df['ds'].max()) if not indoor_df.empty and not road_df.empty else datetime.now()

    start_date = st.sidebar.date_input("Start Date", min_date.date())
    end_date = st.sidebar.date_input("End Date", max_date.date())

    if start_date and end_date:
        mask_indoor = (indoor_df['ds'] >= pd.Timestamp(start_date)) & (indoor_df['ds'] <= pd.Timestamp(end_date))
        mask_road = (road_df['ds'] >= pd.Timestamp(start_date)) & (road_df['ds'] <= pd.Timestamp(end_date))
        filtered_indoor = indoor_df[mask_indoor]
        filtered_road = road_df[mask_road]

        indoor_task_df_filtered = indoor_task_df[
            (indoor_task_df['time'] >= pd.Timestamp(start_date)) &
            (indoor_task_df['time'] <= pd.Timestamp(end_date))
        ]
        road_task_df_filtered = road_task_df[
            (road_task_df['time'] >= pd.Timestamp(start_date)) &
            (road_task_df['time'] <= pd.Timestamp(end_date))
        ]

        st.subheader("🔘 Summary Overview (Selected Dates)")

        avg_indoor = round(filtered_indoor['yhat'].mean(), 1) if not filtered_indoor.empty else 0
        avg_road = round(filtered_road['yhat'].mean(), 1) if not filtered_road.empty else 0

        total_indoor_tasks = indoor_task_df_filtered.shape[0]
        total_road_tasks = road_task_df_filtered.shape[0]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**📊 Avg Indoor Footfall**")
            st_echarts({
                "series": [{
                    "type": "gauge",
                    "data": [{"value": avg_indoor, "name": "Indoor"}],
                    "max": 100
                }]
            }, height="200px")

        with col2:
            st.markdown("**🚗 Avg Road Traffic**")
            st_echarts({
                "series": [{
                    "type": "gauge",
                    "data": [{"value": avg_road, "name": "Road"}],
                    "max": 120
                }]
            }, height="200px")

        with col3:
            st.markdown("**🧹 Tasks in Range**")
            st_echarts({
                "series": [{
                    "type": "pie",
                    "radius": ["40%", "70%"],
                    "data": [
                        {"value": total_indoor_tasks, "name": "Indoor"},
                        {"value": total_road_tasks, "name": "Road"}
                    ]
                }]
            }, height="220px")

        st.subheader("📈 Historical Forecast Trends")

        st.markdown("### 🧍 Indoor")
        if not filtered_indoor.empty:
            st.altair_chart(
                alt.Chart(filtered_indoor).mark_line(color='green').encode(
                    x='ds:T', y='yhat:Q', tooltip=['ds:T', 'yhat:Q']
                ).properties(height=300),
                use_container_width=True
            )
        else:
            st.info("No indoor traffic data.")

        st.markdown("### 🛣️ Road")
        if not filtered_road.empty:
            st.altair_chart(
                alt.Chart(filtered_road).mark_line(color='orange').encode(
                    x='ds:T', y='yhat:Q', tooltip=['ds:T', 'yhat:Q']
                ).properties(height=300),
                use_container_width=True
            )
        else:
            st.info("No road traffic data.")

        st.subheader("📋 Task Logs")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Indoor Tasks")
            st.dataframe(style_priority(indoor_task_df_filtered))

        with col2:
            st.markdown("#### Road Tasks")
            st.dataframe(style_priority(road_task_df_filtered))

    else:
        st.warning("📅 Please select valid start and end dates.")


# ----------------- Task Report Page --------------------
elif page == "Task Report":
    st.title("📊 Task Report & Export")

    _, _, indoor_task_df, road_task_df = load_data()

    all_tasks = pd.concat([indoor_task_df, road_task_df], ignore_index=True)
    all_tasks = all_tasks.sort_values(by='time')

    st.markdown("### 🧹 All Cleaning Tasks")
    st.markdown("Filter, view, and export all scheduled tasks.")

    col1, col2, col3 = st.columns(3)
    col1.metric("📍 Indoor Tasks", len(indoor_task_df))
    col2.metric("🛣️ Road Tasks", len(road_task_df))
    col3.metric("🧾 Total Tasks", len(all_tasks))

    st.markdown("---")

    if all_tasks.empty:
        st.warning("⚠️ No tasks available.")
    else:
        def color_priority(val):
            if val == 'High':
                return 'background-color: #ffcccc; color: red; font-weight: bold;'
            elif val == 'Medium':
                return 'background-color: #fff2cc; color: orange; font-weight: bold;'
            elif val == 'Low':
                return 'background-color: #ccffcc; color: green; font-weight: bold;'
            return ''

        styled_df = all_tasks.style.applymap(color_priority, subset=['priority'])
        st.dataframe(styled_df, use_container_width=True)

        # Download section
        st.markdown("### ⬇️ Export")
        csv = all_tasks.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Tasks CSV",
            data=csv,
            file_name="cleaning_tasks_report.csv",
            mime='text/csv'
        )

    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: grey;'>"
        "🧹 Powered by <b>CleanSweep AI</b> | Predictive Facility Cleaning</div>",
        unsafe_allow_html=True
    )
