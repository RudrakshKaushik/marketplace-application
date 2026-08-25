from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date


VALID_PERIODS = {
    "7d",
    "30d",
    "6m",
    "1y",
}


def get_dashboard_filters(request):
    """
    Parse common admin dashboard query parameters.

    Supported:
        ?period=7d
        ?period=30d
        ?period=6m
        ?period=1y

        ?from=2026-08-01
        ?to=2026-08-25

        ?service=plumber
        ?provider_id=25
        ?status=completed
    """

    period = (
        request.query_params.get("period")
        or "30d"
    ).strip().lower()

    from_value = (
        request.query_params.get("from")
        or ""
    ).strip()

    to_value = (
        request.query_params.get("to")
        or ""
    ).strip()

    service = (
        request.query_params.get("service")
        or ""
    ).strip().lower()

    provider_id = (
        request.query_params.get("provider_id")
        or ""
    ).strip()

    status_value = (
        request.query_params.get("status")
        or ""
    ).strip().lower()

    # =========================================================
    # VALIDATE PERIOD
    # =========================================================

    if period not in VALID_PERIODS:
        period = "30d"

    # =========================================================
    # CURRENT TIME
    # =========================================================

    now = timezone.now()

    # =========================================================
    # CUSTOM DATE RANGE
    # =========================================================

    start_date = (
        parse_date(from_value)
        if from_value
        else None
    )

    end_date = (
        parse_date(to_value)
        if to_value
        else None
    )

    # =========================================================
    # PERIOD DATE RANGE
    # Used when custom dates are not provided.
    # =========================================================

    if not start_date:

        if period == "7d":
            start_date = (
                now - timedelta(days=7)
            ).date()

        elif period == "30d":
            start_date = (
                now - timedelta(days=30)
            ).date()

        elif period == "6m":
            start_date = (
                now - timedelta(days=180)
            ).date()

        elif period == "1y":
            start_date = (
                now - timedelta(days=365)
            ).date()

    if not end_date:
        end_date = now.date()

    # =========================================================
    # PROVIDER ID
    # =========================================================

    parsed_provider_id = None

    if provider_id:
        try:
            parsed_provider_id = int(
                provider_id
            )
        except (TypeError, ValueError):
            parsed_provider_id = None

    # =========================================================
    # RETURN NORMALIZED FILTERS
    # =========================================================

    return {
        "period": period,

        "start_date": start_date,
        "end_date": end_date,

        "service": service or None,

        "provider_id": (
            parsed_provider_id
        ),

        "status": (
            status_value or None
        ),
    }

# ============================================================
# DATE RANGE FILTER
# ============================================================

def apply_created_at_date_filter(
    queryset,
    filters,
):
    """
    Apply the common date range to a queryset
    that contains a created_at DateTimeField.
    """

    start_date = filters.get(
        "start_date"
    )

    end_date = filters.get(
        "end_date"
    )

    if start_date:
        queryset = queryset.filter(
            created_at__date__gte=start_date
        )

    if end_date:
        queryset = queryset.filter(
            created_at__date__lte=end_date
        )

    return queryset


# ============================================================
# CUSTOMER SERVICE REQUEST FILTERS
# ============================================================

def filter_service_requests(
    queryset,
    filters,
):
    """
    Apply dashboard filters to
    CustomerServiceRequest queryset.

    Supported:
    - date range
    - service
    - status

    provider_id is not applied directly because
    CustomerServiceRequest does not directly belong
    to one provider before booking/quotation.
    """

    queryset = apply_created_at_date_filter(
        queryset,
        filters,
    )

    service = filters.get(
        "service"
    )

    status_value = filters.get(
        "status"
    )

    # --------------------------------------------------------
    # SERVICE CATEGORY
    # --------------------------------------------------------

    if service:
        queryset = queryset.filter(
            category__key__iexact=service
        )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if status_value:
        queryset = queryset.filter(
            status__iexact=status_value
        )

    return queryset


# ============================================================
# PROVIDER QUOTATION FILTERS
# ============================================================

def filter_provider_quotations(
    queryset,
    filters,
):
    """
    Apply dashboard filters to
    ProviderQuotation queryset.

    Supported:
    - date range
    - service
    - provider_id
    - quotation status
    """

    queryset = apply_created_at_date_filter(
        queryset,
        filters,
    )

    service = filters.get(
        "service"
    )

    provider_id = filters.get(
        "provider_id"
    )

    status_value = filters.get(
        "status"
    )

    # --------------------------------------------------------
    # SERVICE
    # --------------------------------------------------------

    if service:
        queryset = queryset.filter(
            service_request__category__key__iexact=(
                service
            )
        )

    # --------------------------------------------------------
    # PROVIDER
    # --------------------------------------------------------

    if provider_id:
        queryset = queryset.filter(
            provider_profile__provider_id=(
                provider_id
            )
        )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if status_value:
        queryset = queryset.filter(
            status__iexact=status_value
        )

    return queryset


# ============================================================
# SERVICE BOOKING FILTERS
# ============================================================

def filter_service_bookings(
    queryset,
    filters,
):
    """
    Apply dashboard filters to
    ServiceBooking queryset.

    Supported:
    - date range
    - service
    - provider_id
    - booking status
    """

    queryset = apply_created_at_date_filter(
        queryset,
        filters,
    )

    service = filters.get(
        "service"
    )

    provider_id = filters.get(
        "provider_id"
    )

    status_value = filters.get(
        "status"
    )

    # --------------------------------------------------------
    # SERVICE
    # --------------------------------------------------------

    if service:
        queryset = queryset.filter(
            service_request__category__key__iexact=(
                service
            )
        )

    # --------------------------------------------------------
    # PROVIDER
    # --------------------------------------------------------

    if provider_id:
        queryset = queryset.filter(
            provider_profile__provider_id=(
                provider_id
            )
        )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if status_value:
        queryset = queryset.filter(
            status__iexact=status_value
        )

    return queryset


# ============================================================
# SERVICE REVIEW FILTERS
# ============================================================

def filter_service_reviews(
    queryset,
    filters,
):
    """
    Apply dashboard filters to
    ServiceReview queryset.

    Supported:
    - date range
    - service
    - provider_id

    ServiceReview has no status field,
    so status filtering is ignored here.
    """

    queryset = apply_created_at_date_filter(
        queryset,
        filters,
    )

    service = filters.get(
        "service"
    )

    provider_id = filters.get(
        "provider_id"
    )

    # --------------------------------------------------------
    # SERVICE
    # --------------------------------------------------------

    if service:
        queryset = queryset.filter(
            booking__service_request__category__key__iexact=(
                service
            )
        )

    # --------------------------------------------------------
    # PROVIDER
    # --------------------------------------------------------

    if provider_id:
        queryset = queryset.filter(
            provider_profile__provider_id=(
                provider_id
            )
        )

    return queryset