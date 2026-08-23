"""Random-forest regression model for fair campus resale prices."""

from functools import lru_cache

import numpy as np
from sklearn.ensemble import RandomForestRegressor

CATEGORY = {"books": 0, "electronics": 1, "lab": 2, "hostel": 3, "sports": 4, "other": 5}
CONDITION = {"new": 1.0, "like_new": 0.88, "good": 0.72, "fair": 0.55, "used": 0.38}
TRANSACTION = {"sell": 0, "rent": 1, "borrow": 2, "donate": 3}

# Synthetic but domain-specific starter history. The model can be retrained later
# with real transactions exported from the Payment table.
TRAINING_ROWS = [
    ("books", "new", "sell", 62, 92, 950),
    ("books", "like_new", "sell", 78, 87, 760),
    ("books", "good", "sell", 55, 76, 520),
    ("books", "fair", "sell", 35, 63, 330),
    ("books", "good", "rent", 60, 74, 120),
    ("electronics", "new", "sell", 85, 94, 32500),
    ("electronics", "like_new", "sell", 82, 88, 24500),
    ("electronics", "good", "sell", 74, 78, 15200),
    ("electronics", "fair", "sell", 58, 62, 8200),
    ("electronics", "good", "rent", 76, 76, 950),
    ("lab", "new", "sell", 72, 93, 2800),
    ("lab", "like_new", "sell", 68, 86, 2100),
    ("lab", "good", "sell", 60, 76, 1450),
    ("lab", "fair", "sell", 42, 59, 820),
    ("lab", "good", "rent", 64, 75, 240),
    ("hostel", "new", "sell", 69, 91, 1800),
    ("hostel", "like_new", "sell", 73, 84, 1300),
    ("hostel", "good", "sell", 56, 73, 850),
    ("hostel", "fair", "sell", 40, 60, 480),
    ("hostel", "good", "rent", 50, 70, 180),
    ("sports", "new", "sell", 76, 92, 2500),
    ("sports", "like_new", "sell", 70, 84, 1850),
    ("sports", "good", "sell", 61, 73, 1150),
    ("sports", "fair", "sell", 38, 58, 620),
    ("sports", "good", "rent", 59, 72, 210),
    ("other", "new", "sell", 52, 90, 1200),
    ("other", "like_new", "sell", 50, 84, 850),
    ("other", "good", "sell", 44, 72, 580),
    ("other", "fair", "sell", 31, 57, 320),
    ("other", "good", "rent", 45, 70, 100),
]


def _features(category, condition, transaction_type, demand_score, quality_score):
    return [
        CATEGORY.get(category, CATEGORY["other"]),
        CONDITION.get(condition, CONDITION["good"]),
        TRANSACTION.get(transaction_type, 0),
        max(0, min(100, float(demand_score))),
        max(0, min(100, float(quality_score))),
    ]


@lru_cache(maxsize=1)
def _trained_model():
    x_train = np.asarray([_features(*row[:5]) for row in TRAINING_ROWS], dtype=float)
    y_train = np.asarray([row[5] for row in TRAINING_ROWS], dtype=float)
    model = RandomForestRegressor(
        n_estimators=160,
        max_depth=7,
        min_samples_leaf=1,
        random_state=42,
    )
    model.fit(x_train, y_train)
    return model


def predict_fair_price(
    category,
    condition,
    transaction_type="sell",
    demand_score=50,
    quality_score=72,
    comparable_prices=None,
):
    """Return a rounded fair price and an explainable confidence value."""
    if transaction_type in {"borrow", "donate"}:
        return {"price": 0.0, "confidence": 1.0, "method": "community exchange"}

    prediction = float(
        _trained_model().predict(
            [_features(category, condition, transaction_type, demand_score, quality_score)]
        )[0]
    )
    comparable_prices = [float(p) for p in (comparable_prices or []) if float(p) >= 0]
    if comparable_prices:
        market_average = float(np.median(comparable_prices))
        prediction = prediction * 0.68 + market_average * 0.32
        confidence = min(0.96, 0.76 + len(comparable_prices) * 0.025)
        method = "random forest + comparable listings"
    else:
        confidence = 0.72
        method = "random forest baseline"

    rounded = round(max(0, prediction) / 10) * 10
    return {"price": float(rounded), "confidence": round(confidence, 2), "method": method}
