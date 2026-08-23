"""Database models for marketplace, chat, payments and trust features."""

import uuid

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


def short_id():
    return uuid.uuid4().hex[:12]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    course = models.CharField(max_length=80, blank=True)
    year = models.CharField(max_length=20, blank=True)
    interests = models.JSONField(default=list, blank=True)
    location = models.CharField(max_length=100, default="MVSR Campus")
    trust_score = models.PositiveSmallIntegerField(default=80)
    points = models.PositiveIntegerField(default=0)
    email_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Listing(models.Model):
    CATEGORY_CHOICES = [
        ("books", "Books"),
        ("electronics", "Electronics"),
        ("lab", "Lab Equipment"),
        ("hostel", "Hostel Essentials"),
        ("sports", "Sports"),
        ("other", "Other"),
    ]
    CONDITION_CHOICES = [
        ("new", "New"),
        ("like_new", "Like New"),
        ("good", "Good"),
        ("fair", "Fair"),
        ("used", "Used"),
    ]
    TRANSACTION_CHOICES = [
        ("sell", "Sell"),
        ("rent", "Rent"),
        ("borrow", "Borrow"),
        ("donate", "Donate"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("reserved", "Reserved"),
        ("completed", "Completed"),
        ("blocked", "Blocked"),
    ]
    MODERATION_CHOICES = [
        ("approved", "Approved"),
        ("review", "Needs Review"),
        ("blocked", "Blocked"),
    ]

    id = models.CharField(primary_key=True, max_length=12, default=short_id, editable=False)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="listings")
    title = models.CharField(max_length=120)
    description = models.TextField(max_length=1000)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    condition = models.CharField(max_length=30, choices=CONDITION_CHOICES)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    predicted_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    location = models.CharField(max_length=100, default="MVSR Campus")
    course_tags = models.CharField(max_length=250, blank=True)
    image = models.ImageField(upload_to="listings/", blank=True, null=True)
    image_url = models.URLField(blank=True)
    cnn_labels = models.JSONField(default=list, blank=True)
    image_quality_score = models.PositiveSmallIntegerField(default=72)
    demand_score = models.PositiveSmallIntegerField(default=50)
    fraud_score = models.PositiveSmallIntegerField(default=0)
    fraud_reasons = models.JSONField(default=list, blank=True)
    moderation_status = models.CharField(
        max_length=20, choices=MODERATION_CHOICES, default="approved"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["moderation_status", "created_at"]),
        ]

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        return self.image_url

    def __str__(self):
        return self.title


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "listing"], name="unique_favorite")
        ]


class Message(models.Model):
    id = models.CharField(primary_key=True, max_length=12, default=short_id, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="chat_messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    body = models.CharField(max_length=700)
    sentiment = models.CharField(max_length=20, default="neutral")
    flagged = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class Payment(models.Model):
    METHOD_CHOICES = [
        ("upi", "UPI"),
        ("card", "Card"),
        ("wallet", "Wallet"),
        ("netbanking", "Net Banking"),
    ]
    STATUS_CHOICES = [
        ("created", "Created"),
        ("captured", "Captured"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    transaction_ref = models.CharField(max_length=30, unique=True, default=short_id)
    listing = models.ForeignKey(Listing, on_delete=models.PROTECT, related_name="payments")
    buyer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Review(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews_written")
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews_received")
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    body = models.CharField(max_length=500)
    sentiment = models.CharField(max_length=20, default="neutral")
    moderation_status = models.CharField(max_length=20, default="approved")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["listing", "author"], name="one_review_per_listing_user"
            )
        ]


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=120)
    body = models.CharField(max_length=350)
    kind = models.CharField(max_length=30, default="system")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
