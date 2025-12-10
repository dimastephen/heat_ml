import json
from pathlib import Path
from typing import Tuple, Dict, Any, List
from uuid import UUID

import numpy as np
import pandas as pd
import requests
import tensorflow as tf
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.models import Sequential
from tensorflow.keras.optimizers import Adam

from sqlalchemy import text

from src.core.logger import logger
from src.config import settings
from src.database import PgSessionLocal, TsSessionLocal
from src.files.repository import IngestionBatchRepository
from src.files.models import IngestionBatch
from src.forecasts.models import ForecastJob, ForecastStatus, ForecastSeries, ForecastHouseSeries
from src.forecasts.repository import (
    ForecastJobRepository,
    ForecastSeriesRepository,
    ForecastHouseSeriesRepository,
)


DEFAULT_SEQ_LEN = 60
DEFAULT_EPOCHS = 60
DEFAULT_BATCH_SIZE = 64

_TIMESCALE_READY = False


def run_forecast(job_id: UUID):
    db = PgSessionLocal()
    ts_db = TsSessionLocal() if TsSessionLocal is not None else db
    series_repo = ForecastSeriesRepository(ts_db, ForecastSeries)
    house_series_repo = ForecastHouseSeriesRepository(ts_db, ForecastHouseSeries)
    job_repo = ForecastJobRepository(db, ForecastJob)
    batch_repo = IngestionBatchRepository(db, IngestionBatch)

    job = job_repo.get(job_id)
    if not job:
        logger.error("Forecast job not found", extra={"job_id": str(job_id)})
        db.close()
        if ts_db is not db:
            ts_db.close()
        return

    batch = batch_repo.get(job.batch_id)
    if not batch or not batch.prepared_path:
        logger.error("Prepared dataset missing", extra={"job_id": str(job_id)})
        job_repo.update(job, {"status": ForecastStatus.failed.value, "errors": [{"msg": "dataset missing"}]})
        db.close()
        if ts_db is not db:
            ts_db.close()
        return

    if TsSessionLocal is not None:
        logger.debug("Ensuring Timescale hypertable exists", extra={"job_id": str(job_id)})
        ensure_timescale_hypertable()

    try:
        if not settings.API_KEY:
            raise ValueError("Weather API key is not configured")

        location_name = settings.LOCATION or "Ulyanovsk"
        logger.info(
            "Starting forecast job",
            extra={
                "job_id": str(job.id),
                "batch_id": str(job.batch_id),
                "location": location_name,
            },
        )

        job_repo.update(job, {"status": ForecastStatus.processing.value})
        dataset_path = Path(batch.prepared_path)
        logger.debug("Loading prepared dataset", extra={"path": str(dataset_path)})
        data = pd.read_csv(dataset_path)
        if "date" in data.columns:
            data["date"] = pd.to_datetime(data["date"], errors="coerce")
        logger.info("Loaded dataset", extra={"rows": len(data), "columns": list(data.columns)})
        data, feature_cols = add_encoded_features(data)
        logger.debug("Feature columns prepared", extra={"count": len(feature_cols)})
        seq_len = DEFAULT_SEQ_LEN
        batch_size = DEFAULT_BATCH_SIZE
        epochs = DEFAULT_EPOCHS
        address_uuids = data["address_uuid"].unique().tolist()
        logger.info("Unique houses detected", extra={"houses": len(address_uuids)})

        last_date = data["date"].max()
        start_season, end_season, future_dates = get_next_heating_season_range(last_date)
        weather_df = fetch_visualcrossing_daily(
            api_key=settings.API_KEY,
            location=location_name,
            start_date=start_season.strftime("%Y-%m-%d"),
            end_date=end_season.strftime("%Y-%m-%d"),
        )

        scaler_X, scaler_y, X_all, y_all = fit_global_scalers(data, feature_cols, seq_len)
        logger.debug("Global scalers fitted", extra={"X_shape": X_all.shape, "y_shape": y_all.shape})
        X_train, y_train, X_test, y_test, per_house_data = build_train_test_sets(
            data, X_all, y_all, seq_len
        )
        logger.info(
            "Built train/test datasets",
            extra={
                "X_train": X_train.shape,
                "X_test": X_test.shape,
                "houses_with_sequences": len(per_house_data),
            },
        )

        n_features = X_train.shape[2]
        model = build_lstm_model(seq_len, n_features)

        history = model.fit(
            X_train,
            y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(X_test, y_test),
            verbose=1,
        )
        logger.info("Model training finished", extra={"epochs": epochs})

        y_test_pred_scaled = model.predict(X_test)
        y_test_true = scaler_y.inverse_transform(y_test.reshape(-1, 1))
        y_test_pred = scaler_y.inverse_transform(y_test_pred_scaled)

        test_rmse = float(np.sqrt(mean_squared_error(y_test_true, y_test_pred)))
        test_mape = float(mean_absolute_percentage_error(y_test_true, y_test_pred))
        logger.info("GLOBAL TEST: RMSE=%.3f, MAPE=%.3f", test_rmse, test_mape)

        house_list = address_uuids if address_uuids is not None else list(per_house_data.keys())

        forecasts: Dict[str, List[Dict[str, Any]]] = {}
        aggregated_frames: List[pd.DataFrame] = []
        house_series_payload: list[dict] = []

        for addr in house_list:
            try:
                logger.debug("Forecasting house", extra={"job_id": str(job.id), "house": addr})
                future_df, y_future = forecast_next_heating_season_with_api(
                    model=model,
                    data=data,
                    scaler_X=scaler_X,
                    scaler_y=scaler_y,
                    feature_cols=feature_cols,
                    address_uuid=addr,
                    api_key=settings.API_KEY,
                    location=location_name,
                    weather_df=weather_df,
                    future_dates=future_dates,
                    seq_len=seq_len,
                )
                future_df = future_df.copy()
                future_df["value_forecast"] = y_future
                aggregated_frames.append(future_df[["date", "value_forecast"]].copy())
                json_ready = future_df.copy()
                json_ready["date"] = json_ready["date"].dt.strftime("%Y-%m-%d")
                forecasts[addr] = json_ready.to_dict(orient="records")
                house_series_payload.extend(
                    [
                        {
                            "job_id": job.id,
                            "house_id": addr,
                            "timestamp": row.date.to_pydatetime(),
                            "value": float(row.value_forecast),
                        }
                        for row in future_df.itertuples()
                    ]
                )
                logger.info(
                    "House forecast ready",
                    extra={"job_id": str(job.id), "house": addr, "points": len(y_future)},
                )
            except Exception as exc:
                logger.exception("Ошибка прогноза для дома %s", addr)
                forecasts[addr] = {"error": str(exc)}

        successful_frames = [frame for frame in aggregated_frames if not frame.empty]
        if not successful_frames:
            raise ValueError("Forecast generation failed for all houses")

        aggregated_df = (
            pd.concat(successful_frames)
            .groupby("date", as_index=False)["value_forecast"]
            .sum()
            .sort_values("date")
        )

        result = {
            "metrics": {
                "test_rmse": test_rmse,
                "test_mape": test_mape,
                "houses": len(house_list),
                "points": int(len(aggregated_df)),
            },
            "forecast": forecasts,
            "history": {
                "loss": [float(v) for v in history.history.get("loss", [])],
                "val_loss": [float(v) for v in history.history.get("val_loss", [])],
            },
        }

        model_dir = Path(settings.MODEL_STORAGE_PATH) / str(job.id)
        model_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Model artifacts directory prepared", extra={"path": str(model_dir)})

        series_payload = [
            {
                "job_id": job.id,
                "timestamp": pd.to_datetime(row.date).to_pydatetime(),
                "value": float(row.value_forecast),
            }
            for row in aggregated_df.itertuples()
        ]
        series_repo.bulk_create(series_payload)
        logger.info(
            "Forecast series stored",
            extra={"job_id": str(job.id), "points": len(series_payload)},
        )
        if house_series_payload:
            house_series_repo.bulk_create(house_series_payload)
            logger.info(
                "House series stored",
                extra={"job_id": str(job.id), "points": len(house_series_payload)},
            )

        artifact_df = aggregated_df.rename(columns={"value_forecast": "prediction"})
        output_path = model_dir / "forecast.csv"
        artifact_df.to_csv(output_path, index=False)
        logger.debug("CSV artifact saved", extra={"path": str(output_path)})

        forecast_json_path = model_dir / "forecast.json"
        with forecast_json_path.open("w", encoding="utf-8") as fp:
            json.dump(result, fp, ensure_ascii=False, indent=2)
        logger.debug("JSON artifact saved", extra={"path": str(forecast_json_path)})

        job_repo.update(job, {
            "status": ForecastStatus.completed.value,
            "artifact_path": str(output_path),
            "metrics": result["metrics"],
            "errors": [],
        })
        logger.info(
            "Forecast completed",
            extra={"job_id": str(job.id), "points": len(series_payload), "houses": len(house_list)},
        )
    except Exception as exc:
        logger.exception("Forecast failed", extra={"job_id": str(job_id)})
        job_repo.update(job, {
            "status": ForecastStatus.failed.value,
            "errors": [{"code": "forecast_error", "msg": str(exc)}],
        })
    finally:
        db.close()
        if ts_db is not db:
            ts_db.close()

def load_prepared_data(csv_path: str) -> pd.DataFrame:
    """Read prepared dataset and sort by house/date."""
    data = pd.read_csv(csv_path, sep=";", decimal=".")
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date"])
    data = data.sort_values(["address_uuid", "date"]).reset_index(drop=True)
    return data


def add_encoded_features(data: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Encode categorical features and return feature list."""
    numeric_features = [
        "temp_avg", "humidity_avg",
        "build_year", "floor_number",
        "residential_area",
        "roof_area_metal", "roof_area_total",
        "roof_area_web", "roof_area_piece_goods",
    ]

    required_cols = numeric_features + ["wall_type", "day_sin", "day_cos", "value", "address_uuid"]
    for col in required_cols:
        if col not in data.columns:
            raise ValueError(f"В данных нет обязательной колонки: {col}")

    data = data.copy()

    le_wall = LabelEncoder()
    le_house = LabelEncoder()

    data["wall_type"] = le_wall.fit_transform(data["wall_type"].astype(str))
    data["house_id"] = le_house.fit_transform(data["address_uuid"].astype(str))

    feature_cols = numeric_features + ["wall_type", "house_id", "day_sin", "day_cos"]

    data = data.reset_index(drop=True)
    data["row_idx"] = np.arange(len(data))

    return data, feature_cols


def fit_global_scalers(
    data: pd.DataFrame,
    feature_cols: List[str],
    sequence_length: int = DEFAULT_SEQ_LEN,
) -> Tuple[MinMaxScaler, MinMaxScaler, np.ndarray, np.ndarray]:
    """Fit global scalers and return scaled arrays."""
    X_all_raw = data[feature_cols].values
    y_all_raw = data[["value"]].values

    train_row_idx: List[int] = []

    for _, house_df in data.groupby("address_uuid"):
        n = len(house_df)
        if n <= sequence_length + 5:
            continue
        cut = int(0.8 * n)
        train_row_idx.extend(house_df.iloc[:cut]["row_idx"].to_list())

    train_row_idx = np.array(train_row_idx, dtype=int)

    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()

    scaler_X.fit(X_all_raw[train_row_idx])
    scaler_y.fit(y_all_raw[train_row_idx])

    X_all = scaler_X.transform(X_all_raw)
    y_all = scaler_y.transform(y_all_raw).flatten()

    return scaler_X, scaler_y, X_all, y_all


def create_sequences_for_house(
    house_df: pd.DataFrame,
    X_scaled: np.ndarray,
    y_scaled: np.ndarray,
    seq_len: int,
) -> Tuple[np.ndarray, np.ndarray]:
    idx = house_df["row_idx"].to_numpy()
    X_house = X_scaled[idx]
    y_house = y_scaled[idx]

    if len(X_house) <= seq_len:
        return np.empty((0, seq_len, X_house.shape[1])), np.empty((0,))

    X_seq, y_seq = [], []
    for i in range(seq_len, len(X_house)):
        X_seq.append(X_house[i - seq_len: i])
        y_seq.append(y_house[i])

    return np.array(X_seq), np.array(y_seq)


def build_train_test_sets(
    data: pd.DataFrame,
    X_all: np.ndarray,
    y_all: np.ndarray,
    seq_len: int = DEFAULT_SEQ_LEN,
):
    """Build train/test arrays and per-house data."""
    X_train_list, y_train_list = [], []
    X_test_list, y_test_list = [], []
    per_house_data: Dict[str, Dict[str, np.ndarray]] = {}

    for addr, house_df in data.groupby("address_uuid"):
        house_df = house_df.sort_values("date")

        X_seq, y_seq = create_sequences_for_house(house_df, X_all, y_all, seq_len)
        if X_seq.shape[0] == 0:
            continue

        n_samples = X_seq.shape[0]
        split = int(0.8 * n_samples)

        X_train_house = X_seq[:split]
        y_train_house = y_seq[:split]
        X_test_house = X_seq[split:]
        y_test_house = y_seq[split:]

        if len(X_train_house) == 0 or len(X_test_house) == 0:
            continue

        X_train_list.append(X_train_house)
        y_train_list.append(y_train_house)
        X_test_list.append(X_test_house)
        y_test_list.append(y_test_house)

        per_house_data[addr] = {
            "X_train": X_train_house,
            "y_train": y_train_house,
            "X_test": X_test_house,
            "y_test": y_test_house,
        }

    X_train = np.vstack(X_train_list)
    y_train = np.hstack(y_train_list)
    X_test = np.vstack(X_test_list)
    y_test = np.hstack(y_test_list)

    return X_train, y_train, X_test, y_test, per_house_data


def build_lstm_model(seq_len: int, n_features: int) -> tf.keras.Model:
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(seq_len, n_features)),
        LSTM(32),
        Dense(32, activation="relu"),
        Dense(1, activation="linear"),
    ])
    model.compile(optimizer=Adam(learning_rate=1e-3), loss="mse")
    return model


def fetch_visualcrossing_daily(
    api_key: str,
    location: str,
    start_date: str,
    end_date: str,
    unit_group: str = "metric",
) -> pd.DataFrame:
    """Fetch daily weather data from Visual Crossing."""
    base_url = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
    url = f"{base_url}/{location}/{start_date}/{end_date}"

    params = {
        "key": api_key,
        "unitGroup": unit_group,
        "include": "days",
        "elements": "datetime,temp,humidity",
        "contentType": "json",
    }

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "days" not in data:
        raise ValueError(f"Нет ключа 'days' в ответе API: {data.keys()}")

    days = data["days"]
    df = pd.DataFrame(days)
    df = df[["datetime", "temp", "humidity"]]
    df = df.rename(columns={"datetime": "date", "temp": "temp_avg", "humidity": "humidity_avg"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def get_current_heating_season_year(last_date: pd.Timestamp) -> int:
    """Return heating season year for given date."""
    if last_date.month > 10 or (last_date.month == 10 and last_date.day >= 1):
        return last_date.year
    else:
        return last_date.year - 1


def get_next_heating_season_range(last_date: pd.Timestamp):
    """Return start/end and date range for next heating season."""
    current_season_year = get_current_heating_season_year(last_date)
    next_season_year = current_season_year + 1

    start = pd.Timestamp(f"{next_season_year}-10-01")
    end = pd.Timestamp(f"{next_season_year + 1}-04-30")
    future_dates = pd.date_range(start, end, freq="D")
    return start, end, future_dates

def forecast_next_heating_season_with_api(
    model: tf.keras.Model,
    data: pd.DataFrame,
    scaler_X: MinMaxScaler,
    scaler_y: MinMaxScaler,
    feature_cols: List[str],
    address_uuid: str,
    api_key: str,
    location: str,
    seq_len: int = DEFAULT_SEQ_LEN,
    unit_group: str = "metric",
    weather_df: pd.DataFrame | None = None,
    future_dates: pd.DatetimeIndex | None = None,
):
    """Forecast next heating season for a single house."""
    house_df = data[data["address_uuid"] == address_uuid].copy()
    if house_df.empty:
        raise ValueError(f"Дом {address_uuid} не найден в данных.")

    house_df = house_df.sort_values("date").reset_index(drop=True)
    last_date = house_df["date"].max()

    if future_dates is None:
        start, end, future_dates = get_next_heating_season_range(last_date)
    else:
        if not isinstance(future_dates, pd.DatetimeIndex):
            future_dates = pd.DatetimeIndex(future_dates)
        expected_range = pd.date_range(future_dates[0], future_dates[-1], freq="D")
        if len(expected_range) != len(future_dates) or not future_dates.equals(expected_range):
            raise ValueError("Полученный диапазон дат будущего сезона некорректен или содержит пропуски.")
    n_future = len(future_dates)

    if weather_df is None:
        weather_df = fetch_visualcrossing_daily(
            api_key=api_key,
            location=location,
            start_date=future_dates[0].strftime("%Y-%m-%d"),
            end_date=future_dates[-1].strftime("%Y-%m-%d"),
            unit_group=unit_group,
        )

    weather_local = weather_df.copy()
    if "date" in weather_local.columns:
        weather_local["date"] = pd.to_datetime(weather_local["date"], errors="coerce")
        weather_local = weather_local.set_index("date")
    weather_local = weather_local.reindex(future_dates)
    if weather_local["temp_avg"].isna().any():
        raise ValueError("В погодных данных есть пропуски по temp_avg после reindex.")

    if weather_local["humidity_avg"].isna().any():
        weather_local["humidity_avg"] = weather_local["humidity_avg"].fillna(weather_local["humidity_avg"].mean())

    temp_future = weather_local["temp_avg"].to_numpy()
    humidity_future = weather_local["humidity_avg"].to_numpy()

    last_row = house_df.iloc[-1]
    static_values = {
        "build_year": last_row["build_year"],
        "floor_number": last_row["floor_number"],
        "residential_area": last_row["residential_area"],
        "roof_area_metal": last_row["roof_area_metal"],
        "roof_area_total": last_row["roof_area_total"],
        "roof_area_web": last_row["roof_area_web"],
        "roof_area_piece_goods": last_row["roof_area_piece_goods"],
        "wall_type": last_row["wall_type"],
        "house_id": last_row["house_id"],
    }

    day_of_season = np.arange(1, n_future + 1)
    season_len = n_future
    day_sin_future = np.sin(2 * np.pi * day_of_season / season_len)
    day_cos_future = np.cos(2 * np.pi * day_of_season / season_len)

    future_df = pd.DataFrame({
        "date": future_dates,
        "address_uuid": address_uuid,
        "temp_avg": temp_future,
        "humidity_avg": humidity_future,
        "day_sin": day_sin_future,
        "day_cos": day_cos_future,
    })
    for col, val in static_values.items():
        future_df[col] = val

    future_features = future_df[feature_cols]

    if len(house_df) < seq_len:
        raise ValueError(f"Для дома {address_uuid} недостаточно истории (< {seq_len} точек).")

    history_tail = house_df.tail(seq_len)
    history_features = history_tail[feature_cols]

    combined_features = pd.concat([history_features, future_features], axis=0)
    X_combined_scaled = scaler_X.transform(combined_features.values)

    X_future_seq = []
    for i in range(n_future):
        window = X_combined_scaled[i: i + seq_len]
        X_future_seq.append(window)

    X_future_seq = np.array(X_future_seq)
    y_future_scaled = model.predict(X_future_seq)
    y_future = scaler_y.inverse_transform(y_future_scaled).reshape(-1)

    return future_df, y_future


def ensure_timescale_hypertable() -> None:
    if TsSessionLocal is None:
        return

    global _TIMESCALE_READY
    if _TIMESCALE_READY:
        return

    session = TsSessionLocal()
    try:
        ForecastSeries.__table__.create(bind=session.bind, checkfirst=True)
        ForecastHouseSeries.__table__.create(bind=session.bind, checkfirst=True)
        session.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
        session.execute(
            text(
                "SELECT create_hypertable('forecast_series', 'timestamp', if_not_exists => TRUE, create_default_indexes => TRUE)"
            )
        )
        session.execute(
            text(
                "SELECT create_hypertable('forecast_house_series', 'timestamp', if_not_exists => TRUE, create_default_indexes => TRUE)"
            )
        )
        session.commit()
        _TIMESCALE_READY = True
        logger.info("Timescale hypertable ready")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
