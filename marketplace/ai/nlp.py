"""Small, reproducible NLP pipeline for descriptions, sentiment and moderation."""

import re
from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

SENTIMENT_EXAMPLES = [
    ("excellent condition and very helpful seller", "positive"),
    ("smooth exchange and product works perfectly", "positive"),
    ("good price and quick campus pickup", "positive"),
    ("clean item exactly as described", "positive"),
    ("average condition but usable", "neutral"),
    ("the transaction was okay", "neutral"),
    ("item is available for pickup", "neutral"),
    ("normal wear for an old book", "neutral"),
    ("broken item and misleading description", "negative"),
    ("seller never responded and wasted time", "negative"),
    ("terrible quality and unfair price", "negative"),
    ("scam do not buy from this person", "negative"),
]

BLOCKED_TERMS = {"weapon", "drugs", "fake certificate", "stolen", "exam paper leak"}
ABUSIVE_TERMS = {"idiot", "stupid", "hate", "fraudster"}


@lru_cache(maxsize=1)
def _sentiment_model():
    model = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("classifier", LogisticRegression(max_iter=500, random_state=42)),
        ]
    )
    model.fit([row[0] for row in SENTIMENT_EXAMPLES], [row[1] for row in SENTIMENT_EXAMPLES])
    return model


def analyze_text(text):
    normalized = " ".join((text or "").lower().split())
    sentiment = str(_sentiment_model().predict([normalized or "neutral"])[0])
    blocked = sorted(term for term in BLOCKED_TERMS if term in normalized)
    abusive = sorted(term for term in ABUSIVE_TERMS if re.search(rf"\b{re.escape(term)}\b", normalized))
    status = "blocked" if blocked else "review" if abusive else "approved"
    return {
        "sentiment": sentiment,
        "moderation_status": status,
        "flags": [*blocked, *abusive],
    }


def generate_listing_draft(category, condition, transaction_type, location, keywords=""):
    category_label = category.replace("_", " ").title()
    condition_label = condition.replace("_", " ").title()
    action = {
        "sell": "available for sale",
        "rent": "available for short-term rent",
        "borrow": "available to borrow",
        "donate": "available as a free donation",
    }.get(transaction_type, "available")
    cleaned_keywords = ", ".join(
        token.strip() for token in re.split(r"[,;]", keywords or "") if token.strip()
    )
    title = f"{condition_label} {category_label} for Campus Students"
    description = (
        f"This {category_label.lower()} item is in {condition_label.lower()} condition and is {action}. "
        f"It is suitable for students looking for a reliable, affordable campus resource. "
        f"Pickup is available near {location or 'the main campus'}."
    )
    if cleaned_keywords:
        description += f" Key details: {cleaned_keywords}."
    description += " Please message through the platform to confirm availability and pickup time."
    tags = [category_label, condition_label, transaction_type.title(), "Campus"]
    return {"title": title, "description": description, "tags": tags}
