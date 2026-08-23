from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("listing/new/", views.listing_create, name="listing_create"),
    path("listing/<str:listing_id>/", views.listing_detail, name="listing_detail"),
    path("listing/<str:listing_id>/favorite/", views.toggle_favorite, name="toggle_favorite"),
    path("listing/<str:listing_id>/message/", views.send_message, name="send_message"),
    path("listing/<str:listing_id>/checkout/", views.demo_checkout, name="demo_checkout"),
    path("payments/", views.payment_history, name="payment_history"),
    path("listing/<str:listing_id>/review/", views.add_review, name="add_review"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("messages/", views.message_center, name="message_center"),
    path("ai-lab/", views.ai_lab, name="ai_lab"),
    path("assistant/", views.ai_assistant, name="ai_assistant"),
    path("moderation/", views.moderation_panel, name="moderation_panel"),
    path("moderation/<str:listing_id>/<str:action>/", views.moderate_listing, name="moderate_listing"),
    path("notification/<int:notification_id>/read/", views.read_notification, name="read_notification"),
    path("api/ai/draft/", views.api_generate_draft, name="api_generate_draft"),
    path("api/ai/price/", views.api_predict_price, name="api_predict_price"),
]
