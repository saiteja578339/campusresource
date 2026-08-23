"""Explainable fraud detection using rules and Isolation Forest anomalies."""

import re

import numpy as np
from sklearn.ensemble import IsolationForest

RISKY_PATTERNS = {
    r"\bpay\s*(first|advance)\b": "Requests advance payment",
    r"\boutside\s+(campus|app)\b": "Attempts to move transaction outside the platform",
    r"\bwhatsapp\s+only\b": "Requests WhatsApp-only communication",
    r"\bno\s+(refund|return)\b": "Uses a no-refund pressure phrase",
    r"\btoo\s+urgent\b": "Uses unusual urgency",
    r"\bgift\s*card\b": "Requests an unsafe payment method",
}


def detect_fraud(title, description, price, predicted_price, comparable_prices=None, duplicate_count=0):
    text = f"{title} {description}".lower()
    score = 0
    reasons = []

    for pattern, reason in RISKY_PATTERNS.items():
        if re.search(pattern, text):
            score += 18
            reasons.append(reason)

    predicted_price = max(float(predicted_price or 0), 1.0)
    deviation = abs(float(price) - predicted_price) / predicted_price
    if deviation > 1.25:
        score += 34
        reasons.append("Price is far outside the ML-predicted range")
    elif deviation > 0.65:
        score += 18
        reasons.append("Price differs significantly from the predicted range")

    comparable_prices = [float(p) for p in (comparable_prices or []) if float(p) > 0]
    if len(comparable_prices) >= 8 and float(price) > 0:
        training = np.asarray(comparable_prices, dtype=float).reshape(-1, 1)
        detector = IsolationForest(contamination="auto", random_state=42)
        detector.fit(training)
        anomaly = detector.predict([[float(price)]])[0]
        if anomaly == -1:
            score += 22
            reasons.append("Isolation Forest detected an unusual market price")

    if duplicate_count:
        score += min(28, duplicate_count * 14)
        reasons.append("Seller already has a similar active listing")

    if len(description.strip()) < 30:
        score += 9
        reasons.append("Description contains too little verifiable detail")

    score = min(100, score)
    status = "blocked" if score >= 75 else "review" if score >= 42 else "approved"
    return {"score": score, "status": status, "reasons": reasons}
