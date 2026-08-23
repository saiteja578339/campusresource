"""Retrieval-based AI assistant for campus marketplace questions and discovery."""

import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


FAQ_KNOWLEDGE = [
    {
        "intent": "greeting",
        "questions": "hello hi hey good morning campus assistant help",
        "reply": "Hello! I am the CampusLoop AI Assistant. I can help you find items, create listings, understand fair prices, make a demo payment, and exchange safely.",
    },
    {
        "intent": "create_listing",
        "questions": "how to sell list item create listing upload product rent donate borrow",
        "reply": "Choose ‘List an item’, enter the category, condition, exchange type, price, location, description, and optional photo. The Python AI services then suggest a fair price and run image, text, and fraud checks.",
    },
    {
        "intent": "payment",
        "questions": "payment pay checkout upi card wallet net banking reserve purchase transaction",
        "reply": "Open an active listing and select ‘Pay / Reserve’. Choose UPI, card, wallet, or net banking. This academic project records a simulated payment and never charges real money.",
    },
    {
        "intent": "payment_history",
        "questions": "payment history receipt transaction id previous payments purchased orders",
        "reply": "Open the Payments page from the navigation menu to view transaction references, methods, amounts, and payment status.",
    },
    {
        "intent": "fair_price",
        "questions": "fair price predicted price random forest value expensive cheap pricing",
        "reply": "The fair-price feature uses Random Forest regression with category, condition, exchange type, demand, and image quality. When comparable listings exist, their median price is blended into the result.",
    },
    {
        "intent": "safety",
        "questions": "safe scam fraud risky suspicious trust moderation advance payment whatsapp",
        "reply": "Keep communication and the demo payment inside CampusLoop. Check the seller trust score and AI fraud score, avoid advance-payment pressure, and report listings marked for review.",
    },
    {
        "intent": "search",
        "questions": "how search find item recommendation discover resource book calculator laptop",
        "reply": "Use natural words in Discover, such as ‘affordable Python book’ or ‘calculator for lab’. TF-IDF and cosine similarity rank listings by text relevance.",
    },
    {
        "intent": "cnn",
        "questions": "image photo cnn mobilenet object label quality tensorflow keras",
        "reply": "Uploaded photos are resized to 224×224 and analyzed with MobileNetV2 when TensorFlow is available. Pillow also checks brightness and contrast for a photo-quality score.",
    },
    {
        "intent": "contact",
        "questions": "contact seller message chat negotiate pickup meet exchange",
        "reply": "Open the listing and use the seller message form. Confirm availability and arrange pickup at a safe campus location.",
    },
]


def _listing_document(listing):
    return " ".join(
        str(value or "")
        for value in (
            listing.title,
            listing.description,
            listing.category,
            listing.get_category_display(),
            listing.condition,
            listing.transaction_type,
            listing.course_tags,
            listing.location,
        )
    ).lower()


def _budget_from_message(message):
    match = re.search(r"(?:under|below|less than|within)\s*(?:rs\.?|₹)?\s*([0-9][0-9,]*)", message)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def assistant_reply(message, listings=None, limit=3):
    """Return an explainable FAQ or listing-retrieval response."""
    normalized = " ".join((message or "").lower().split())
    if not normalized:
        return {
            "reply": "Please type a question, for example: ‘Find a calculator under ₹800’.",
            "intent": "empty",
            "confidence": 0.0,
            "listings": [],
        }

    listings = list(listings or [])
    faq_documents = [item["questions"] for item in FAQ_KNOWLEDGE]
    listing_documents = [_listing_document(listing) for listing in listings]
    documents = [normalized, *faq_documents, *listing_documents]
    try:
        matrix = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), min_df=1, sublinear_tf=True
        ).fit_transform(documents)
        similarities = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    except ValueError:
        similarities = [0.0] * (len(documents) - 1)

    faq_scores = similarities[: len(FAQ_KNOWLEDGE)]
    listing_scores = similarities[len(FAQ_KNOWLEDGE) :]
    best_faq_index = int(max(range(len(faq_scores)), key=lambda index: faq_scores[index]))
    best_faq_score = float(faq_scores[best_faq_index])

    budget = _budget_from_message(normalized)
    ranked_listings = []
    for listing, score in sorted(
        zip(listings, listing_scores), key=lambda item: float(item[1]), reverse=True
    ):
        if float(score) <= 0:
            continue
        if budget is not None and float(listing.price) > budget:
            continue
        ranked_listings.append(
            {
                "id": listing.pk,
                "title": listing.title,
                "price": float(listing.price),
                "transaction_type": listing.get_transaction_type_display(),
                "score": round(float(score), 3),
            }
        )
        if len(ranked_listings) >= limit:
            break

    discovery_words = {
        "find", "show", "need", "looking", "book", "books", "calculator", "laptop",
        "electronics", "lab", "hostel", "sports", "rent", "borrow", "donate",
    }
    wants_discovery = bool(discovery_words.intersection(normalized.split()))
    if wants_discovery and ranked_listings:
        budget_note = f" within your ₹{budget:.0f} budget" if budget is not None else ""
        return {
            "reply": f"I found {len(ranked_listings)} relevant campus listing(s){budget_note}. Open a result to view its AI price and safety details.",
            "intent": "listing_search",
            "confidence": round(max(item["score"] for item in ranked_listings), 3),
            "listings": ranked_listings,
        }

    if best_faq_score >= 0.08:
        selected = FAQ_KNOWLEDGE[best_faq_index]
        return {
            "reply": selected["reply"],
            "intent": selected["intent"],
            "confidence": round(best_faq_score, 3),
            "listings": ranked_listings if selected["intent"] == "search" else [],
        }

    return {
        "reply": "I can help with listing creation, item search, fair-price prediction, payments, fraud safety, image analysis, or contacting a seller. Please ask using a few specific words.",
        "intent": "fallback",
        "confidence": round(best_faq_score, 3),
        "listings": [],
    }
