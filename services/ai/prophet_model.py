"""
Prophet model wrapper for currency exchange-rate forecasting.

This module provides a two-tier forecasting strategy:

1. **Prophet AI** (primary): Used when ≥30 data points are available.
   The Facebook Prophet library captures trend and changepoints in daily
   exchange-rate time series.  Output is post-processed with rolling-mean
   smoothing, hard-anchored to the live spot rate on Day 1, and validated
   against realistic movement constraints (±3% per day, ≤15% overall).

2. **Linear Regression** (fallback): Used when <30 data points exist or
   when the Prophet forecast is rejected for excessive deviation.  Uses
   scikit-learn's OLS to extrapolate the trend from ordinal dates.

Both strategies share the same output contract:
    - Day 1 is always hard-anchored to the current live spot rate.
    - Daily movement is clamped to ±3%.
    - Confidence bands (lower / upper) are constrained to ±3% of expected
      and guaranteed to have non-zero width.
"""

import logging
from datetime import timedelta
import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.linear_model import LinearRegression

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Primary Forecast — Prophet AI
# ---------------------------------------------------------------------------

def generate_forecast(df: pd.DataFrame, days: int, spot_rate: float = None) -> tuple[list[dict], str]:
    """
    Generate a currency forecast using Facebook Prophet, with automatic
    fallback to linear regression when data is insufficient or the model
    produces unstable results.

    Processing pipeline:
        1. Determine the anchor price (live spot rate preferred over last DB entry).
        2. If fewer than 30 data points, delegate immediately to linear regression.
        3. Remove statistical outliers via the IQR method (keeping the most
           recent 3 days exempt so current market moves aren't discarded).
        4. Fit a Prophet model with conservative changepoint sensitivity
           (``changepoint_prior_scale=0.02``) and additive seasonality.
        5. Generate a future DataFrame and predict.
        6. Smooth raw Prophet output with a 3-day rolling mean to reduce noise.
        7. Validate Day 1 deviation (must be ≤3% of spot rate; reject otherwise).
        8. Hard-anchor Day 1 to the exact spot rate.
        9. Clamp each subsequent day to ±3% of the previous day.
        10. Reject the entire forecast if any day deviates >15% from spot rate.
        11. Shift Prophet's yhat_lower / yhat_upper bands to follow the
            anchored expected value, then constrain to ±3% with guaranteed
            minimum width.

    Args:
        df:        DataFrame with 'ds' (datetime) and 'y' (float rate) columns,
                   pre-cleaned and resampled to daily frequency.
        days:      Number of future days to forecast.
        spot_rate: Current live market spot rate used as the anchor price.
                   Falls back to the most recent 'y' value if unavailable.

    Returns:
        Tuple of (predictions, model_name) where:
            - predictions: list of dicts with keys {date, expected, lower, upper}
            - model_name:  "prophet_ai", "linear_regression", or
                           "linear_regression_fallback" (Prophet failed at runtime)
    """
    if df.empty:
        return [], "none"
        
    df = df.sort_values(by='ds')
    
    # 1. CURRENT PRICE FIX: Use spot_rate if available, else latest DB entry
    last_date = df['ds'].max()
    current_price = float(spot_rate) if spot_rate and spot_rate > 0 else float(df['y'].iloc[-1])
    logger.info(f"[Validation] Prediction Spot Rate for {df['ds'].iloc[0] if not df.empty else 'Unknown'}: {current_price}")
    logger.info(f"Current price (spot rate) for forecasting: {current_price}")
    
    # Prophet requires a minimum of ~30 data points to fit meaningful
    # changepoints; below that threshold, linear regression is more stable.
    if len(df) < 30:
        logger.info("Less than 30 days of data. Using Linear Regression fallback.")
        return _linear_regression_forecast(df, days, current_price), "linear_regression"

    # 2. OUTLIER FILTERING: Remove abnormal rows using IQR
    # The Interquartile Range (IQR) method flags any rate outside
    # [Q1 − 1.5·IQR, Q3 + 1.5·IQR] as an outlier.
    Q1 = df['y'].quantile(0.25)
    Q3 = df['y'].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    # Ensure we don't filter out recent actual valid spikes if they are the new normal,
    # but strictly filter historical anomalies.
    # Records within the last 3 days are always kept regardless of IQR bounds.
    is_recent = df['ds'] >= (last_date - pd.Timedelta(days=3))
    in_bounds = (df['y'] >= lower_bound) & (df['y'] <= upper_bound)
    filtered_df = df[in_bounds | is_recent].copy()

    try:
        # 4. PROPHET CONFIG UPDATE
        # - changepoint_prior_scale=0.02: low flexibility prevents overfitting
        #   to short-term noise while still capturing genuine trend shifts.
        # - additive seasonality: appropriate for exchange rates where seasonal
        #   effects are roughly constant in absolute terms.
        # - daily_seasonality=False: exchange rates don't exhibit meaningful
        #   intra-day seasonal patterns at a daily granularity.
        # - interval_width=0.95: 95% prediction intervals for confidence bands.
        model = Prophet(
            changepoint_prior_scale=0.02,
            seasonality_mode='additive',
            daily_seasonality=False,
            interval_width=0.95
        )
        model.fit(filtered_df)
        
        # Generate future date index and run prediction
        future = model.make_future_dataframe(periods=days, freq='D')
        forecast = model.predict(future)
        
        # Extract only the future predictions (beyond the last historical date)
        pred_df = forecast[forecast['ds'] > last_date].copy()
        
        # 6. FORECAST SMOOTHING: Rolling mean smoothing after Prophet output
        # A 3-day rolling average reduces day-to-day noise in Prophet's
        # raw output while preserving the overall trend direction.
        pred_df['yhat_original'] = pred_df['yhat']
        pred_df['yhat'] = pred_df['yhat'].rolling(window=3, min_periods=1).mean()
        
        predictions = []
        last_day_price = current_price
        rejected_forecasts = 0
        
        for idx, row in pred_df.iterrows():
            expected = row['yhat']
            
            # 7. VALIDATE FORECAST START & 1. HARD ANCHOR THE FORECAST
            # The very first predicted day must be within 3% of the live spot
            # rate.  A larger gap indicates the model is disconnected from
            # the real market, so we reject and fall back to linear regression.
            if idx == pred_df.index[0]:
                first_predicted = expected
                first_dev = abs(first_predicted - current_price) / current_price
                
                logger.info(f"Live current price: {current_price}, First predicted value: {first_predicted:.4f}, Deviation: {first_dev*100:.2f}%")
                
                if first_dev > 0.03: # Reject if first prediction differs by >3%
                    logger.warning(f"Rejecting forecast: Day 1 prediction deviates by {first_dev*100:.2f}% ( > 3% )")
                    raise ValueError(f"Day 1 deviation too high ({first_dev*100:.2f}%)")
                    
                # Hard anchor Day 1 to exact current live market price
                expected = current_price
            
            # 3. STABLE FORECAST CONSTRAINTS: Maximum daily movement = ±3%
            # Prevents unrealistic jumps that would alarm users and produce
            # misleading recommendations.
            max_drop = last_day_price * 0.97
            max_spike = last_day_price * 1.03
            
            if expected < max_drop:
                expected = max_drop
            elif expected > max_spike:
                expected = max_spike
                
            pct_deviation = abs(expected - current_price) / current_price
            logger.info(f"Date: {row['ds'].date()}, Expected: {expected:.4f}, Pct Deviation: {pct_deviation*100:.2f}%")
            
            # 5. FORECAST VALIDATION LAYER
            # If any single day drifts more than 15% from today's spot rate,
            # the model is considered unreliable and we abort to fallback.
            if pct_deviation > 0.15: # 15% overall max deviation from current price
                logger.warning(f"Rejected forecast: deviation {pct_deviation*100:.2f}% exceeds realistic thresholds.")
                rejected_forecasts += 1
                raise ValueError(f"Unstable prediction detected (deviation {pct_deviation*100:.2f}%)")
                
            # 2. APPLY CONSTRAINTS TO ALL BOUNDS
            # Shift Prophet's raw confidence bounds by the same delta used to
            # anchor/constrain the expected value.  This keeps the bands
            # centred on the adjusted prediction rather than the raw yhat.
            shift = expected - row['yhat_original']
            lower = row['yhat_lower'] + shift
            upper = row['yhat_upper'] + shift
            
            # Prevent lower/upper bound collapses and enforce reasonable boundaries
            lower = max(lower, expected * 0.97)  # Don't let lower bound drop >3% from expected
            lower = min(lower, expected * 0.999) # Ensure lower is always below expected
            
            upper = min(upper, expected * 1.03)
            upper = max(upper, expected * 1.001)
            
            predictions.append({
                "date": row['ds'].strftime("%Y-%m-%d"),
                "expected": round(expected, 4),
                "lower": round(lower, 4),
                "upper": round(upper, 4)
            })
            
            last_day_price = expected
            
        return predictions, "prophet_ai"
        
    except Exception as e:
        logger.error(f"Prophet forecast failed or rejected: {e}")
        # Fallback to moving average / linear regression if unstable
        return _linear_regression_forecast(df, days, current_price), "linear_regression_fallback"


# ---------------------------------------------------------------------------
# Fallback Forecast — Scikit-learn Linear Regression
# ---------------------------------------------------------------------------

def _linear_regression_forecast(df: pd.DataFrame, days: int, current_price: float) -> list[dict]:
    """
    Simple linear-regression forecast used as a fallback when Prophet is
    unavailable or produces unstable results.

    The model fits an OLS regression on ordinal date values (integer
    representation of dates) against historical rates, then extrapolates
    forward.  Confidence bands are derived from the training-set RMSE
    (±1.96 × std_err for ~95% coverage).

    The same stability constraints applied to the Prophet forecast are
    enforced here:
        - Day 1 is hard-anchored to the live spot rate.
        - Daily movement is clamped to ±3%.
        - Confidence bands are constrained to ±3% with guaranteed width.

    Args:
        df:            DataFrame with 'ds' (datetime) and 'y' (float) columns.
        days:          Number of future days to forecast.
        current_price: Live spot rate to anchor Day 1.

    Returns:
        List of prediction dicts with keys {date, expected, lower, upper}.
    """
    df = df.copy()
    # Convert datetime to ordinal integers for linear regression feature space
    df['ds_ord'] = df['ds'].map(pd.Timestamp.toordinal)
    
    X = df[['ds_ord']].values
    y = df['y'].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    # Compute training-set RMSE to estimate prediction uncertainty
    y_pred_train = model.predict(X)
    mse = np.mean((y - y_pred_train) ** 2)
    std_err = np.sqrt(mse)
    
    last_date = df['ds'].max()
    predictions = []
    
    last_day_price = current_price
    
    for i in range(1, days + 1):
        target_date = last_date + timedelta(days=i)
        target_ord = target_date.toordinal()
        
        pred_y = model.predict([[target_ord]])[0]
        
        # 1. HARD ANCHOR (Fallback)
        # Force Day 1 to the live spot rate regardless of regression output,
        # ensuring the forecast starts at today's actual market price.
        if i == 1:
            first_dev = abs(pred_y - current_price) / current_price
            logger.info(f"[Fallback] Live price: {current_price}, First predicted: {pred_y:.4f}, Dev: {first_dev*100:.2f}%")
            pred_y = current_price
            
        # Apply stable constraints to fallback as well (±3% daily cap)
        max_drop = last_day_price * 0.97
        max_spike = last_day_price * 1.03
        if pred_y < max_drop:
            pred_y = max_drop
        elif pred_y > max_spike:
            pred_y = max_spike
        
        # 95% confidence margin from training RMSE; fallback to 5% of price
        margin = 1.96 * std_err if std_err > 0 else (pred_y * 0.05)
        lower = pred_y - margin
        upper = pred_y + margin
        
        # Prevent lower/upper bound collapses in fallback
        lower = max(lower, pred_y * 0.97)
        lower = min(lower, pred_y * 0.999)
        upper = min(upper, pred_y * 1.03)
        upper = max(upper, pred_y * 1.001)
        
        predictions.append({
            "date": target_date.strftime("%Y-%m-%d"),
            "expected": round(pred_y, 4),
            "lower": round(lower, 4),
            "upper": round(upper, 4)
        })
        
        last_day_price = pred_y
        
    return predictions
