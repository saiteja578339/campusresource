"""Marketplace pages and JSON endpoints."""

import json
import uuid
from decimal import Decimal

from django.contrib import messages as django_messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Avg, Count, F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .ai import (
    analyze_listing_image,
    analyze_text,
    assistant_reply,
    detect_fraud,
    generate_listing_draft,
    predict_fair_price,
    recommend_listings,
    semantic_search,
)
from .forms import ListingForm, MessageForm, RegisterForm, ReviewForm
from .models import Favorite, Listing, Message, Notification, Payment, Review


def _active_listings():
    return Listing.objects.filter(status="active", moderation_status="approved").select_related(
        "seller", "seller__profile"
    )


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def home(request):
    listings_qs = _active_listings()
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    transaction = request.GET.get("type", "").strip()
    sort = request.GET.get("sort", "recommended")

    if category:
        listings_qs = listings_qs.filter(category=category)
    if transaction:
        listings_qs = listings_qs.filter(transaction_type=transaction)

    listings = list(listings_qs)
    search_scores = {}
    if query:
        ranked = semantic_search(query, listings)
        listings = [item for item, _ in ranked]
        search_scores = {item.pk: score for item, score in ranked}
    elif sort == "price_low":
        listings.sort(key=lambda item: float(item.price))
    elif sort == "popular":
        listings.sort(key=lambda item: (item.demand_score, item.views), reverse=True)

    recommendations = []
    if request.user.is_authenticated:
        recommendation_pool = [item for item in _active_listings() if item.seller_id != request.user.id]
        recommendations = recommend_listings(request.user, recommendation_pool, limit=5)

    stats = {
        "active": _active_listings().count(),
        "students": Listing.objects.values("seller").distinct().count(),
        "exchanges": Payment.objects.filter(status="captured").count(),
        "saved": Payment.objects.filter(status="captured").aggregate(total=Sum("amount"))["total"] or 0,
    }
    context = {
        "listings": listings,
        "query": query,
        "selected_category": category,
        "selected_transaction": transaction,
        "selected_sort": sort,
        "search_scores": search_scores,
        "recommendations": recommendations,
        "stats": stats,
        "categories": Listing.CATEGORY_CHOICES,
        "transaction_types": Listing.TRANSACTION_CHOICES,
    }
    return render(request, "marketplace/home.html", context)


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        django_messages.success(request, "Welcome! Your campus marketplace account is ready.")
        return redirect("home")
    return render(request, "marketplace/register.html", {"form": form})


@login_required
def listing_create(request):
    form = ListingForm(request.POST or None, request.FILES or None)
    ai_preview = None
    if request.method == "POST" and form.is_valid():
        listing = form.save(commit=False)
        listing.seller = request.user
        comparable_prices = list(
            Listing.objects.filter(
                category=listing.category,
                condition=listing.condition,
                status__in=["active", "completed"],
            ).values_list("price", flat=True)[:30]
        )
        prediction = predict_fair_price(
            listing.category,
            listing.condition,
            listing.transaction_type,
            listing.demand_score,
            72,
            comparable_prices,
        )
        listing.predicted_price = Decimal(str(prediction["price"]))
        listing.save()

        if listing.image:
            image_result = analyze_listing_image(listing.image.path)
            listing.image_quality_score = image_result["quality_score"]
            listing.cnn_labels = image_result["labels"]
            prediction = predict_fair_price(
                listing.category,
                listing.condition,
                listing.transaction_type,
                listing.demand_score,
                listing.image_quality_score,
                comparable_prices,
            )
            listing.predicted_price = Decimal(str(prediction["price"]))

        duplicate_count = Listing.objects.filter(
            seller=request.user, title__iexact=listing.title, status="active"
        ).exclude(pk=listing.pk).count()
        fraud = detect_fraud(
            listing.title,
            listing.description,
            listing.price,
            listing.predicted_price,
            comparable_prices,
            duplicate_count,
        )
        text_result = analyze_text(f"{listing.title} {listing.description}")
        listing.fraud_score = fraud["score"]
        listing.fraud_reasons = fraud["reasons"]
        listing.moderation_status = (
            "blocked"
            if "blocked" in {fraud["status"], text_result["moderation_status"]}
            else "review"
            if "review" in {fraud["status"], text_result["moderation_status"]}
            else "approved"
        )
        listing.status = "blocked" if listing.moderation_status == "blocked" else "active"
        listing.save()

        Notification.objects.create(
            user=request.user,
            title="Listing analysis complete",
            body=f"{listing.title} received a fraud score of {listing.fraud_score}/100 and a suggested price of ₹{listing.predicted_price:.0f}.",
            kind="ai",
        )
        if listing.moderation_status == "approved":
            django_messages.success(request, "Listing published after AI safety checks.")
        else:
            django_messages.warning(request, "Listing saved and sent for moderation review.")
        return redirect("listing_detail", listing_id=listing.pk)
    return render(
        request,
        "marketplace/listing_form.html",
        {"form": form, "ai_preview": ai_preview},
    )


def listing_detail(request, listing_id):
    listing = get_object_or_404(
        Listing.objects.select_related("seller", "seller__profile"), pk=listing_id
    )
    Listing.objects.filter(pk=listing.pk).update(views=F("views") + 1)
    listing.refresh_from_db(fields=["views"])
    related_pool = _active_listings().filter(category=listing.category).exclude(pk=listing.pk)
    if request.user.is_authenticated:
        related = [item for item, _ in recommend_listings(request.user, related_pool, limit=4)]
    else:
        related = list(related_pool[:4])
    is_favorite = (
        request.user.is_authenticated
        and Favorite.objects.filter(user=request.user, listing=listing).exists()
    )
    reviews = listing.reviews.filter(moderation_status="approved").select_related("author")
    review_summary = reviews.aggregate(average=Avg("rating"), count=Count("id"))
    context = {
        "listing": listing,
        "related": related,
        "is_favorite": is_favorite,
        "message_form": MessageForm(),
        "review_form": ReviewForm(),
        "reviews": reviews,
        "review_summary": review_summary,
    }
    return render(request, "marketplace/listing_detail.html", context)


@login_required
@require_POST
def toggle_favorite(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, listing=listing)
    if not created:
        favorite.delete()
        django_messages.info(request, "Removed from saved items.")
    else:
        django_messages.success(request, "Saved for later.")
    next_url = request.POST.get("next", "").strip()
    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect("listing_detail", listing_id=listing.pk)


@login_required
@require_POST
def send_message(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    form = MessageForm(request.POST)
    if request.user == listing.seller:
        django_messages.error(request, "You cannot send a message to yourself.")
    elif form.is_valid():
        text_result = analyze_text(form.cleaned_data["body"])
        chat_message = form.save(commit=False)
        chat_message.listing = listing
        chat_message.sender = request.user
        chat_message.receiver = listing.seller
        chat_message.sentiment = text_result["sentiment"]
        chat_message.flagged = text_result["moderation_status"] != "approved"
        chat_message.save()
        Notification.objects.create(
            user=listing.seller,
            title="New message",
            body=f"{request.user.get_full_name() or request.user.username} messaged you about {listing.title}.",
            kind="chat",
        )
        django_messages.success(request, "Message sent securely.")
    else:
        django_messages.error(request, "Please enter a valid message.")
    return redirect("listing_detail", listing_id=listing.pk)


@login_required
@require_POST
def demo_checkout(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id, status="active")
    if listing.seller == request.user:
        django_messages.error(request, "You cannot purchase your own listing.")
        return redirect("listing_detail", listing_id=listing.pk)
    method = request.POST.get("method", "upi")
    valid_methods = {choice[0] for choice in Payment.METHOD_CHOICES}
    if method not in valid_methods:
        method = "upi"
    payment = Payment.objects.create(
        transaction_ref=f"DEMO-{uuid.uuid4().hex[:12].upper()}",
        listing=listing,
        buyer=request.user,
        amount=listing.price,
        method=method,
        status="captured",
    )
    listing.status = "reserved"
    listing.save(update_fields=["status", "updated_at"])
    Notification.objects.bulk_create(
        [
            Notification(
                user=request.user,
                title="Demo payment successful",
                body=f"Transaction {payment.transaction_ref} was captured for {listing.title}.",
                kind="payment",
            ),
            Notification(
                user=listing.seller,
                title="Your item has a buyer",
                body=f"{request.user.get_full_name() or request.user.username} reserved {listing.title}.",
                kind="payment",
            ),
        ]
    )
    django_messages.success(request, f"Demo payment successful: {payment.transaction_ref}")
    return redirect("dashboard")


@login_required
def payment_history(request):
    payments = request.user.payments.select_related("listing", "listing__seller")
    received = Payment.objects.filter(listing__seller=request.user).select_related(
        "listing", "buyer"
    )
    context = {
        "payments": payments,
        "received_payments": received,
        "total_paid": payments.filter(status="captured").aggregate(total=Sum("amount"))["total"] or 0,
        "total_received": received.filter(status="captured").aggregate(total=Sum("amount"))["total"] or 0,
    }
    return render(request, "marketplace/payments.html", context)


@login_required
@require_POST
def add_review(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    if listing.seller == request.user:
        django_messages.error(request, "You cannot review your own listing.")
        return redirect("listing_detail", listing_id=listing.pk)
    form = ReviewForm(request.POST)
    if form.is_valid():
        text_result = analyze_text(form.cleaned_data["body"])
        Review.objects.update_or_create(
            listing=listing,
            author=request.user,
            defaults={
                "seller": listing.seller,
                "rating": form.cleaned_data["rating"],
                "body": form.cleaned_data["body"],
                "sentiment": text_result["sentiment"],
                "moderation_status": text_result["moderation_status"],
            },
        )
        django_messages.success(request, "Your review was analyzed and saved.")
    return redirect("listing_detail", listing_id=listing.pk)


@login_required
def dashboard(request):
    user_listings = request.user.listings.all()
    context = {
        "user_listings": user_listings,
        "favorites": Listing.objects.filter(favorited_by__user=request.user).select_related("seller")[:12],
        "payments": request.user.payments.select_related("listing")[:10],
        "notifications": request.user.notifications.all()[:12],
        "stats": {
            "listings": user_listings.count(),
            "views": user_listings.aggregate(total=Sum("views"))["total"] or 0,
            "sales": Payment.objects.filter(listing__seller=request.user, status="captured").count(),
            "trust": request.user.profile.trust_score,
        },
    }
    return render(request, "marketplace/dashboard.html", context)


@login_required
def message_center(request):
    chat_messages = Message.objects.filter(Q(sender=request.user) | Q(receiver=request.user)).select_related(
        "sender", "receiver", "listing"
    )
    request.user.received_messages.filter(is_read=False).update(is_read=True)
    return render(request, "marketplace/messages.html", {"chat_messages": chat_messages})


def ai_lab(request):
    models = [
        {
            "name": "Fair Price Predictor",
            "model": "Random Forest Regressor",
            "input": "Category, condition, transaction type, demand and image quality",
            "output": "Suggested campus price with confidence",
        },
        {
            "name": "Smart Search & Recommendations",
            "model": "TF-IDF + Cosine Similarity",
            "input": "Listing text, course tags and student interests",
            "output": "Semantic relevance and personalized ranking",
        },
        {
            "name": "Fraud Detector",
            "model": "Isolation Forest + Explainable Rules",
            "input": "Price deviation, duplicates and suspicious language",
            "output": "0-100 risk score and moderation decision",
        },
        {
            "name": "Image Analyzer",
            "model": "MobileNetV2 CNN (ImageNet)",
            "input": "224×224 uploaded product image",
            "output": "Object labels, confidence and photo-quality score",
        },
        {
            "name": "Text Safety & Sentiment",
            "model": "TF-IDF + Logistic Regression",
            "input": "Descriptions, chats and reviews",
            "output": "Sentiment label and moderation flags",
        },
        {
            "name": "Campus AI Assistant",
            "model": "TF-IDF + Cosine Retrieval",
            "input": "Student questions and active listing text",
            "output": "FAQ guidance or ranked campus listings",
        },
    ]
    return render(request, "marketplace/ai_lab.html", {"ai_models": models})


def ai_assistant(request):
    history = request.session.get("assistant_history", [])
    if request.method == "POST":
        data = _json_body(request) if request.content_type == "application/json" else request.POST
        message = str(data.get("message", "")).strip()
        if not message:
            return JsonResponse({"error": "Please enter a question."}, status=400)
        result = assistant_reply(message, _active_listings()[:120])
        history.extend(
            [
                {"role": "user", "text": message},
                {"role": "assistant", "text": result["reply"]},
            ]
        )
        request.session["assistant_history"] = history[-12:]
        return JsonResponse(result)
    return render(request, "marketplace/assistant.html", {"assistant_history": history})


def _is_moderator(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(_is_moderator)
def moderation_panel(request):
    review_queue = Listing.objects.filter(moderation_status__in=["review", "blocked"]).select_related(
        "seller"
    )
    return render(request, "marketplace/moderation.html", {"review_queue": review_queue})


@user_passes_test(_is_moderator)
@require_POST
def moderate_listing(request, listing_id, action):
    listing = get_object_or_404(Listing, pk=listing_id)
    if action == "approve":
        listing.moderation_status = "approved"
        listing.status = "active"
    elif action == "block":
        listing.moderation_status = "blocked"
        listing.status = "blocked"
    else:
        django_messages.error(request, "Unknown moderation action.")
        return redirect("moderation_panel")
    listing.save()
    Notification.objects.create(
        user=listing.seller,
        title="Moderation update",
        body=f"Your listing {listing.title} was {listing.moderation_status}.",
        kind="moderation",
    )
    django_messages.success(request, "Moderation decision saved.")
    return redirect("moderation_panel")


@login_required
@require_POST
def read_notification(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return redirect("dashboard")


@require_POST
def api_generate_draft(request):
    data = _json_body(request)
    result = generate_listing_draft(
        data.get("category", "other"),
        data.get("condition", "good"),
        data.get("transaction_type", "sell"),
        data.get("location", "MVSR Campus"),
        data.get("keywords", ""),
    )
    return JsonResponse(result)


@require_POST
def api_predict_price(request):
    data = _json_body(request)
    comparables = list(
        Listing.objects.filter(category=data.get("category", "other"), status__in=["active", "completed"])
        .values_list("price", flat=True)[:30]
    )
    result = predict_fair_price(
        data.get("category", "other"),
        data.get("condition", "good"),
        data.get("transaction_type", "sell"),
        data.get("demand_score", 50),
        data.get("quality_score", 72),
        comparables,
    )
    return JsonResponse(result)
