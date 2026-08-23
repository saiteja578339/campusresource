def navigation_context(request):
    if not request.user.is_authenticated:
        return {"unread_notifications": 0, "unread_messages": 0}
    return {
        "unread_notifications": request.user.notifications.filter(is_read=False).count(),
        "unread_messages": request.user.received_messages.filter(is_read=False).count(),
    }
