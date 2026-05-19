from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer


ROOT = Path(__file__).resolve().parents[2]


def train() -> None:
    path = ROOT / "data" / "processed" / "ganak_sale_clean.csv"
    df = pd.read_csv(path)
    if len(df) < 2:
        print("not enough rows for sale model")
        return
    features = ["dong", "housing_type", "area_m2", "floor", "built_year"]
    preprocessor = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore"), ["dong", "housing_type"])],
        remainder="passthrough",
    )
    model = Pipeline([("preprocess", preprocessor), ("rf", RandomForestRegressor(n_estimators=30, random_state=42))])
    model.fit(df[features], df["price"])
    (ROOT / "models").mkdir(exist_ok=True)
    joblib.dump(model, ROOT / "models" / "sale_model.pkl")
    print("saved models/sale_model.pkl")


if __name__ == "__main__":
    train()
