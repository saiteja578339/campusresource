import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .ai import (
    analyze_listing_image,
    assistant_reply,
    detect_fraud,
    generate_listing_draft,
    predict_fair_price,
)
from .models import Listing, Payment


class AiPipelineTests(TestCase):
    def test_price_predictor_returns_price_and_confidence(self):
        result = predict_fair_price("books", "good", "sell", 70, 80)
        self.assertGreater(result["price"], 0)
        self.assertGreater(result["confidence"], 0.5)

    def test_community_exchange_has_zero_price(self):
        result = predict_fair_price("books", "good", "donate", 50, 70)
        self.assertEqual(result["price"], 0)

    def test_fraud_detector_explains_risky_listing(self):
        result = detect_fraud(
            "Urgent laptop",
            "Pay advance first and contact WhatsApp only. No refund.",
            500,
            18000,
        )
        self.assertGreaterEqual(result["score"], 42)
        self.assertTrue(result["reasons"])

    def test_nlp_draft_is_complete(self):
        draft = generate_listing_draft("electronics", "good", "sell", "IT Block", "calculator")
        self.assertIn("Electronics", draft["title"])
        self.assertIn("IT Block", draft["description"])

    def test_cnn_fallback_handles_missing_image(self):
        result = analyze_listing_image("/does/not/exist.jpg")
        self.assertEqual(result["provider"], "none")

    def test_chatbot_explains_payment_option(self):
        result = assistant_reply("How can I pay using UPI?")
        self.assertEqual(result["intent"], "payment")
        self.assertIn("simulated payment", result["reply"])


class MarketplaceViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("tester", "tester@mvsrec.edu.in", "StrongPass123")
        self.seller = User.objects.create_user("seller", "seller@mvsrec.edu.in", "StrongPass123")
        self.listing = Listing.objects.create(
            seller=self.seller,
            title="Python Project Book",
            description="A clean practical Python project book for engineering students.",
            category="books",
            condition="good",
            transaction_type="sell",
            price=500,
            predicted_price=520,
            location="Library",
        )

    def test_home_page_lists_approved_items(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Project Book")

    def test_semantic_search_endpoint_page(self):
        response = self.client.get(reverse("home"), {"q": "python engineering book"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Project Book")

    def test_price_api(self):
        response = self.client.post(
            reverse("api_predict_price"),
            data=json.dumps(
                {
                    "category": "books",
                    "condition": "good",
                    "transaction_type": "sell",
                    "demand_score": 70,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("price", response.json())

    def test_authenticated_user_can_favorite(self):
        self.client.login(username="tester", password="StrongPass123")
        response = self.client.post(reverse("toggle_favorite", args=[self.listing.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.user.favorites.filter(listing=self.listing).exists())

    def test_ai_assistant_can_find_a_listing(self):
        response = self.client.post(
            reverse("ai_assistant"),
            {"message": "Find a Python book under ₹600"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "listing_search")
        self.assertEqual(response.json()["listings"][0]["id"], self.listing.pk)

    def test_payment_option_records_transaction_and_reserves_item(self):
        self.client.login(username="tester", password="StrongPass123")
        response = self.client.post(
            reverse("demo_checkout", args=[self.listing.pk]),
            {"method": "upi"},
        )
        self.assertEqual(response.status_code, 302)
        payment = Payment.objects.get(buyer=self.user, listing=self.listing)
        self.assertEqual(payment.method, "upi")
        self.assertEqual(payment.status, "captured")
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, "reserved")

    def test_payment_history_page_is_visible(self):
        self.client.login(username="tester", password="StrongPass123")
        response = self.client.get(reverse("payment_history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Payments and reservations")
