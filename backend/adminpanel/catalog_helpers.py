from backend.cache_utils import cache_delete, cache_get, cache_set

from .models import ServiceCategory, SpotlightImage

HOME_CATALOG_CACHE_KEY = "catalog:home:v1"
HOME_CATALOG_TTL = 120


def _serialize_service(service, request):
    service_image = None
    if service.service_image:
        service_image = request.build_absolute_uri(service.service_image.url)

    return {
        "id": service.id,
        "name": service.name,
        "key": service.key,
        "description": service.description,
        "service_image": service_image,
        "status": service.status,
        "start_date": service.start_date,
        "display_order": service.display_order,
        "is_popular": service.is_popular,
        "is_available": service.status == "active",
    }


def _serialize_spotlight(spotlight, request):
    image_url = None
    if spotlight.image:
        image_url = request.build_absolute_uri(spotlight.image.url)

    return {
        "id": spotlight.id,
        "title": spotlight.title,
        "subtitle": spotlight.subtitle,
        "image_url": image_url,
        "redirect_url": spotlight.redirect_url,
        "display_order": spotlight.display_order,
    }


def build_home_catalog_payload(request):
    cached = cache_get(HOME_CATALOG_CACHE_KEY)
    if cached is not None:
        return cached

    services = list(
        ServiceCategory.objects.filter(
            status__in=["active", "coming_soon"],
        ).order_by("display_order", "name")
    )

    active_services = []
    popular_services = []
    coming_soon_services = []

    for service in services:
        row = _serialize_service(service, request)
        if service.status == "active":
            active_services.append(row)
            if service.is_popular:
                popular_services.append(row)
        elif service.status == "coming_soon":
            coming_soon_services.append(row)

    spotlights = [
        _serialize_spotlight(item, request)
        for item in SpotlightImage.objects.filter(is_active=True).order_by(
            "display_order",
            "-created_at",
        )
    ]

    payload = {
        "active_services": active_services,
        "popular_services": popular_services,
        "coming_soon_services": coming_soon_services,
        "spotlights": spotlights,
    }
    cache_set(HOME_CATALOG_CACHE_KEY, payload, HOME_CATALOG_TTL)
    return payload


def invalidate_home_catalog_cache():
    cache_delete(HOME_CATALOG_CACHE_KEY)
