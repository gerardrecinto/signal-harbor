from django.conf import settings
from django.http import JsonResponse
from django.utils.crypto import constant_time_compare


class ApiKeyMiddleware:
    # SRP: only enforces API key authentication — routing and business logic stay elsewhere

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            provided = request.META.get("HTTP_X_API_KEY", "")
            if not constant_time_compare(provided, settings.SIGNAL_HARBOR_API_KEY):
                return JsonResponse({"detail": "Unauthorized"}, status=401)
        return self.get_response(request)
