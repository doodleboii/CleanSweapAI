from datetime import datetime


def adjust_threshold(dt):
    hour = dt.hour
    weekday = dt.weekday()  # Monday=0, Sunday=6

    # Peak hours: Morning 8-10 AM, Evening 5-7 PM
    if 8 <= hour <= 10 or 17 <= hour <= 19:
        base_threshold = 15
    else:
        base_threshold = 25

    # Weekends (Saturday=5, Sunday=6) are busier outdoors
    if weekday >= 5:
        base_threshold += 5

    return base_threshold

def schedule_cleaning(forecast_df, location_type):
    tasks = []
    for _, row in forecast_df.iterrows():
        threshold = adjust_threshold(row['ds'])
        if row['yhat'] >= threshold:
            priority = 'High'
        elif row['yhat'] >= threshold * 0.7:
            priority = 'Medium'
        else:
            priority = 'Low'

        tasks.append({
            'time': row['ds'],
            'task': f"Clean {location_type} area",
            'priority': priority
        })
    return tasks

