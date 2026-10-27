def async_create(hass, message, title=None, notification_id=None):
    hass.notifications[notification_id] = message


def async_dismiss(hass, notification_id):
    hass.notifications.pop(notification_id, None)
