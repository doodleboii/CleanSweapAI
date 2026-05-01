from statsmodels.tsa.arima.model import ARIMA
import pandas as pd
from sklearn.metrics import mean_absolute_error
import numpy as np
import warnings
import logging

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")


# NEW — Dynamic ARIMA order selection via AIC grid search
def find_best_arima_order(ts, max_p=2, max_d=1, max_q=2):
    """
    Grid search over ARIMA(p,d,q) to find the order with the lowest AIC.
    Falls back to (1,1,1) if all combinations fail.
    """
    best_aic = float("inf")
    best_order = (1, 1, 1)

    for p in range(max_p + 1):
        for d in range(max_d + 1):
            for q in range(max_q + 1):
                if p == 0 and q == 0:
                    continue  # Skip degenerate model
                try:
                    model = ARIMA(ts, order=(p, d, q))
                    model_fit = model.fit()
                    if model_fit.aic < best_aic:
                        best_aic = model_fit.aic
                        best_order = (p, d, q)
                except Exception:
                    continue

    logger.info(f"Best ARIMA order: {best_order} (AIC: {best_aic:.2f})")
    return best_order


# UPDATED — Now uses dynamic order + returns confidence intervals + best_order
def train_predictor(df, column):
    """
    Train ARIMA with dynamic order selection and produce 24-hour forecast
    with confidence intervals.

    Returns: (forecast_df, best_order)
        forecast_df columns: ds, yhat, lower, upper
    """
    ts = df.set_index('timestamp')[column]

    best_order = find_best_arima_order(ts)

    model = ARIMA(ts, order=best_order)
    model_fit = model.fit()

    forecast = model_fit.get_forecast(steps=24)
    forecast_df = forecast.summary_frame().reset_index()
    forecast_df.rename(columns={
        'index': 'ds',
        'mean': 'yhat',
        'mean_ci_lower': 'lower',
        'mean_ci_upper': 'upper'
    }, inplace=True)

    # Keep only relevant columns
    forecast_df = forecast_df[['ds', 'yhat', 'lower', 'upper']]

    return forecast_df, best_order


# UPDATED — Dynamic order, fixed MAPE, returns best_order
def evaluate_model(df, column):
    """
    Evaluates ARIMA on the dataset using train/test split.
    Returns: (mae, mape, forecast_values, test_values, best_order)
    """
    ts = df.set_index('timestamp')[column]

    # Train-test split (forecast horizon = 24 hours)
    train = ts.iloc[:-24]
    test = ts.iloc[-24:]

    try:
        best_order = find_best_arima_order(train)
        model = ARIMA(train, order=best_order)
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=24)
        mae = mean_absolute_error(test, forecast)
        # UPDATED — Safe MAPE using np.maximum to avoid division by zero
        mape = np.mean(np.abs((test - forecast) / np.maximum(test, 1))) * 100
    except Exception as e:
        logger.warning(f"ARIMA fitting failed: {e}")
        best_order = (1, 1, 1)
        # Naive fallback — use last known value
        forecast = pd.Series([train.iloc[-1]] * 24, index=test.index)
        mae = mean_absolute_error(test, forecast)
        mape = np.mean(np.abs((test - forecast) / np.maximum(test, 1))) * 100

    return mae, mape, forecast.values, test.values, best_order
