from django.db.models import Count, Q

from backend.cache_utils import cache_delete, cache_delete_many, cache_get, cache_set

from services.models import Booking, Quote, ServiceRequest

from accounts.helpers import provider_rating

CUSTOMER_STATS_CACHE_PREFIX = "customer:dashboard:stats:"
PROVIDER_STATS_CACHE_PREFIX = "provider:dashboard:stats:"
CUSTOMER_HOME_CACHE_PREFIX = "customer:home:bootstrap:"
DASHBOARD_CACHE_TTL = 45


def _customer_stats_key(user_id: int) -> str:
    return f"{CUSTOMER_STATS_CACHE_PREFIX}{user_id}"


def _provider_stats_key(user_id: int) -> str:
    return f"{PROVIDER_STATS_CACHE_PREFIX}{user_id}"


def _customer_home_key(user_id: int) -> str:
    return f"{CUSTOMER_HOME_CACHE_PREFIX}{user_id}"


def invalidate_customer_dashboard_cache(user_id: int) -> None:
    cache_delete_many(
        [
            _customer_stats_key(user_id),
            _customer_home_key(user_id),
        ]
    )


def invalidate_provider_dashboard_cache(user_id: int) -> None:
    cache_delete(_provider_stats_key(user_id))


def get_customer_stats(user_id: int) -> dict[str, int]:
    cache_key = _customer_stats_key(user_id)
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    stats = ServiceRequest.objects.filter(customer_id=user_id).aggregate(
        total=Count("id"),
        booked=Count("id", filter=Q(is_booked=True)),
    )
    booked_count = stats["booked"] or 0
    total = stats["total"] or 0
    payload = {
        "booked_count": booked_count,
        "open_requests": total - booked_count,
    }
    cache_set(cache_key, payload, DASHBOARD_CACHE_TTL)
    return payload


def get_provider_stats(user) -> dict:
    cache_key = _provider_stats_key(user.id)
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    from django.db.models import Exists, OuterRef

    my_quote = Quote.objects.filter(
        service_request_id=OuterRef("pk"),
        provider_id=user.id,
    )

    new_jobs = (
        ServiceRequest.objects.filter(
            service_type=user.role,
            is_booked=False,
            selected_provider__isnull=True,
            status="pending",
        )
        .annotate(has_quoted=Exists(my_quote))
        .filter(has_quoted=False)
        .count()
    )

    active_jobs = (
        Booking.objects.filter(provider=user)
        .exclude(status__in=["completed", "cancelled"])
        .count()
    )

    average_rating, total_reviews = provider_rating(user)
    service_name = user.role.replace("_", " ").title()

    payload = {
        "role": "provider",
        "dashboard_type": f"{service_name} Dashboard",
        "features": [
            "View Service Requests",
            "Send Quotations",
            "Manage Jobs",
            "View Rating",
        ],
        "new_jobs": new_jobs,
        "active_jobs": active_jobs,
        "average_rating": average_rating,
        "total_reviews": total_reviews,
    }
    cache_set(cache_key, payload, DASHBOARD_CACHE_TTL)
    return payload


def get_customer_home_payload(request, user_id: int, catalog_payload: dict) -> dict:
    cache_key = _customer_home_key(user_id)
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    stats = get_customer_stats(user_id)
    payload = {
        "booked_count": stats["booked_count"],
        "open_requests": stats["open_requests"],
        "catalog": catalog_payload,
    }
    cache_set(cache_key, payload, DASHBOARD_CACHE_TTL)
    return payload
