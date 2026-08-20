from django.urls import include, path

from signals.views import HealthView

urlpatterns = [
    path("health", HealthView.as_view()),
    path("api/v1/", include("signals.urls")),
]
