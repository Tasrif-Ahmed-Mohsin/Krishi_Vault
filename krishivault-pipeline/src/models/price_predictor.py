"""
KrishiVault Price Prediction Models
=====================================
SARIMA + LSTM hybrid ensemble for potato price forecasting.

Trained on:
- Historical daily prices (DAM portal data)
- Weather features (temperature, rainfall, humidity)
- Seasonal indicators (month, week, harvest season flags)
- Market volume data

Outputs:
- 7-day, 14-day, 30-day price forecasts with confidence intervals
"""

import sys
import warnings
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import (
    SARIMA_ORDER, SARIMA_SEASONAL_ORDER,
    LSTM_SEQUENCE_LENGTH, LSTM_HIDDEN_SIZE, LSTM_NUM_LAYERS, LSTM_DROPOUT,
    PREDICTION_HORIZONS, POTATO_SEASONAL_PATTERN,
    MODEL_DIR, PROCESSED_DIR
)

warnings.filterwarnings("ignore", category=FutureWarning)


# ============================================================
# FEATURE ENGINEERING
# ============================================================

class FeatureEngineer:
    """
    Transform raw price + weather data into ML-ready features.
    
    Features created:
    - Lag features: price_t-1, price_t-7, price_t-14, price_t-30
    - Rolling statistics: mean, std, min, max over 7d/14d/30d windows
    - Seasonal features: month_sin, month_cos, week_sin, week_cos
    - Calendar: is_harvest_season, is_ramadan, is_weekend
    - Weather: temp_avg, rainfall_mm, humidity_pct
    - Volatility: rolling standard deviation of returns
    """

    @staticmethod
    def create_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Create feature matrix from raw price + weather data.
        
        Expected input columns:
        - date, retail_avg (or wholesale_avg), temp_avg, rainfall_mm, humidity_pct
        """
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        price_col = "retail_avg" if "retail_avg" in df.columns else "wholesale_avg"

        # --- Lag Features ---
        for lag in [1, 2, 3, 7, 14, 30]:
            df[f"price_lag_{lag}"] = df[price_col].shift(lag)

        # --- Rolling Statistics ---
        for window in [7, 14, 30]:
            df[f"price_roll_mean_{window}"] = df[price_col].rolling(window).mean()
            df[f"price_roll_std_{window}"] = df[price_col].rolling(window).std()
            df[f"price_roll_min_{window}"] = df[price_col].rolling(window).min()
            df[f"price_roll_max_{window}"] = df[price_col].rolling(window).max()

        # --- Price Returns (% change) ---
        df["return_1d"] = df[price_col].pct_change()
        df["return_7d"] = df[price_col].pct_change(7)

        # --- Volatility ---
        df["volatility_7d"] = df["return_1d"].rolling(7).std()
        df["volatility_30d"] = df["return_1d"].rolling(30).std()

        # --- Seasonal Features (cyclical encoding) ---
        df["month"] = df["date"].dt.month
        df["week"] = df["date"].dt.isocalendar().week.astype(int)
        df["day_of_week"] = df["date"].dt.dayofweek
        df["day_of_year"] = df["date"].dt.dayofyear

        # Cyclical encoding (sin/cos) for month and week
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
        df["week_sin"] = np.sin(2 * np.pi * df["week"] / 52)
        df["week_cos"] = np.cos(2 * np.pi * df["week"] / 52)

        # --- Calendar Flags ---
        df["is_harvest_season"] = df["month"].isin([2, 3, 4]).astype(int)
        df["is_lean_season"] = df["month"].isin([10, 11, 12]).astype(int)
        df["is_weekend"] = (df["day_of_week"] >= 4).astype(int)  # Fri-Sat in BD

        # --- Seasonal Index (from research) ---
        df["seasonal_index"] = df["month"].map(POTATO_SEASONAL_PATTERN)

        # --- Weather Features (fill missing with interpolation) ---
        for col in ["temp_avg", "rainfall_mm", "humidity_pct"]:
            if col in df.columns:
                df[col] = df[col].interpolate(method="linear")
                df[col] = df[col].fillna(df[col].median())

        return df

    @staticmethod
    def get_feature_columns() -> list[str]:
        """Return the list of feature columns for the model."""
        return [
            # Lags
            "price_lag_1", "price_lag_2", "price_lag_3",
            "price_lag_7", "price_lag_14", "price_lag_30",
            # Rolling stats
            "price_roll_mean_7", "price_roll_std_7",
            "price_roll_mean_14", "price_roll_std_14",
            "price_roll_mean_30", "price_roll_std_30",
            # Returns & volatility
            "return_1d", "return_7d", "volatility_7d", "volatility_30d",
            # Seasonal
            "month_sin", "month_cos", "week_sin", "week_cos",
            "is_harvest_season", "is_lean_season", "seasonal_index",
            # Weather
            "temp_avg", "rainfall_mm", "humidity_pct",
        ]


# ============================================================
# SARIMA MODEL
# ============================================================

class SARIMAPredictor:
    """
    Seasonal ARIMA model for potato price forecasting.
    
    SARIMA captures:
    - Trend component (prices generally rising with inflation)
    - Seasonal pattern (low Feb-Mar, high Nov-Dec)
    - Autoregressive behavior (yesterday's price predicts today's)
    
    Best for: Stable markets with clear seasonal patterns
    Weakness: Cannot capture sudden shocks or non-linear dynamics
    """

    def __init__(self):
        self.model = None
        self.results = None

    def train(self, price_series: pd.Series, exog: pd.DataFrame = None):
        """
        Train SARIMA model on historical price data.
        
        Args:
            price_series: Daily price series (should be at least 2 years)
            exog: Exogenous variables (weather, seasonal indices)
        """
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        logger.info("📊 Training SARIMA model...")
        logger.info(f"   Data points: {len(price_series)}")
        logger.info(f"   Date range: {price_series.index[0]} → {price_series.index[-1]}")

        self.model = SARIMAX(
            price_series,
            order=SARIMA_ORDER,
            seasonal_order=SARIMA_SEASONAL_ORDER,
            exog=exog,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )

        self.results = self.model.fit(disp=False, maxiter=200)

        # Log model diagnostics
        aic = self.results.aic
        bic = self.results.bic
        logger.success(f"✅ SARIMA trained | AIC: {aic:.1f} | BIC: {bic:.1f}")

        return self.results

    def predict(
        self,
        horizon_days: int = 7,
        exog_future: pd.DataFrame = None,
        confidence: float = 0.95
    ) -> dict:
        """
        Generate price forecast with confidence intervals.
        
        Returns:
            {
                "predicted_prices": [...],
                "confidence_lower": [...],
                "confidence_upper": [...],
                "dates": [...],
            }
        """
        if self.results is None:
            raise ValueError("Model not trained. Call train() first.")

        forecast = self.results.get_forecast(
            steps=horizon_days,
            exog=exog_future,
            alpha=1 - confidence,
        )

        mean = forecast.predicted_mean
        conf_int = forecast.conf_int()

        return {
            "predicted_prices": mean.values.tolist(),
            "confidence_lower": conf_int.iloc[:, 0].values.tolist(),
            "confidence_upper": conf_int.iloc[:, 1].values.tolist(),
            "dates": [
                (date.today() + timedelta(days=i+1)).isoformat()
                for i in range(horizon_days)
            ],
            "model": "sarima",
            "horizon_days": horizon_days,
        }


# ============================================================
# LSTM MODEL
# ============================================================

class LSTMPredictor:
    """
    LSTM (Long Short-Term Memory) neural network for price prediction.
    
    LSTM captures:
    - Non-linear price dynamics
    - Complex interactions between weather, season, and price
    - Anomalous market events (supply shocks, policy changes)
    
    Best for: Volatile markets, capturing sudden changes
    Weakness: Needs more data, can overfit on small datasets
    """

    def __init__(self):
        self.model = None
        self.scaler_X = None
        self.scaler_y = None
        self.is_trained = False

    def build_model(self, input_size: int):
        """Build the LSTM architecture."""
        try:
            import torch
            import torch.nn as nn

            class PotatoPriceLSTM(nn.Module):
                def __init__(self, input_size, hidden_size, num_layers, dropout):
                    super().__init__()
                    self.lstm = nn.LSTM(
                        input_size=input_size,
                        hidden_size=hidden_size,
                        num_layers=num_layers,
                        batch_first=True,
                        dropout=dropout if num_layers > 1 else 0,
                    )
                    self.dropout = nn.Dropout(dropout)
                    self.fc1 = nn.Linear(hidden_size, hidden_size // 2)
                    self.relu = nn.ReLU()
                    self.fc2 = nn.Linear(hidden_size // 2, 1)

                def forward(self, x):
                    lstm_out, _ = self.lstm(x)
                    last_hidden = lstm_out[:, -1, :]
                    out = self.dropout(last_hidden)
                    out = self.relu(self.fc1(out))
                    out = self.fc2(out)
                    return out

            self.model = PotatoPriceLSTM(
                input_size=input_size,
                hidden_size=LSTM_HIDDEN_SIZE,
                num_layers=LSTM_NUM_LAYERS,
                dropout=LSTM_DROPOUT,
            )
            logger.info(f"🧠 LSTM model built: {sum(p.numel() for p in self.model.parameters())} parameters")
            return self.model

        except ImportError:
            logger.warning("PyTorch not installed. LSTM predictions unavailable.")
            return None

    def prepare_sequences(
        self, features: np.ndarray, targets: np.ndarray, seq_length: int = None
    ) -> tuple:
        """
        Convert tabular data into sequences for LSTM.
        
        Args:
            features: (n_samples, n_features) array
            targets: (n_samples,) array
            seq_length: lookback window (default: 30 days)
            
        Returns:
            X: (n_sequences, seq_length, n_features)
            y: (n_sequences,)
        """
        seq_length = seq_length or LSTM_SEQUENCE_LENGTH
        X, y = [], []

        for i in range(seq_length, len(features)):
            X.append(features[i - seq_length:i])
            y.append(targets[i])

        return np.array(X), np.array(y)

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        epochs: int = 100,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        validation_split: float = 0.15,
    ):
        """
        Train the LSTM model.
        """
        try:
            import torch
            import torch.nn as nn
            from torch.utils.data import DataLoader, TensorDataset
            from sklearn.preprocessing import MinMaxScaler

            # Scale features
            self.scaler_X = MinMaxScaler()
            self.scaler_y = MinMaxScaler()

            n_samples, seq_len, n_features = X_train.shape
            X_flat = X_train.reshape(-1, n_features)
            X_scaled = self.scaler_X.fit_transform(X_flat).reshape(n_samples, seq_len, n_features)
            y_scaled = self.scaler_y.fit_transform(y_train.reshape(-1, 1)).flatten()

            # Build model if not already built
            if self.model is None:
                self.build_model(n_features)

            if self.model is None:
                return

            # Split validation
            split_idx = int(len(X_scaled) * (1 - validation_split))
            X_t, X_v = X_scaled[:split_idx], X_scaled[split_idx:]
            y_t, y_v = y_scaled[:split_idx], y_scaled[split_idx:]

            # Convert to tensors
            train_ds = TensorDataset(
                torch.FloatTensor(X_t), torch.FloatTensor(y_t)
            )
            train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

            # Training
            optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
            criterion = nn.MSELoss()
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, patience=10, factor=0.5
            )

            self.model.train()
            best_val_loss = float("inf")

            logger.info(f"🏋️ Training LSTM: {epochs} epochs, {n_samples} samples")

            for epoch in range(epochs):
                epoch_loss = 0
                for X_batch, y_batch in train_loader:
                    optimizer.zero_grad()
                    predictions = self.model(X_batch).squeeze()
                    loss = criterion(predictions, y_batch)
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                    optimizer.step()
                    epoch_loss += loss.item()

                avg_loss = epoch_loss / len(train_loader)

                # Validation
                self.model.eval()
                with torch.no_grad():
                    val_pred = self.model(torch.FloatTensor(X_v)).squeeze()
                    val_loss = criterion(val_pred, torch.FloatTensor(y_v)).item()
                self.model.train()

                scheduler.step(val_loss)

                if val_loss < best_val_loss:
                    best_val_loss = val_loss

                if (epoch + 1) % 20 == 0:
                    logger.info(
                        f"   Epoch {epoch+1}/{epochs} | "
                        f"Train Loss: {avg_loss:.6f} | Val Loss: {val_loss:.6f}"
                    )

            self.is_trained = True
            logger.success(f"✅ LSTM training complete | Best Val Loss: {best_val_loss:.6f}")

        except ImportError:
            logger.warning("PyTorch not installed. Skipping LSTM training.")

    def predict(self, X_input: np.ndarray) -> dict:
        """
        Generate price prediction from feature sequence.
        
        Args:
            X_input: (1, seq_length, n_features) or (seq_length, n_features)
            
        Returns:
            {"predicted_price": float, "model": "lstm"}
        """
        if not self.is_trained or self.model is None:
            return {"predicted_price": None, "model": "lstm", "error": "Model not trained"}

        try:
            import torch

            if X_input.ndim == 2:
                X_input = X_input[np.newaxis, :]

            n_samples, seq_len, n_features = X_input.shape
            X_flat = X_input.reshape(-1, n_features)
            X_scaled = self.scaler_X.transform(X_flat).reshape(n_samples, seq_len, n_features)

            self.model.eval()
            with torch.no_grad():
                pred_scaled = self.model(torch.FloatTensor(X_scaled)).squeeze().numpy()

            pred = self.scaler_y.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()

            return {
                "predicted_price": float(pred[0]),
                "model": "lstm",
            }

        except Exception as e:
            logger.error(f"LSTM prediction failed: {e}")
            return {"predicted_price": None, "model": "lstm", "error": str(e)}


# ============================================================
# HYBRID ENSEMBLE
# ============================================================

class HybridEnsemble:
    """
    Combines SARIMA and LSTM predictions using adaptive weighting.
    
    Strategy:
    - Stable market (low volatility) → Weight SARIMA more (0.6/0.4)
    - Volatile market → Weight LSTM more (0.3/0.7)
    - Uses recent prediction errors to calibrate weights
    """

    def __init__(self):
        self.sarima = SARIMAPredictor()
        self.lstm = LSTMPredictor()
        self.weight_sarima = 0.5
        self.weight_lstm = 0.5
        self.volatility_threshold = 0.03  # 3% daily return std

    def adaptive_weights(self, recent_volatility: float) -> tuple[float, float]:
        """
        Compute adaptive weights based on recent market volatility.
        """
        if recent_volatility < self.volatility_threshold:
            # Stable → trust SARIMA's seasonal patterns
            w_sarima, w_lstm = 0.6, 0.4
        elif recent_volatility < self.volatility_threshold * 2:
            # Moderate → balanced
            w_sarima, w_lstm = 0.45, 0.55
        else:
            # Volatile → trust LSTM's pattern recognition
            w_sarima, w_lstm = 0.3, 0.7

        self.weight_sarima = w_sarima
        self.weight_lstm = w_lstm

        return w_sarima, w_lstm

    def predict(
        self,
        sarima_pred: float,
        lstm_pred: Optional[float],
        recent_volatility: float
    ) -> dict:
        """
        Generate ensemble prediction.
        """
        w_s, w_l = self.adaptive_weights(recent_volatility)

        if lstm_pred is None:
            # LSTM unavailable — use SARIMA only
            final_pred = sarima_pred
            model_used = "sarima_only"
        else:
            final_pred = w_s * sarima_pred + w_l * lstm_pred
            model_used = f"ensemble (SARIMA:{w_s:.0%}, LSTM:{w_l:.0%})"

        return {
            "predicted_price": final_pred,
            "sarima_prediction": sarima_pred,
            "lstm_prediction": lstm_pred,
            "weight_sarima": w_s,
            "weight_lstm": w_l,
            "model": model_used,
            "volatility": recent_volatility,
        }


# ============================================================
# QUICK TEST WITH SYNTHETIC DATA
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 KrishiVault Price Prediction — Synthetic Test")
    print("=" * 60)

    # Generate synthetic potato price data (simulating seasonal pattern)
    np.random.seed(42)
    days = 365 * 3  # 3 years of daily data
    dates = pd.date_range(start="2023-01-01", periods=days, freq="D")

    # Base price with seasonal pattern
    base_price = 20  # Tk per kg
    seasonal = np.array([
        POTATO_SEASONAL_PATTERN.get(d.month, 1.0) for d in dates
    ])
    noise = np.random.normal(0, 1.5, days)
    trend = np.linspace(0, 3, days)  # Slight upward trend (inflation)

    prices = base_price * seasonal + noise + trend
    prices = np.maximum(prices, 5)  # Floor at Tk 5/kg

    # Synthetic weather
    temp = 25 + 8 * np.sin(2 * np.pi * np.arange(days) / 365) + np.random.normal(0, 2, days)
    rain = np.maximum(0, 5 + 8 * np.sin(2 * np.pi * (np.arange(days) - 120) / 365) + np.random.normal(0, 3, days))
    humidity = 60 + 20 * np.sin(2 * np.pi * (np.arange(days) - 90) / 365) + np.random.normal(0, 5, days)

    df = pd.DataFrame({
        "date": dates,
        "retail_avg": prices,
        "temp_avg": temp,
        "rainfall_mm": rain,
        "humidity_pct": humidity,
    })

    # Feature engineering
    fe = FeatureEngineer()
    df_features = fe.create_features(df)
    df_features = df_features.dropna()

    print(f"\n📊 Dataset: {len(df_features)} samples after feature engineering")
    print(f"📅 Range: {df_features['date'].min()} → {df_features['date'].max()}")

    feature_cols = fe.get_feature_columns()
    available_cols = [c for c in feature_cols if c in df_features.columns]
    print(f"🔧 Features: {len(available_cols)} columns")

    # --- SARIMA Test ---
    print("\n--- SARIMA ---")
    price_series = df_features.set_index("date")["retail_avg"]
    sarima = SARIMAPredictor()

    try:
        sarima.train(price_series)
        forecast = sarima.predict(horizon_days=7)
        print(f"7-day forecast: {[f'Tk {p:.1f}' for p in forecast['predicted_prices']]}")
    except Exception as e:
        print(f"SARIMA error: {e}")

    # --- Ensemble Test ---
    print("\n--- Ensemble ---")
    ensemble = HybridEnsemble()
    volatility = df_features["volatility_30d"].iloc[-1] if "volatility_30d" in df_features.columns else 0.02

    sarima_pred = forecast["predicted_prices"][0] if forecast.get("predicted_prices") else 22.0
    result = ensemble.predict(sarima_pred, None, volatility)
    print(f"Ensemble prediction: Tk {result['predicted_price']:.2f}/kg")
    print(f"Model: {result['model']}")
    print(f"Volatility: {result['volatility']:.4f}")

    print("\n✅ Prediction pipeline test complete!")
