from django.http import JsonResponse


def healthcheck(request):
    """Simple root endpoint so Nginx checks and bare domain do not 404."""
    return JsonResponse({"status": "ok"})
