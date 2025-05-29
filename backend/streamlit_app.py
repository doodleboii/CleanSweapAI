import streamlit as st
import pandas as pd
import requests
from db import SessionLocal, Forecast, CleaningTask
from datetime import datetime
import altair as alt
from streamlit_echarts import st_echarts

st.set_page_config(page_title="CleanSweep AI Dashboard", layout="wide")

# Sidebar menu
page = st.sidebar.selectbox("Select Page", ["Dashboard", "History", "Task Report"])

# Function to load data from DB
@st.cache_data
def load_data():
    try:
        session = SessionLocal()

        indoor_forecast = session.query(Forecast).filter(Forecast.location_type == 'indoor').all()
        road_forecast = session.query(Forecast).filter(Forecast.location_type == 'road').all()
        indoor_tasks = session.query(CleaningTask).filter(CleaningTask.location_type == 'indoor').all()
        road_tasks = session.query(CleaningTask).filter(CleaningTask.location_type == 'road').all()

        session.close()

        # Convert to DataFrames with proper datetime handling
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

    # Sidebar date selector
    st.sidebar.subheader("📅 Historical Trends Filter")
    min_date = min(indoor_df['ds'].min(), road_df['ds'].min()) if not indoor_df.empty and not road_df.empty else datetime.now()
    max_date = max(indoor_df['ds'].max(), road_df['ds'].max()) if not indoor_df.empty and not road_df.empty else datetime.now()
    start_date = st.sidebar.date_input("Start Date", min_date.date() if pd.notnull(min_date) else None)
    end_date = st.sidebar.date_input("End Date", max_date.date() if pd.notnull(max_date) else None)

    if start_date and end_date:
        # Filter forecasts
        mask_indoor = (indoor_df['ds'] >= pd.Timestamp(start_date)) & (indoor_df['ds'] <= pd.Timestamp(end_date))
        mask_road = (road_df['ds'] >= pd.Timestamp(start_date)) & (road_df['ds'] <= pd.Timestamp(end_date))
        filtered_indoor = indoor_df[mask_indoor]
        filtered_road = road_df[mask_road]

        # Filter tasks
        indoor_task_df_filtered = indoor_task_df[
            (indoor_task_df['time'] >= pd.Timestamp(start_date)) &
            (indoor_task_df['time'] <= pd.Timestamp(end_date))
        ]
        road_task_df_filtered = road_task_df[
            (road_task_df['time'] >= pd.Timestamp(start_date)) &
            (road_task_df['time'] <= pd.Timestamp(end_date))
        ]

        #  KPI CIRCLES ----------
        st.subheader("🔘 Summary Overview (Selected Dates)")

        avg_indoor = round(filtered_indoor['yhat'].mean(), 1) if not filtered_indoor.empty else 0
        avg_road = round(filtered_road['yhat'].mean(), 1) if not filtered_road.empty else 0

        total_indoor_tasks = indoor_task_df_filtered.shape[0]
        total_road_tasks = road_task_df_filtered.shape[0]

        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)

        with col_kpi1:
            st.markdown("**📊 Avg Indoor Footfall**")
            st_echarts({
                "animationDuration": 5000,
                "animationEasing": "elasticOut",
                "series": [{
                    "type": 'gauge',
                    "progress": {"show": True},
                    "detail": {
                        "valueAnimation": True,
                        "formatter": f'{avg_indoor}',
                    },
                    "data": [{"value": avg_indoor, "name": "Indoor"}],
                    "max": 100
                }]
            }, height="200px")

        with col_kpi2:
            st.markdown("**🚗 Avg Road Traffic**")
            st_echarts({
                "animationDuration": 5000,
                "animationEasing": "cubicOut",
                "series": [{
                    "type": 'gauge',
                    "progress": {"show": True},
                    "detail": {
                        "valueAnimation": True,
                        "formatter": f'{avg_road}',
                    },
                    "data": [{"value": avg_road, "name": "Road"}],
                    "max": 120
                }]
            }, height="200px")

        with col_kpi3:
            st.markdown("**🧹 Tasks in Range**")
            st_echarts({
                "series": [{
                    "type": "pie",
                    "radius": ["40%", "70%"],
                    "avoidLabelOverlap": False,
                    "label": {"show": False},
                    "emphasis": {"label": {"show": True, "fontSize": "18", "fontWeight": "bold"}},
                    "data": [
                        {"value": total_indoor_tasks, "name": "Indoor"},
                        {"value": total_road_tasks, "name": "Road"}
                    ]
                }]
            }, height="220px")

        # LINE GRAPHS 
        st.subheader("📈 Historical Traffic Trends")

        st.markdown("### 🧍 Indoor Footfall")
        if not filtered_indoor.empty:
            indoor_chart = alt.Chart(filtered_indoor).mark_line(color='green').encode(
                x='ds:T', y='yhat:Q', tooltip=['ds:T', 'yhat:Q']
            ).properties(height=300, title='Indoor Footfall Over Time')
            st.altair_chart(indoor_chart, use_container_width=True)
        else:
            st.write("No indoor traffic data available for selected period.")

        st.markdown("### 🛣️ Road Traffic")
        if not filtered_road.empty:
            road_chart = alt.Chart(filtered_road).mark_line(color='orange').encode(
                x='ds:T', y='yhat:Q', tooltip=['ds:T', 'yhat:Q']
            ).properties(height=300, title='Road Traffic Over Time')
            st.altair_chart(road_chart, use_container_width=True)
        else:
            st.write("No road traffic data available for selected period.")

        # DATA TABLES 
        st.subheader("📊 Historical Forecast Data")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Indoor Forecast History")
            st.dataframe(filtered_indoor)

        with col2:
            st.markdown("#### Road Forecast History")
            st.dataframe(filtered_road)

        # -TASK TABLES 
        st.subheader("🧼 Cleaning Task History")

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("#### Indoor Cleaning Tasks")
            st.dataframe(indoor_task_df_filtered)

        with col4:
            st.markdown("#### Road Cleaning Tasks")
            st.dataframe(road_task_df_filtered)

    else:
        st.info("📅 Please select both start and end dates to view historical data.")

elif page == "Task Report":
    st.title("📊 Task Report & Export")

    # Load data
    _, _, indoor_task_df, road_task_df = load_data()

    # Merge & sort all tasks
    all_tasks = pd.concat([indoor_task_df, road_task_df], ignore_index=True)
    all_tasks = all_tasks.sort_values(by='time')

    # Add some spacing
    st.markdown("### 🧹 All Scheduled Cleaning Tasks")
    st.markdown("Filter, view, and export all cleaning tasks from indoor and road locations.")

    # Show stats at top
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📍 Indoor Tasks", len(indoor_task_df))
    with col2:
        st.metric("🛣️ Road Tasks", len(road_task_df))
    with col3:
        st.metric("🧾 Total Tasks", len(all_tasks))

    st.markdown("---")

    # Display table with colorful priority badges
    if all_tasks.empty:
        st.warning("⚠️ No cleaning task data available.")
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

        # Export button
        st.markdown("### ⬇️ Download")
        st.markdown("Export the full task report below:")
        csv = all_tasks.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Cleaning Tasks as CSV",
            data=csv,
            file_name="cleaning_tasks_report.csv",
            mime='text/csv',
            help="Click to download the task schedule in CSV format."
        )

    # Add a soft footer message
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: grey; font-size: 0.9em;'>"
        "Powered by <b>CleanSweep AI</b> | Automating Facility Cleanliness Predictively 🚀"
        "</div>",
        unsafe_allow_html=True
    )
