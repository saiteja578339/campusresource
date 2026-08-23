from django.contrib import admin

from .models import Favorite, Listing, Message, Notification, Payment, Profile, Review


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "seller",
        "category",
        "transaction_type",
        "price",
        "moderation_status",
        "status",
    )
    list_filter = ("category", "condition", "transaction_type", "moderation_status", "status")
    search_fields = ("title", "description", "seller__username")


admin.site.register(Profile)
admin.site.register(Favorite)
admin.site.register(Message)
admin.site.register(Payment)
admin.site.register(Review)
admin.site.register(Notification)
