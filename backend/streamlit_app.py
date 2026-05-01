# streamlit_app.py

import streamlit as st
import pandas as pd
import requests
from db import SessionLocal, Forecast, CleaningTask
from datetime import datetime
import altair as alt
from streamlit_echarts import st_echarts

# Page Setup
st.set_page_config(page_title="CleanSweep AI — Decision System", layout="wide")
page = st.sidebar.selectbox("Select Page", ["Dashboard", "Model Evaluation", "History", "Task Report"])

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 15px 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: transform 0.2s ease-in-out, box-shadow 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.2);
    }
    </style>
""", unsafe_allow_html=True)


# NEW — Cached data loading
@st.cache_data(ttl=300)
def load_data():
    try:
        session = SessionLocal()
        indoor_forecast = session.query(Forecast).filter(Forecast.location_type == 'indoor').order_by(Forecast.id.desc()).limit(24).all()
        road_forecast = session.query(Forecast).filter(Forecast.location_type == 'road').order_by(Forecast.id.desc()).limit(24).all()
        indoor_tasks = session.query(CleaningTask).filter(CleaningTask.location_type == 'indoor').order_by(CleaningTask.id.desc()).limit(10).all()
        road_tasks = session.query(CleaningTask).filter(CleaningTask.location_type == 'road').order_by(CleaningTask.id.desc()).limit(10).all()

        indoor_forecast.reverse()
        road_forecast.reverse()
        indoor_tasks.reverse()
        road_tasks.reverse()
        session.close()

        indoor_df = pd.DataFrame([{
            'ds': pd.to_datetime(row.timestamp),
            'yhat': float(row.predicted_value),
            'lower': float(row.lower) if row.lower else None,
            'upper': float(row.upper) if row.upper else None
        } for row in indoor_forecast])

        road_df = pd.DataFrame([{
            'ds': pd.to_datetime(row.timestamp),
            'yhat': float(row.predicted_value),
            'lower': float(row.lower) if row.lower else None,
            'upper': float(row.upper) if row.upper else None
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


# NEW — Cached evaluation
@st.cache_data(ttl=300)
def cached_evaluate_all():
    try:
        response = requests.get("http://127.0.0.1:5000/evaluate-all", timeout=120)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


def priority_color(priority):
    return {"High": "#FF4C4C", "Medium": "#FFA500", "Low": "#90EE90"}.get(priority, "white")

def style_priority(df):
    return df.style.applymap(lambda v: f"background-color: {priority_color(v)}", subset=['priority'])


# NEW — Render forecast chart with confidence bands
def render_forecast_chart(df, color, title):
    if df.empty:
        st.info(f"No {title} data.")
        return

    has_ci = 'lower' in df.columns and 'upper' in df.columns and df['lower'].notna().any()

    line = alt.Chart(df).mark_line(color=color, strokeWidth=2.5).encode(
        x=alt.X('ds:T', title='Time'),
        y=alt.Y('yhat:Q', title='Predicted Value'),
        tooltip=['ds:T', 'yhat:Q']
    )

    if has_ci:
        band = alt.Chart(df).mark_area(opacity=0.15, color=color).encode(
            x='ds:T',
            y='lower:Q',
            y2='upper:Q'
        )
        chart = (band + line).interactive()
    else:
        chart = line.interactive()

    st.altair_chart(chart, use_container_width=True)


# ================= Dashboard Page ====================
if page == "Dashboard":
    st.title("🧹 CleanSweep AI — Predictive Cleaning Decision System")

    mode = st.selectbox("Select Data Mode", ["normal", "peak", "low", "random", "trend"])

    if st.button("🔄 Refresh Predictions"):
        with st.spinner(f"Updating predictions for mode: {mode}..."):
            try:
                response = requests.get(f"http://127.0.0.1:5000/predict-cleaning?mode={mode}", timeout=120)
                if response.status_code == 200:
                    data = response.json()
                    st.success("✅ Predictions updated successfully!")
                    if "metrics" in data:
                        for key in ["indoor_mae", "road_mae", "indoor_mape", "road_mape"]:
                            st.session_state[key] = data["metrics"].get(key, 0)
                        st.session_state["best_order_indoor"] = data["metrics"].get("best_order_indoor", [])
                        st.session_state["best_order_road"] = data["metrics"].get("best_order_road", [])
                        st.session_state["indoor_mean"] = data["metrics"].get("indoor_mean", 0)
                        st.session_state["road_mean"] = data["metrics"].get("road_mean", 0)
                    load_data.clear()
                    st.rerun()
                else:
                    st.error("❌ Failed to update. Check if Flask server is running.")
            except Exception as e:
                st.error(f"Error connecting to prediction API: {e}")

    indoor_df, road_df, indoor_task_df, road_task_df = load_data()

    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Indoor Next Task", indoor_task_df['task'].iloc[0] if not indoor_task_df.empty else "No task",
                indoor_task_df['priority'].iloc[0] if not indoor_task_df.empty else "")
    col2.metric("Road Next Task", road_task_df['task'].iloc[0] if not road_task_df.empty else "No task",
                road_task_df['priority'].iloc[0] if not road_task_df.empty else "")
    col3.metric("Indoor Peak Footfall", int(indoor_df['yhat'].max()) if not indoor_df.empty else 0)
    col4.metric("Road Peak Traffic", int(road_df['yhat'].max()) if not road_df.empty else 0)

    # Model Metrics
    if "indoor_mae" in st.session_state:
        st.markdown("### 📊 Model Evaluation Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Indoor MAE", f"{st.session_state['indoor_mae']:.2f}")
        m2.metric("Road MAE", f"{st.session_state['road_mae']:.2f}")
        if "indoor_mape" in st.session_state:
            m3.metric("Indoor Error (%)", f"{st.session_state['indoor_mape']:.2f}%")
            m4.metric("Road Error (%)", f"{st.session_state['road_mape']:.2f}%")

        # NEW — Show ARIMA orders
        if "best_order_indoor" in st.session_state:
            o1, o2 = st.columns(2)
            o1.info(f"🔧 Indoor ARIMA Order: {st.session_state['best_order_indoor']}")
            o2.info(f"🔧 Road ARIMA Order: {st.session_state['best_order_road']}")

    st.markdown("---")

    # Charts with confidence bands
    st.subheader("📈 Forecast with Confidence Intervals")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Indoor Traffic Forecast")
        render_forecast_chart(indoor_df, '#2ecc71', 'indoor')
    with c2:
        st.markdown("### Road Traffic Forecast")
        render_forecast_chart(road_df, '#e67e22', 'road')

    st.markdown("---")

    # NEW — Decision Engine Visual
    st.subheader("🧠 Decision Engine Logic")
    st.markdown("""
    The CleanSweep AI decision engine uses **dynamic thresholds** based on historical traffic data:

    | Condition | Priority | Action |
    |---|---|---|
    | Predicted traffic > **Mean × 1.3** | 🔴 **High** | Immediate cleaning required |
    | Predicted traffic **Mean × 0.7 – 1.3** | 🟡 **Medium** | Schedule within window |
    | Predicted traffic < **Mean × 0.7** | 🟢 **Low** | Defer or skip |

    > *Thresholds adapt per scenario mode — peak hours trigger more aggressive scheduling.*
    """)

    if "indoor_mean" in st.session_state:
        dm1, dm2 = st.columns(2)
        dm1.metric("Indoor Baseline (Mean)", f"{st.session_state['indoor_mean']:.1f}")
        dm2.metric("Road Baseline (Mean)", f"{st.session_state['road_mean']:.1f}")

    st.markdown("---")

    # NEW — Impact Metrics
    st.subheader("💡 Estimated Impact Metrics")
    total_tasks = len(indoor_task_df) + len(road_task_df)
    if total_tasks > 0:
        high_tasks = len(indoor_task_df[indoor_task_df['priority'] == 'High']) + len(road_task_df[road_task_df['priority'] == 'High']) if not indoor_task_df.empty and not road_task_df.empty else 0
        low_tasks = len(indoor_task_df[indoor_task_df['priority'] == 'Low']) + len(road_task_df[road_task_df['priority'] == 'Low']) if not indoor_task_df.empty and not road_task_df.empty else 0

        efficiency_gain = round((1 - high_tasks / max(total_tasks, 1)) * 100, 1)
        reduction = round(low_tasks / max(total_tasks, 1) * 100, 1)
        optimization = round(100 - (high_tasks / max(total_tasks, 1)) * 50 - (low_tasks / max(total_tasks, 1)) * 10, 1)

        i1, i2, i3 = st.columns(3)
        i1.metric("🚀 Cleaning Efficiency", f"{efficiency_gain}%", "AI-optimized scheduling")
        i2.metric("📉 Unnecessary Cleanings Avoided", f"{reduction}%", "Low-priority deferrals")
        i3.metric("⚙️ Resource Optimization", f"{optimization}%", "Balanced workload distribution")
    else:
        st.info("Run predictions first to see impact metrics.")

    st.markdown("---")

    # Task Display
    st.subheader("🧼 Scheduled Cleaning Tasks")
    priority_filter = st.selectbox("Filter by Priority", ["All", "High", "Medium", "Low"])
    filtered_indoor = indoor_task_df if priority_filter == "All" else indoor_task_df[indoor_task_df['priority'] == priority_filter]
    filtered_road = road_task_df if priority_filter == "All" else road_task_df[road_task_df['priority'] == priority_filter]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Indoor Cleaning Tasks")
        if not filtered_indoor.empty:
            st.dataframe(style_priority(filtered_indoor.sort_values('time')))
        else:
            st.info("No tasks")
    with col2:
        st.markdown("### Road Cleaning Tasks")
        if not filtered_road.empty:
            st.dataframe(style_priority(filtered_road.sort_values('time')))
        else:
            st.info("No tasks")


# ================= Model Evaluation Page ====================
elif page == "Model Evaluation":
    st.title("🔬 Model Evaluation — Multi-Scenario Analysis")
    st.markdown("Compare ARIMA performance across traffic scenarios with auto-generated insights.")

    if st.button("🚀 Run Comprehensive Evaluation"):
        with st.spinner("Running evaluation across all modes (dynamic ARIMA)..."):
            cached_evaluate_all.clear()
            data = cached_evaluate_all()
            if data:
                st.session_state["eval_results"] = data.get("results", [])
                st.session_state["eval_insights"] = data.get("insights", {})

    if "eval_results" in st.session_state and st.session_state["eval_results"]:
        results = st.session_state["eval_results"]
        insights = st.session_state.get("eval_insights", {})
        results_df = pd.DataFrame(results)

        # Auto insights
        if insights:
            st.subheader("🧠 System Insights")
            st.success(f"✅ **Best indoor performance:** `{insights.get('best_indoor_mode', 'N/A')}` mode (MAE: {insights.get('best_indoor_mae', 'N/A')})")
            st.warning(f"⚠️ **Worst indoor performance:** `{insights.get('worst_indoor_mode', 'N/A')}` mode (MAE: {insights.get('worst_indoor_mae', 'N/A')})")
            if "system_insight" in insights:
                st.info(f"💡 {insights['system_insight']}")

        st.subheader("📊 Scenario Comparison Table")
        st.dataframe(results_df, use_container_width=True)

        # ARIMA orders per scenario
        st.subheader("🔧 ARIMA Orders Selected")
        order_data = []
        for r in results:
            order_data.append({
                "Mode": r['mode'],
                "Indoor Order": str(r.get('indoor_order', 'N/A')),
                "Road Order": str(r.get('road_order', 'N/A'))
            })
        st.dataframe(pd.DataFrame(order_data), use_container_width=True)

        # MAE Chart
        st.subheader("📈 MAE Comparison")
        df_mae = results_df.melt(id_vars='mode', value_vars=['indoor_mae', 'road_mae'], var_name='Metric', value_name='MAE')
        chart_mae = alt.Chart(df_mae).mark_bar().encode(
            x=alt.X('mode:N', title='Scenario'),
            y=alt.Y('MAE:Q', title='Mean Absolute Error'),
            color='Metric:N',
            xOffset='Metric:N'
        ).properties(height=400)
        st.altair_chart(chart_mae, use_container_width=True)

        # MAPE Chart
        st.subheader("📉 MAPE Comparison")
        df_mape = results_df.melt(id_vars='mode', value_vars=['indoor_mape', 'road_mape'], var_name='Metric', value_name='MAPE')
        chart_mape = alt.Chart(df_mape).mark_bar().encode(
            x=alt.X('mode:N', title='Scenario'),
            y=alt.Y('MAPE:Q', title='Mean Absolute % Error'),
            color='Metric:N',
            xOffset='Metric:N'
        ).properties(height=400)
        st.altair_chart(chart_mape, use_container_width=True)


# ================= History Page ====================
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
            st_echarts({"series": [{"type": "gauge", "data": [{"value": avg_indoor, "name": "Indoor"}], "max": 100}]}, height="200px")
        with col2:
            st.markdown("**🚗 Avg Road Traffic**")
            st_echarts({"series": [{"type": "gauge", "data": [{"value": avg_road, "name": "Road"}], "max": 120}]}, height="200px")
        with col3:
            st.markdown("**🧹 Tasks in Range**")
            st_echarts({"series": [{"type": "pie", "radius": ["40%", "70%"], "data": [
                {"value": total_indoor_tasks, "name": "Indoor"},
                {"value": total_road_tasks, "name": "Road"}
            ]}]}, height="220px")

        st.subheader("📈 Historical Forecast Trends")
        st.markdown("### 🧍 Indoor")
        render_forecast_chart(filtered_indoor, 'green', 'indoor')
        st.markdown("### 🛣️ Road")
        render_forecast_chart(filtered_road, 'orange', 'road')

        st.subheader("📋 Task Logs")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Indoor Tasks")
            if not indoor_task_df_filtered.empty:
                st.dataframe(style_priority(indoor_task_df_filtered))
            else:
                st.info("No indoor tasks in range.")
        with col2:
            st.markdown("#### Road Tasks")
            if not road_task_df_filtered.empty:
                st.dataframe(style_priority(road_task_df_filtered))
            else:
                st.info("No road tasks in range.")
    else:
        st.warning("📅 Please select valid start and end dates.")


# ================= Task Report Page ====================
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

        st.markdown("### ⬇️ Export")
        csv = all_tasks.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Download Tasks CSV", data=csv, file_name="cleaning_tasks_report.csv", mime='text/csv')

    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: grey;'>"
        "🧹 Powered by <b>CleanSweep AI</b> | AI-Powered Facility Management Decision System</div>",
        unsafe_allow_html=True
    )