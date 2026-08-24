from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, TypeVar

from backend.cache_utils import (
    cache_delete_many,
    cache_get,
    cache_get_or_set,
    cache_set,
)
from django.db import connection
from django.db.models import Avg, Count, Q

from accounts.helpers import provider_role_keys
from accounts.models import User
from adminpanel.models import ServiceCategory
from services.models import Booking, Quote, Review, ServiceRequest

ADMIN_MONITOR_BOOKINGS_KEY = "admin:marketplace:monitor:bookings:v2"
ADMIN_MONITOR_QUOTES_KEY = "admin:marketplace:monitor:quotes:v2"
ADMIN_MONITOR_PROVIDERS_KEY = "admin:marketplace:monitor:providers:v2"
ADMIN_STATS_CACHE_KEY = "admin:dashboard:stats:v2"
ADMIN_PENDING_CACHE_KEY = "admin:pending_providers:v2"
ADMIN_MONITOR_CACHE_KEY = "admin:marketplace:monitor:v2"
ADMIN_CACHE_TTL = 45


T = TypeVar("T")


def run_parallel(*tasks: Callable[[], T]) -> list[T]:
    if len(tasks) == 1:
        return [tasks[0]()]
    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        futures = [pool.submit(task) for task in tasks]
        return [future.result() for future in futures]


def invalidate_admin_cache() -> None:
    cache_delete_many(
        [
            ADMIN_STATS_CACHE_KEY,
            ADMIN_PENDING_CACHE_KEY,
            ADMIN_MONITOR_CACHE_KEY,
            ADMIN_MONITOR_BOOKINGS_KEY,
            ADMIN_MONITOR_QUOTES_KEY,
            ADMIN_MONITOR_PROVIDERS_KEY,
        ]
    )


def _fetch_user_stats(provider_roles: list[str]) -> dict[str, int]:
    return User.objects.aggregate(
        total_customers=Count("id", filter=Q(role="customer")),
        active_customers=Count("id", filter=Q(role="customer", is_active=True)),
        inactive_customers=Count("id", filter=Q(role="customer", is_active=False)),
        total_providers=Count("id", filter=Q(role__in=provider_roles)),
        active_providers=Count("id", filter=Q(role__in=provider_roles, is_active=True)),
        inactive_providers=Count("id", filter=Q(role__in=provider_roles, is_active=False)),
        pending_providers=Count("id", filter=Q(role__in=provider_roles, is_approved=False)),
        approved_providers=Count("id", filter=Q(role__in=provider_roles, is_approved=True)),
        verified_providers=Count("id", filter=Q(role__in=provider_roles, is_verified=True)),
    )


def _fetch_service_stats() -> dict[str, int]:
    return ServiceCategory.objects.aggregate(
        total_services=Count("id"),
        active_services=Count("id", filter=Q(status="active")),
        coming_soon_services=Count("id", filter=Q(status="coming_soon")),
        inactive_services=Count("id", filter=Q(status="inactive")),
    )


def _fetch_marketplace_totals() -> dict[str, int]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*)::int FROM services_booking) AS total_bookings,
                (SELECT COUNT(*)::int FROM services_booking WHERE status = 'completed') AS completed_bookings,
                (SELECT COUNT(*)::int FROM services_booking WHERE status = 'cancelled') AS cancelled_bookings,
                (SELECT COUNT(*)::int FROM services_servicerequest) AS total_requests,
                (SELECT COUNT(*)::int FROM services_quote) AS total_quotes,
                (SELECT COUNT(*)::int FROM services_review) AS total_reviews
            """
        )
        row = cursor.fetchone()
        columns = [col.name for col in cursor.description]
    return dict(zip(columns, row, strict=True))


def get_dashboard_stats() -> dict[str, Any]:
    cached = cache_get(ADMIN_STATS_CACHE_KEY)
    if cached is not None:
        return cached

    provider_roles = provider_role_keys()
    user_stats, service_stats, marketplace_totals = run_parallel(
        lambda: _fetch_user_stats(provider_roles),
        _fetch_service_stats,
        _fetch_marketplace_totals,
    )

    payload = {
        "users": user_stats,
        "services": service_stats,
        "marketplace": marketplace_totals,
    }
    cache_set(ADMIN_STATS_CACHE_KEY, payload, ADMIN_CACHE_TTL)
    return payload


def _serialize_pending_provider(provider: User, request) -> dict[str, Any]:
    return {
        "id": provider.id,
        "username": provider.username,
        "email": provider.email,
        "phone": provider.phone,
        "address": provider.address,
        "role": provider.role,
        "bio": provider.bio,
        "experience_years": provider.experience_years,
        "is_approved": provider.is_approved,
        "is_verified": provider.is_verified,
        "profile_picture": (
            request.build_absolute_uri(provider.profile_picture.url)
            if provider.profile_picture
            else None
        ),
        "date_joined": provider.date_joined,
    }


def get_pending_providers_payload(request) -> dict[str, Any]:
    cached = cache_get(ADMIN_PENDING_CACHE_KEY)
    if cached is not None:
        return cached

    providers = list(
        User.objects.filter(
            role__in=provider_role_keys(),
            is_approved=False,
        )
        .only(
            "id",
            "username",
            "email",
            "phone",
            "address",
            "role",
            "bio",
            "experience_years",
            "is_approved",
            "is_verified",
            "profile_picture",
            "date_joined",
        )
        .order_by("-date_joined")
    )

    payload = {
        "success": True,
        "providers": [_serialize_pending_provider(provider, request) for provider in providers],
    }
    cache_set(ADMIN_PENDING_CACHE_KEY, payload, ADMIN_CACHE_TTL)
    return payload


def _fetch_booking_rows() -> list[dict[str, Any]]:
    return list(
        Booking.objects.select_related("service_request", "customer", "provider")
        .order_by("-created_at")
        .values(
            "id",
            "service_request_id",
            "service_request__service_type",
            "customer_id",
            "customer__username",
            "provider_id",
            "provider__username",
            "final_price",
            "status",
            "created_at",
            "updated_at",
        )
    )


def _fetch_quote_rows() -> list[dict[str, Any]]:
    return list(
        Quote.objects.select_related("service_request__customer", "provider")
        .order_by("-created_at")
        .values(
            "id",
            "service_request_id",
            "service_request__service_type",
            "service_request__customer__username",
            "provider_id",
            "provider__username",
            "price",
            "message",
            "status",
            "created_at",
        )
    )


def _fetch_provider_performance_rows(request) -> list[dict[str, Any]]:
    providers = list(
        User.objects.filter(role__in=provider_role_keys())
        .order_by("username")
        .only(
            "id",
            "username",
            "email",
            "phone",
            "role",
            "is_active",
            "is_approved",
            "is_verified",
            "profile_picture",
        )
    )

    provider_ids = [provider.id for provider in providers]
    if not provider_ids:
        return []

    quote_stats, booking_stats, review_stats = run_parallel(
        lambda: {
            row["provider_id"]: row
            for row in Quote.objects.filter(provider_id__in=provider_ids)
            .values("provider_id")
            .annotate(
                total_quotes=Count("id"),
                accepted_quotes=Count("id", filter=Q(status="accepted")),
            )
        },
        lambda: {
            row["provider_id"]: row
            for row in Booking.objects.filter(provider_id__in=provider_ids)
            .values("provider_id")
            .annotate(
                total_bookings=Count("id"),
                completed_bookings=Count("id", filter=Q(status="completed")),
                cancelled_bookings=Count("id", filter=Q(status="cancelled")),
            )
        },
        lambda: {
            row["provider_id"]: row
            for row in Review.objects.filter(provider_id__in=provider_ids)
            .values("provider_id")
            .annotate(
                total_reviews=Count("id"),
                average_rating=Avg("rating"),
            )
        },
    )

    data = []
    for provider in providers:
        quotes = quote_stats.get(provider.id, {})
        bookings = booking_stats.get(provider.id, {})
        reviews = review_stats.get(provider.id, {})

        total_quotes = quotes.get("total_quotes", 0)
        accepted_quotes = quotes.get("accepted_quotes", 0)
        total_bookings = bookings.get("total_bookings", 0)
        completed_bookings = bookings.get("completed_bookings", 0)
        cancelled_bookings = bookings.get("cancelled_bookings", 0)
        total_reviews = reviews.get("total_reviews", 0)
        average_rating = round(reviews.get("average_rating") or 0, 1)

        acceptance_rate = round((accepted_quotes / total_quotes) * 100, 2) if total_quotes else 0
        completion_rate = round((completed_bookings / total_bookings) * 100, 2) if total_bookings else 0

        data.append(
            {
                "provider_id": provider.id,
                "provider": provider.username,
                "email": provider.email,
                "phone": provider.phone,
                "role": provider.role,
                "is_active": provider.is_active,
                "is_approved": provider.is_approved,
                "is_verified": provider.is_verified,
                "profile_picture": (
                    request.build_absolute_uri(provider.profile_picture.url)
                    if provider.profile_picture
                    else None
                ),
                "total_quotes": total_quotes,
                "accepted_quotes": accepted_quotes,
                "acceptance_rate": acceptance_rate,
                "total_bookings": total_bookings,
                "completed_bookings": completed_bookings,
                "cancelled_bookings": cancelled_bookings,
                "completion_rate": completion_rate,
                "total_reviews": total_reviews,
                "average_rating": average_rating,
            }
        )

    return data


def _normalize_booking_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": row["id"],
            "service_request_id": row["service_request_id"],
            "service_type": row["service_request__service_type"],
            "customer_id": row["customer_id"],
            "customer": row["customer__username"],
            "provider_id": row["provider_id"],
            "provider": row["provider__username"],
            "final_price": row["final_price"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def _normalize_quote_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": row["id"],
            "service_request_id": row["service_request_id"],
            "service_type": row["service_request__service_type"],
            "customer": row["service_request__customer__username"],
            "provider_id": row["provider_id"],
            "provider": row["provider__username"],
            "price": row["price"],
            "message": row["message"],
            "status": row["status"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_marketplace_monitor_payload(request, sections: set[str] | None = None) -> dict[str, Any]:
    include = sections or {"bookings", "quotes", "providers"}
    if include == {"bookings", "quotes", "providers"}:
        cached = cache_get(ADMIN_MONITOR_CACHE_KEY)
        if cached is not None:
            return cached

    payload: dict[str, Any] = {"success": True}
    tasks: list[tuple[str, Callable[[], Any]]] = []

    if "bookings" in include:
        tasks.append(
            (
                "bookings",
                lambda: cache_get_or_set(
                    ADMIN_MONITOR_BOOKINGS_KEY,
                    lambda: _normalize_booking_rows(_fetch_booking_rows()),
                    ADMIN_CACHE_TTL,
                ),
            )
        )
    if "quotes" in include:
        tasks.append(
            (
                "quotes",
                lambda: cache_get_or_set(
                    ADMIN_MONITOR_QUOTES_KEY,
                    lambda: _normalize_quote_rows(_fetch_quote_rows()),
                    ADMIN_CACHE_TTL,
                ),
            )
        )
    if "providers" in include:
        tasks.append(
            (
                "providers",
                lambda: cache_get_or_set(
                    ADMIN_MONITOR_PROVIDERS_KEY,
                    lambda: _fetch_provider_performance_rows(request),
                    ADMIN_CACHE_TTL,
                ),
            )
        )

    if len(tasks) == 1:
        key, task = tasks[0]
        payload[key] = task()
    else:
        results = run_parallel(lambda _task=task: _task() for _, task in tasks)
        for (key, _), value in zip(tasks, results, strict=True):
            payload[key] = value

    if include == {"bookings", "quotes", "providers"}:
        cache_set(ADMIN_MONITOR_CACHE_KEY, payload, ADMIN_CACHE_TTL)

    return payload
