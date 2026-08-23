"""TF-IDF semantic search and hybrid recommendation ranking."""

from datetime import timezone
from math import exp

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _document(listing):
    return " ".join(
        str(value or "")
        for value in (
            listing.title,
            listing.description,
            listing.category,
            listing.get_category_display(),
            listing.course_tags,
            listing.condition,
            listing.transaction_type,
            listing.location,
        )
    ).lower()


def _semantic_scores(query, listings):
    if not listings:
        return np.asarray([])
    query = (query or "campus student useful affordable").strip().lower()
    documents = [_document(listing) for listing in listings]
    try:
        matrix = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), min_df=1, sublinear_tf=True
        ).fit_transform([query, *documents])
        return cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    except ValueError:
        return np.zeros(len(listings))


def semantic_search(query, listings, limit=24):
    """Rank marketplace items by semantic similarity to a natural-language query."""
    listings = list(listings)
    scores = _semantic_scores(query, listings)
    ranked = sorted(zip(listings, scores), key=lambda item: item[1], reverse=True)
    return [(listing, round(float(score), 4)) for listing, score in ranked[:limit] if score > 0]


def recommend_listings(user, listings, limit=8):
    """Blend content relevance, demand, affordability and freshness."""
    listings = list(listings)
    profile = getattr(user, "profile", None)
    interests = " ".join(getattr(profile, "interests", []) or [])
    course = getattr(profile, "course", "") if profile else ""
    year = getattr(profile, "year", "") if profile else ""
    query = f"{interests} {course} {year} student campus affordable"
    semantic = _semantic_scores(query, listings)

    scored = []
    now = __import__("datetime").datetime.now(timezone.utc)
    for listing, similarity in zip(listings, semantic):
        age_days = max(0, (now - listing.created_at).total_seconds() / 86400)
        freshness = exp(-age_days / 30)
        affordability = 1.0 if float(listing.price) <= 1000 else max(0.1, 1000 / float(listing.price))
        demand = listing.demand_score / 100
        trust = getattr(listing.seller.profile, "trust_score", 70) / 100
        score = 0.50 * float(similarity) + 0.17 * freshness + 0.14 * affordability + 0.11 * demand + 0.08 * trust
        scored.append((listing, round(score, 4)))

    return sorted(scored, key=lambda item: item[1], reverse=True)[:limit]
