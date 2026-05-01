from datetime import datetime


def adjust_threshold(dt):
    """Static threshold based on time-of-day and weekday. Used as fallback."""
    hour = dt.hour
    weekday = dt.weekday()  # Monday=0, Sunday=6

    # Peak hours: Morning 8-10 AM, Evening 5-7 PM
    if 8 <= hour <= 10 or 17 <= hour <= 19:
        base_threshold = 15
    else:
        base_threshold = 25

    # Weekends are busier outdoors
    if weekday >= 5:
        base_threshold += 5

    return base_threshold


# UPDATED — Dynamic thresholds using historical data mean
def schedule_cleaning(forecast_df, location_type, data_mean=None):
    """
    Schedule cleaning tasks based on forecast values.

    If data_mean is provided, uses dynamic thresholds:
        High:   value > mean * 1.3
        Medium: mean * 0.7 to mean * 1.3
        Low:    value < mean * 0.7

    Falls back to static time-based thresholds if data_mean is None.
    """
    tasks = []
    for _, row in forecast_df.iterrows():
        value = row['yhat']

        if data_mean is not None and data_mean > 0:
            # NEW — Dynamic threshold based on historical average
            if value > data_mean * 1.3:
                priority = 'High'
            elif value >= data_mean * 0.7:
                priority = 'Medium'
            else:
                priority = 'Low'
        else:
            # Fallback to static time-based thresholds
            threshold = adjust_threshold(row['ds'])
            if value >= threshold:
                priority = 'High'
            elif value >= threshold * 0.7:
                priority = 'Medium'
            else:
                priority = 'Low'

        tasks.append({
            'time': row['ds'],
            'task': f"Clean {location_type} area",
            'priority': priority
        })
    return tasks
