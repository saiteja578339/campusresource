"""MobileNetV2 CNN image analysis with a deterministic Pillow fallback."""

from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageStat


@lru_cache(maxsize=1)
def _mobilenet_components():
    """Load ImageNet MobileNetV2 only when TensorFlow is installed."""
    try:
        from tensorflow.keras.applications.mobilenet_v2 import (
            MobileNetV2,
            decode_predictions,
            preprocess_input,
        )

        return MobileNetV2(weights="imagenet"), preprocess_input, decode_predictions
    except (ImportError, OSError, ValueError):
        return None


def _quality_score(image):
    gray = image.convert("L").resize((224, 224))
    contrast = ImageStat.Stat(gray).stddev[0]
    brightness = ImageStat.Stat(gray).mean[0]
    brightness_penalty = abs(brightness - 130) / 130
    score = 58 + min(30, contrast * 0.55) - brightness_penalty * 20
    return int(max(25, min(98, round(score))))


def analyze_listing_image(image_path):
    """Return CNN labels, confidence and a photo-quality score."""
    if not image_path or not Path(image_path).exists():
        return {
            "provider": "none",
            "labels": [],
            "confidence": 0.0,
            "quality_score": 72,
            "summary": "No uploaded image was available for CNN analysis.",
        }

    image = Image.open(image_path).convert("RGB")
    quality_score = _quality_score(image)
    components = _mobilenet_components()
    if components is None:
        return {
            "provider": "Pillow fallback",
            "labels": [],
            "confidence": 0.42,
            "quality_score": quality_score,
            "summary": "TensorFlow is not installed; image brightness and contrast were checked locally.",
        }

    model, preprocess_input, decode_predictions = components
    batch = np.expand_dims(np.asarray(image.resize((224, 224)), dtype=np.float32), axis=0)
    predictions = model.predict(preprocess_input(batch), verbose=0)
    decoded = decode_predictions(predictions, top=3)[0]
    labels = [label.replace("_", " ") for _, label, _ in decoded]
    confidence = float(decoded[0][2])
    return {
        "provider": "MobileNetV2 (ImageNet)",
        "labels": labels,
        "confidence": round(confidence, 3),
        "quality_score": quality_score,
        "summary": f"MobileNetV2 recognized: {', '.join(labels)}.",
    }
