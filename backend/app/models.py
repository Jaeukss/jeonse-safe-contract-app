from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn

from .address import NormalizedContract


ROOT = Path(__file__).resolve().parents[2]
MARKET_PATH = ROOT / "data" / "market_transactions_mvp.csv"


class TabularMLP(nn.Module):
    """Small tabular MLP used directly in the Hugging Face Space."""

    def __init__(self, input_dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 48),
            nn.ReLU(),
            nn.Linear(48, 24),
            nn.ReLU(),
            nn.Linear(24, 1),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.net(features)


@dataclass
class PricePrediction:
    predicted_rent_price: int
    predicted_sale_price: int
    model_note: str


@dataclass
class TrainedPriceModels:
    rent_model: TabularMLP
    sale_model: TabularMLP
    feature_columns: list[str]
    mean: np.ndarray
    std: np.ndarray
    fallback_rent: int
    fallback_sale: int


def _prepare_training_frame() -> tuple[pd.DataFrame, list[str]]:
    frame = pd.read_csv(MARKET_PATH, encoding="utf-8-sig")
    frame["exclusive_area_m2"] = pd.to_numeric(frame["exclusive_area_m2"], errors="coerce")
    frame["floor"] = pd.to_numeric(frame["floor"], errors="coerce").fillna(0)
    frame["built_year"] = pd.to_numeric(frame["built_year"], errors="coerce").fillna(frame["built_year"].median())
    frame["price_or_deposit_won"] = pd.to_numeric(frame["price_or_deposit_won"], errors="coerce")
    frame = frame.dropna(subset=["exclusive_area_m2", "price_or_deposit_won"]).copy()
    frame["area_x_year"] = frame["exclusive_area_m2"] * frame["built_year"]
    frame["area_x_floor"] = frame["exclusive_area_m2"] * frame["floor"]
    dummies = pd.get_dummies(frame[["legal_dong_code", "housing_type"]].astype(str), prefix=["dong", "type"])
    numeric = frame[["exclusive_area_m2", "floor", "built_year", "area_x_year", "area_x_floor"]].astype(float)
    model_frame = pd.concat([frame[["trade_type", "price_or_deposit_won"]], numeric, dummies], axis=1)
    feature_columns = [column for column in model_frame.columns if column not in {"trade_type", "price_or_deposit_won"}]
    return model_frame, feature_columns


def _train_one(features: np.ndarray, target: np.ndarray) -> TabularMLP:
    torch.manual_seed(42)
    model = TabularMLP(features.shape[1])
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.015, weight_decay=0.001)
    loss_fn = nn.SmoothL1Loss()
    x = torch.tensor(features, dtype=torch.float32)
    y = torch.tensor(np.log1p(target).reshape(-1, 1), dtype=torch.float32)
    for _ in range(260):
        optimizer.zero_grad()
        loss = loss_fn(model(x), y)
        loss.backward()
        optimizer.step()
    model.eval()
    return model


@lru_cache(maxsize=1)
def train_price_models() -> TrainedPriceModels:
    model_frame, feature_columns = _prepare_training_frame()
    x_raw = model_frame[feature_columns].astype(float).to_numpy()
    mean = x_raw.mean(axis=0)
    std = x_raw.std(axis=0)
    std[std == 0] = 1
    x = (x_raw - mean) / std

    rent_rows = model_frame["trade_type"] == "전세"
    sale_rows = model_frame["trade_type"] == "매매"
    rent_model = _train_one(x[rent_rows], model_frame.loc[rent_rows, "price_or_deposit_won"].to_numpy())
    sale_model = _train_one(x[sale_rows], model_frame.loc[sale_rows, "price_or_deposit_won"].to_numpy())

    return TrainedPriceModels(
        rent_model=rent_model,
        sale_model=sale_model,
        feature_columns=feature_columns,
        mean=mean,
        std=std,
        fallback_rent=int(model_frame.loc[rent_rows, "price_or_deposit_won"].median()),
        fallback_sale=int(model_frame.loc[sale_rows, "price_or_deposit_won"].median()),
    )


def _features_for_contract(contract: NormalizedContract, model: TrainedPriceModels) -> np.ndarray:
    row = {column: 0.0 for column in model.feature_columns}
    area = float(contract.exclusive_area_m2)
    floor = float(contract.floor or 0)
    built_year = float(contract.built_year or 2010)
    row["exclusive_area_m2"] = area
    row["floor"] = floor
    row["built_year"] = built_year
    row["area_x_year"] = area * built_year
    row["area_x_floor"] = area * floor

    dong_col = f"dong_{contract.legal_dong_code}"
    type_col = f"type_{contract.housing_type}"
    if dong_col in row:
        row[dong_col] = 1.0
    if type_col in row:
        row[type_col] = 1.0

    values = np.array([row[column] for column in model.feature_columns], dtype=float)
    return (values - model.mean) / model.std


def predict_prices(contract: NormalizedContract, market: dict) -> PricePrediction:
    trained = train_price_models()
    x = torch.tensor(_features_for_contract(contract, trained).reshape(1, -1), dtype=torch.float32)
    with torch.no_grad():
        rent = int(np.expm1(trained.rent_model(x).item()))
        sale = int(np.expm1(trained.sale_model(x).item()))

    # Anchor extreme cold-start predictions to nearby medians where available.
    if market["rent"]["median"]:
        rent = int((rent + market["rent"]["median"]) / 2)
    if market["sale"]["median"]:
        sale = int((sale + market["sale"]["median"]) / 2)
    rent = max(rent, int(trained.fallback_rent * 0.35))
    sale = max(sale, int(rent / 0.62), int(trained.fallback_sale * 0.35))

    return PricePrediction(
        predicted_rent_price=round(rent / 1_000_000) * 1_000_000,
        predicted_sale_price=round(sale / 1_000_000) * 1_000_000,
        model_note="PyTorch TabularMLP trained on included MVP transaction data",
    )
