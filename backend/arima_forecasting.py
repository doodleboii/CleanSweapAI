import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_absolute_error
import warnings

# Suppress warnings from statsmodels for clean output
warnings.filterwarnings("ignore")

def generate_mock_data(scenario='normal', hours=720):
    """
    Generates hourly mock time-series data for indoor footfall and road traffic.
    Simulates IoT sensor data for CleanSweep AI.
    
    Parameters:
        scenario (str): 'normal', 'peak', 'low', 'random', or 'trend'
        hours (int): Total number of hours to simulate (720 hours = 30 days)
        
    Returns:
        pd.DataFrame: DataFrame containing timestamp, indoor_footfall, and road_traffic
    """
    # Ensure randomness on every run
    np.random.seed(None)
    
    # Generate hourly timestamps
    timestamps = pd.date_range(start='2024-01-01', periods=hours, freq='h')
    
    # Create a base diurnal pattern (24-hour cycle mimicking human activity)
    # Peak activity around 14:00 (2 PM)
    time_of_day = np.arange(hours) % 24
    diurnal_pattern = np.sin((time_of_day - 8) * (np.pi / 12)) 
    diurnal_pattern = np.where(diurnal_pattern < 0, 0, diurnal_pattern) # No negative activity
    
    if scenario == 'normal':
        # Standard daily pattern with some gaussian noise
        footfall = 100 * diurnal_pattern + np.random.normal(10, 5, hours)
        traffic = 500 * diurnal_pattern + np.random.normal(50, 20, hours)
        
    elif scenario == 'peak':
        # Normal pattern but with sudden huge spikes (e.g., special events, sales)
        footfall = 100 * diurnal_pattern + np.random.normal(10, 5, hours)
        traffic = 500 * diurnal_pattern + np.random.normal(50, 20, hours)
        # Add 5 random extreme peaks
        peak_indices = np.random.choice(hours, size=5, replace=False)
        footfall[peak_indices] += 400
        traffic[peak_indices] += 2000
        
    elif scenario == 'low':
        # Reduced traffic (e.g., lockdown, heavy rain, or closed sections)
        footfall = 20 * diurnal_pattern + np.random.normal(5, 2, hours)
        traffic = 100 * diurnal_pattern + np.random.normal(20, 10, hours)
        
    elif scenario == 'random':
        # Pure noise / broken sensor simulation
        footfall = np.random.uniform(0, 200, hours)
        traffic = np.random.uniform(0, 1000, hours)
        
    elif scenario == 'trend':
        # Daily pattern superimposed on a linearly increasing trend
        trend = np.linspace(0, 150, hours)
        footfall = 100 * diurnal_pattern + trend + np.random.normal(10, 5, hours)
        traffic = 500 * diurnal_pattern + (trend * 4) + np.random.normal(50, 20, hours)
        
    else:
        raise ValueError(f"Unknown scenario: {scenario}")
        
    # Clip values to ensure no negative footfall/traffic
    footfall = np.maximum(footfall, 0)
    traffic = np.maximum(traffic, 0)
    
    # Construct DataFrame
    df = pd.DataFrame({
        'timestamp': timestamps,
        'indoor_footfall': footfall.astype(int),
        'road_traffic': traffic.astype(int)
    })
    df.set_index('timestamp', inplace=True)
    return df

def train_and_evaluate_arima(df, target_column='indoor_footfall', forecast_horizon=24):
    """
    Trains an ARIMA model on historical data and forecasts the next `forecast_horizon` hours.
    Evaluates the model against the actual held-out test data.
    
    Parameters:
        df (pd.DataFrame): Time-series dataframe
        target_column (str): Column to forecast
        forecast_horizon (int): Number of hours to forecast and test against
        
    Returns:
        tuple: (MAE score, actual test values array, predicted values array)
    """
    # Split data into train (all but last 24 hours) and test (last 24 hours)
    train = df[target_column].iloc[:-forecast_horizon]
    test = df[target_column].iloc[-forecast_horizon:]
    
    # Define ARIMA model
    # Note: For robust daily seasonality, seasonal_order=(P,D,Q,24) would be ideal (SARIMA).
    # We use a standard ARIMA(2,1,2) here to ensure fast convergence for the demonstration.
    model = ARIMA(train, order=(2, 1, 2))
    
    try:
        fitted_model = model.fit()
        # Forecast the next 'forecast_horizon' hours
        forecast = fitted_model.forecast(steps=forecast_horizon)
        predictions = forecast.values
    except Exception as e:
        print(f"Model fitting failed: {e}. Falling back to naive forecast.")
        # Naive fallback if the model fails to converge
        predictions = np.full(forecast_horizon, train.iloc[-1])
        
    # Calculate Mean Absolute Error (MAE)
    mae = mean_absolute_error(test, predictions)
    
    return mae, test.values, predictions

def plot_scenario_results(scenario, test_actuals, predictions):
    """
    Plots the Actual vs Predicted values for visual evaluation.
    """
    plt.figure(figsize=(10, 5))
    plt.plot(test_actuals, label='Actual Data', marker='o', linewidth=2)
    plt.plot(predictions, label='ARIMA Forecast', marker='x', linestyle='--', linewidth=2)
    
    plt.title(f'ARIMA Forecast vs Actuals - {scenario.capitalize()} Scenario')
    plt.xlabel('Hours into Forecast Period (Next 24h)')
    plt.ylabel('Indoor Footfall Count')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.show()

def run_experiment():
    """
    Main function to run the evaluation across all data scenarios.
    """
    scenarios = ['normal', 'peak', 'low', 'random', 'trend']
    forecast_horizon = 24
    
    print("="*60)
    print("CleanSweep AI: ARIMA Forecasting Scenario Evaluation")
    print("="*60)
    
    results = []
    plot_data = {}
    
    # 1. Run evaluation for each scenario
    for scenario in scenarios:
        # Generate 30 days of data
        df = generate_mock_data(scenario=scenario, hours=720) 
        
        # Train and evaluate
        mae, actuals, predictions = train_and_evaluate_arima(
            df, 
            target_column='indoor_footfall', 
            forecast_horizon=forecast_horizon
        )
        
        results.append({'Scenario': scenario.capitalize(), 'MAE': mae})
        plot_data[scenario] = (actuals, predictions)
        
    # 2. Output Table of MAE values
    results_df = pd.DataFrame(results)
    
    print("\n--- Performance Comparison (Mean Absolute Error) ---")
    print(results_df.to_string(index=False))
    
    # 3. Clearly identify Best and Worst performing scenarios
    best_scenario = results_df.loc[results_df['MAE'].idxmin()]
    worst_scenario = results_df.loc[results_df['MAE'].idxmax()]
    
    print("\n--- Conclusion ---")
    print(f"Best Performing Scenario:  {best_scenario['Scenario']} (Lowest MAE: {best_scenario['MAE']:.2f})")
    print(f"Worst Performing Scenario: {worst_scenario['Scenario']} (Highest MAE: {worst_scenario['MAE']:.2f})")
    
    print("\nGenerating plots... (Close each window to see the next plot)")
    
    # 4. Plot graphs one by one
    for scenario in scenarios:
        actuals, predictions = plot_data[scenario]
        plot_scenario_results(scenario, actuals, predictions)

if __name__ == "__main__":
    run_experiment()
