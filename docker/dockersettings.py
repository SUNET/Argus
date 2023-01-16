"""Settings for production-like deployments in Docker"""
from argus.site.settings.prod import *

# Allow all hosts to reach backend, since all requests will typically come from
# outside the container:
ALLOWED_HOSTS = ["*"]
ARGUS_SEND_NOTIFICATIONS = True
DEFAULT_SMS_MEDIA="argus.notificationprofile.media.sms_as_email.SMSNotification"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
CSRF_TRUSTED_ORIGINS = ['https://*.sunet.se','https://*.127.0.0.1','https://*.sunet.se:9000']
CORS_ORIGIN_WHITELIST = ['https://*sunet.se','https://*.sunet.se:9000']

MEDIA_PLUGINS = [
    "argus.notificationprofile.media.email.EmailNotification",
    "argus.notificationprofile.media.sms_as_email.SMSNotification",
]

# Uncomment to enable both Email and SMS-as-email notification backends,
# leave commented out to keep just the default email backend:
# MEDIA_PLUGINS = [
#    "argus.notificationprofile.media.email.EmailNotification",
#    "argus.notificationprofile.media.sms_as_email.SMSNotification",
# ]
