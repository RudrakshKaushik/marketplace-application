from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.models import User
from accounts.helpers import is_provider_role, media_url, provider_role_keys
from service_requests.models import (
    CustomerServiceRequest,
    ProviderQuotation,
    ServiceBooking,
    ServiceReview,
)
from datetime import timedelta
from django.db.models.functions import TruncDate, TruncMonth
from django.db.models import Avg, Count, Max, Q, Sum
from django.utils import timezone

from .services.dashboard_filters import (
    get_dashboard_filters,
    filter_service_requests,
    filter_provider_quotations,
    filter_service_bookings,
    filter_service_reviews,
)
from .models import ServiceCategory, SpotlightImage

from .permissions import (
    IsAdminUser,
    CanManageAdminUsers,
    CanManageProviders,
    CanManageCustomers,
    CanManageServices,
    CanManageBookings,
    CanManageQuotes,
    CanViewReports,
    CanManageSpotlights,
    get_admin_permissions,
)

from .serializers import (
    AdminUserSerializer,
    CreateAdminUserSerializer,
    UpdateAdminUserSerializer,
    SpotlightImageSerializer,
)

def parse_boolean(value, default=False):
    """
    Convert form-data/string boolean values safely.
    """

    if value is None:
        return default

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in (
        "true",
        "1",
        "yes",
        "on",
    )


@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    IsAdminUser,
])
def admin_dashboard(request):
    """
    Production admin dashboard summary.

    Supports:
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

    user = request.user

    # =========================================================
    # ADMIN PERMISSIONS
    # =========================================================

    permissions = get_admin_permissions(
        user
    )

    # =========================================================
    # DASHBOARD FILTERS
    # =========================================================

    dashboard_filters = (
        get_dashboard_filters(request)
    )

    # =========================================================
    # CUSTOMER STATISTICS
    # =========================================================

    customer_queryset = (
        User.objects
        .filter(
            role="customer"
        )
    )

    total_customers = (
        customer_queryset.count()
    )

    active_customers = (
        customer_queryset
        .filter(
            is_active=True
        )
        .count()
    )

    inactive_customers = (
        customer_queryset
        .filter(
            is_active=False
        )
        .count()
    )

    # =========================================================
    # PROVIDER STATISTICS
    # =========================================================

    provider_roles = (
        provider_role_keys()
    )

    provider_queryset = (
        User.objects
        .filter(
            role__in=provider_roles
        )
    )

    total_providers = (
        provider_queryset.count()
    )

    active_providers = (
        provider_queryset
        .filter(
            is_active=True
        )
        .count()
    )

    inactive_providers = (
        provider_queryset
        .filter(
            is_active=False
        )
        .count()
    )

    pending_providers = (
        provider_queryset
        .filter(
            is_approved=False
        )
        .count()
    )

    approved_providers = (
        provider_queryset
        .filter(
            is_approved=True
        )
        .count()
    )

    verified_providers = (
        provider_queryset
        .filter(
            is_verified=True
        )
        .count()
    )

    unverified_providers = (
        provider_queryset
        .filter(
            is_verified=False
        )
        .count()
    )

    # =========================================================
    # SERVICE STATISTICS
    # =========================================================

    total_services = (
        ServiceCategory.objects.count()
    )

    active_services = (
        ServiceCategory.objects
        .filter(
            status="active"
        )
        .count()
    )

    coming_soon_services = (
        ServiceCategory.objects
        .filter(
            status="coming_soon"
        )
        .count()
    )

    inactive_services = (
        ServiceCategory.objects
        .filter(
            status="inactive"
        )
        .count()
    )

    popular_services = (
        ServiceCategory.objects
        .filter(
            status="active",
            is_popular=True,
        )
        .count()
    )

    # =========================================================
    # BASE ANALYTICS QUERYSETS
    # =========================================================

    service_requests = (
        filter_service_requests(
            CustomerServiceRequest.objects.all(),
            dashboard_filters,
        )
    )

    quotations = (
        filter_provider_quotations(
            ProviderQuotation.objects.all(),
            dashboard_filters,
        )
    )

    bookings = (
        filter_service_bookings(
            ServiceBooking.objects.all(),
            dashboard_filters,
        )
    )

    reviews = (
        filter_service_reviews(
            ServiceReview.objects.all(),
            dashboard_filters,
        )
    )

    # =========================================================
    # MARKETPLACE TOTALS
    # =========================================================

    total_requests = (
        service_requests.count()
    )

    total_quotes = (
        quotations.count()
    )

    total_bookings = (
        bookings.count()
    )

    completed_bookings = (
        bookings
        .filter(
            status="completed"
        )
        .count()
    )

    cancelled_bookings = (
        bookings
        .filter(
            status="cancelled"
        )
        .count()
    )

    total_reviews = (
        reviews.count()
    )

    # =========================================================
    # REQUEST ACTIVITY
    # =========================================================

    now = timezone.now()

    today = now.date()

    seven_days_ago = (
        today - timedelta(days=6)
    )

    month_start = (
        today.replace(day=1)
    )

    requests_today = (
        CustomerServiceRequest.objects
        .filter(
            created_at__date=today
        )
    )

    requests_this_week = (
        CustomerServiceRequest.objects
        .filter(
            created_at__date__gte=(
                seven_days_ago
            ),
            created_at__date__lte=today,
        )
    )

    requests_this_month = (
        CustomerServiceRequest.objects
        .filter(
            created_at__date__gte=(
                month_start
            ),
            created_at__date__lte=today,
        )
    )

    # Apply service filter to these operational counters too.
    service_filter = (
        dashboard_filters.get(
            "service"
        )
    )

    if service_filter:

        requests_today = (
            requests_today.filter(
                category__key__iexact=(
                    service_filter
                )
            )
        )

        requests_this_week = (
            requests_this_week.filter(
                category__key__iexact=(
                    service_filter
                )
            )
        )

        requests_this_month = (
            requests_this_month.filter(
                category__key__iexact=(
                    service_filter
                )
            )
        )

    requests_today_count = (
        requests_today.count()
    )

    requests_this_week_count = (
        requests_this_week.count()
    )

    requests_this_month_count = (
        requests_this_month.count()
    )

    # =========================================================
    # BOOKING VALUE
    # =========================================================
    # Cancelled bookings are excluded from booking-value KPIs.

    non_cancelled_bookings = (
        bookings.exclude(
            status="cancelled"
        )
    )

    booking_value_data = (
        non_cancelled_bookings.aggregate(
            total=Sum(
                "final_price"
            ),
            average=Avg(
                "final_price"
            ),
        )
    )

    total_booking_value = (
        booking_value_data["total"]
        or 0
    )

    average_booking_value = (
        booking_value_data["average"]
        or 0
    )

    # =========================================================
    # COMPLETION RATE
    # =========================================================

    completion_rate = 0

    if total_bookings > 0:

        completion_rate = round(
            (
                completed_bookings
                / total_bookings
            )
            * 100,
            2,
        )

    # =========================================================
    # CANCELLATION RATE
    # =========================================================

    cancellation_rate = 0

    if total_bookings > 0:

        cancellation_rate = round(
            (
                cancelled_bookings
                / total_bookings
            )
            * 100,
            2,
        )

    # =========================================================
    # AVERAGE PROVIDER RATING
    # =========================================================

    rating_data = (
        reviews.aggregate(
            average=Avg(
                "rating"
            )
        )
    )

    average_provider_rating = (
        rating_data["average"]
        or 0
    )

    average_provider_rating = round(
        float(
            average_provider_rating
        ),
        2,
    )

    # =========================================================
    # RESPONSE
    # =========================================================

    return Response(
        {
            "success": True,

            "message": (
                "Admin dashboard fetched "
                "successfully."
            ),

            # =================================================
            # APPLIED FILTERS
            # =================================================

            "filters": {
                "period": (
                    dashboard_filters[
                        "period"
                    ]
                ),

                "from": (
                    dashboard_filters[
                        "start_date"
                    ]
                ),

                "to": (
                    dashboard_filters[
                        "end_date"
                    ]
                ),

                "service": (
                    dashboard_filters[
                        "service"
                    ]
                ),

                "provider_id": (
                    dashboard_filters[
                        "provider_id"
                    ]
                ),

                "status": (
                    dashboard_filters[
                        "status"
                    ]
                ),
            },

            # =================================================
            # LOGGED-IN ADMIN
            # =================================================

            "admin": {
                "id": user.id,

                "username": (
                    user.username
                ),

                "email": (
                    user.email
                ),

                "first_name": (
                    user.first_name
                ),

                "last_name": (
                    user.last_name
                ),

                "full_name": (
                    user.get_full_name()
                    or user.username
                ),

                "is_staff": (
                    user.is_staff
                ),

                "is_superuser": (
                    user.is_superuser
                ),

                "is_active": (
                    user.is_active
                ),

                "admin_type": (
                    "super_admin"
                    if user.is_superuser
                    else "admin"
                ),

                "permissions": (
                    permissions
                ),
            },

            # =================================================
            # DASHBOARD DATA
            # =================================================

            "data": {

                # =============================================
                # USERS
                # =============================================

                "users": {

                    "customers": {
                        "total": (
                            total_customers
                        ),

                        "active": (
                            active_customers
                        ),

                        "inactive": (
                            inactive_customers
                        ),
                    },

                    "providers": {
                        "total": (
                            total_providers
                        ),

                        "active": (
                            active_providers
                        ),

                        "inactive": (
                            inactive_providers
                        ),

                        "pending": (
                            pending_providers
                        ),

                        "approved": (
                            approved_providers
                        ),

                        "verified": (
                            verified_providers
                        ),

                        "unverified": (
                            unverified_providers
                        ),

                        "pending_approvals": (
                            pending_providers
                        ),
                    },
                },

                # =============================================
                # SERVICES
                # =============================================

                "services": {
                    "total": (
                        total_services
                    ),

                    "active": (
                        active_services
                    ),

                    "coming_soon": (
                        coming_soon_services
                    ),

                    "inactive": (
                        inactive_services
                    ),

                    "popular": (
                        popular_services
                    ),
                },

                # =============================================
                # REQUESTS
                # =============================================

                "requests": {
                    "total": (
                        total_requests
                    ),

                    "today": (
                        requests_today_count
                    ),

                    "this_week": (
                        requests_this_week_count
                    ),

                    "this_month": (
                        requests_this_month_count
                    ),
                },

                # =============================================
                # QUOTATIONS
                # =============================================

                "quotations": {
                    "total": (
                        total_quotes
                    ),
                },

                # =============================================
                # BOOKINGS
                # =============================================

                "bookings": {
                    "total": (
                        total_bookings
                    ),

                    "completed": (
                        completed_bookings
                    ),

                    "cancelled": (
                        cancelled_bookings
                    ),

                    "completion_rate": (
                        completion_rate
                    ),

                    "cancellation_rate": (
                        cancellation_rate
                    ),

                    "total_booking_value": (
                        total_booking_value
                    ),

                    "average_booking_value": (
                        average_booking_value
                    ),
                },

                # =============================================
                # REVIEWS
                # =============================================

                "reviews": {
                    "total": (
                        total_reviews
                    ),

                    "average_provider_rating": (
                        average_provider_rating
                    ),
                },
            },
        },
        status=status.HTTP_200_OK,
    )
    
@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    CanViewReports,
])
def dashboard_trends_api(request):
    """
    Return booking and booking-value trends
    for admin dashboard charts.

    Supports:
        ?period=7d
        ?period=30d
        ?period=6m
        ?period=1y
        ?from=YYYY-MM-DD
        ?to=YYYY-MM-DD
        ?service=plumber
        ?provider_id=25
    """

    dashboard_filters = (
        get_dashboard_filters(request)
    )

    bookings = (
        filter_service_bookings(
            ServiceBooking.objects.all(),
            dashboard_filters,
        )
    )

    period = dashboard_filters["period"]

    # =========================================================
    # GROUPING
    # =========================================================

    if period in [
        "6m",
        "1y",
    ]:

        grouped = (
            bookings
            .annotate(
                period_label=TruncMonth(
                    "created_at"
                )
            )
            .values(
                "period_label"
            )
            .annotate(
                booking_count=Count("id"),

                completed_bookings=Count(
                    "id",
                    filter=Q(
                        status="completed"
                    ),
                ),

                cancelled_bookings=Count(
                    "id",
                    filter=Q(
                        status="cancelled"
                    ),
                ),

                booking_value=Sum(
                    "final_price"
                ),
            )
            .order_by(
                "period_label"
            )
        )

    else:

        grouped = (
            bookings
            .annotate(
                period_label=TruncDate(
                    "created_at"
                )
            )
            .values(
                "period_label"
            )
            .annotate(
                booking_count=Count("id"),

                completed_bookings=Count(
                    "id",
                    filter=Q(
                        status="completed"
                    ),
                ),

                cancelled_bookings=Count(
                    "id",
                    filter=Q(
                        status="cancelled"
                    ),
                ),

                booking_value=Sum(
                    "final_price"
                ),
            )
            .order_by(
                "period_label"
            )
        )

    # =========================================================
    # CHART DATA
    # =========================================================

    labels = []
    booking_count = []
    completed_bookings = []
    cancelled_bookings = []
    booking_value = []

    for item in grouped:

        label = item["period_label"]

        if period in [
            "6m",
            "1y",
        ]:
            label = label.strftime(
                "%b %Y"
            )

        else:
            label = label.strftime(
                "%d %b"
            )

        labels.append(label)

        booking_count.append(
            item["booking_count"]
        )

        completed_bookings.append(
            item[
                "completed_bookings"
            ]
        )

        cancelled_bookings.append(
            item[
                "cancelled_bookings"
            ]
        )

        booking_value.append(
            float(
                item["booking_value"]
                or 0
            )
        )

    # =========================================================
    # SUMMARY
    # =========================================================

    summary = bookings.aggregate(
        total_booking_value=Sum(
            "final_price"
        ),
        total_bookings=Count(
            "id"
        ),
    )

    total_booking_value = (
        summary[
            "total_booking_value"
        ]
        or 0
    )

    total_bookings = (
        summary[
            "total_bookings"
        ]
        or 0
    )

    # =========================================================
    # RESPONSE
    # =========================================================

    return Response(
        {
            "success": True,
            "message": (
                "Dashboard trends fetched successfully."
            ),

            "filters": {
                "period": (
                    dashboard_filters[
                        "period"
                    ]
                ),

                "from": (
                    dashboard_filters[
                        "start_date"
                    ]
                ),

                "to": (
                    dashboard_filters[
                        "end_date"
                    ]
                ),

                "service": (
                    dashboard_filters[
                        "service"
                    ]
                ),

                "provider_id": (
                    dashboard_filters[
                        "provider_id"
                    ]
                ),
            },

            "summary": {
                "total_bookings": (
                    total_bookings
                ),

                "total_booking_value": (
                    total_booking_value
                ),
            },

            "chart": {
                "labels": labels,

                "booking_count": (
                    booking_count
                ),

                "completed_bookings": (
                    completed_bookings
                ),

                "cancelled_bookings": (
                    cancelled_bookings
                ),

                "booking_value": (
                    booking_value
                ),
            },
        },
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    CanManageProviders,
])
def pending_providers(request):
    """
    Return providers waiting for admin approval.
    """

    providers = (
        User.objects
        .filter(
            role__in=provider_role_keys(),
            is_approved=False,
        )
        .order_by("-date_joined")
    )

    data = []

    for provider in providers:
        data.append(
            {
                "id": provider.id,
                "username": provider.username,
                "email": provider.email,
                "first_name": provider.first_name,
                "last_name": provider.last_name,
                "full_name": (
                    provider.get_full_name()
                    or provider.username
                ),
                "phone": provider.phone,
                "address": provider.address,
                "role": provider.role,
                "bio": provider.bio,
                "experience_years": provider.experience_years,
                "is_email_verified": provider.is_email_verified,
                "is_approved": provider.is_approved,
                "is_verified": provider.is_verified,
                "is_active": provider.is_active,
                "status_note": provider.status_note or "",
                "profile_picture": (
                    request.build_absolute_uri(
                        provider.profile_picture.url
                    )
                    if provider.profile_picture
                    else None
                ),
                "date_joined": provider.date_joined,
            }
        )

    return Response(
        {
            "success": True,
            "message": "Pending providers fetched successfully.",
            "count": len(data),
            "providers": data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([
    IsAuthenticated,
    CanManageProviders,
])
def approve_provider(request, provider_id):
    """
    Approve a provider account.

    Approval also:
    - verifies the provider
    - activates the provider
    - clears previous status/rejection note
    """

    provider = (
        User.objects
        .filter(
            id=provider_id,
            role__in=provider_role_keys(),
        )
        .first()
    )

    if not provider:
        return Response(
            {
                "success": False,
                "message": "Provider not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    provider.is_approved = True
    provider.is_verified = True
    provider.is_active = True
    provider.status_note = ""

    provider.save(
        update_fields=[
            "is_approved",
            "is_verified",
            "is_active",
            "status_note",
        ]
    )

    return Response(
        {
            "success": True,
            "message": "Provider approved successfully.",
            "data": {
                "id": provider.id,
                "username": provider.username,
                "email": provider.email,
                "role": provider.role,
                "is_approved": provider.is_approved,
                "is_verified": provider.is_verified,
                "is_active": provider.is_active,
                "status_note": provider.status_note,
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([
    IsAuthenticated,
    CanManageProviders,
])
def reject_provider(request, provider_id):
    """
    Reject a provider account.

    Rejection:
    - removes approval
    - removes verification
    - deactivates the account
    - stores rejection reason
    """

    reason = (
        request.data.get("reason")
        or ""
    ).strip()

    if not reason:
        return Response(
            {
                "success": False,
                "message": "Reason is required.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    provider = (
        User.objects
        .filter(
            id=provider_id,
            role__in=provider_role_keys(),
        )
        .first()
    )

    if not provider:
        return Response(
            {
                "success": False,
                "message": "Provider not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    provider.is_approved = False
    provider.is_verified = False
    provider.is_active = False
    provider.status_note = reason

    provider.save(
        update_fields=[
            "is_approved",
            "is_verified",
            "is_active",
            "status_note",
        ]
    )

    return Response(
        {
            "success": True,
            "message": "Provider rejected successfully.",
            "data": {
                "id": provider.id,
                "username": provider.username,
                "email": provider.email,
                "role": provider.role,
                "is_approved": provider.is_approved,
                "is_verified": provider.is_verified,
                "is_active": provider.is_active,
                "status_note": provider.status_note,
            },
        },
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    CanManageServices,
])
def service_categories(request):

    services = (
        ServiceCategory.objects
        .all()
        .order_by(
            "display_order",
            "id",
        )
    )

    return Response({
        "success": True,

        "services": [
            {
                "id": service.id,

                "name": service.name,

                "key": service.key,

                "description": service.description,
                "service_image": media_url(request, service.service_image),
                "status": service.status,

                "start_date": service.start_date,

                "display_order": (
                    service.display_order
                ),

                "is_popular": (
                    service.is_popular
                ),
            }

            for service in services
        ],
    })


@api_view(["POST"])
@permission_classes([
    IsAuthenticated,
    CanManageServices,
])
def create_service_category(request):

    name = request.data.get("name")
    key = request.data.get("key")
    description = request.data.get(
        "description"
    )

    service_image = request.FILES.get(
        "service_image"
    )

    # -----------------------------------------
    # VALIDATION
    # -----------------------------------------

    if not name or not key or not description:

        return Response(
            {
                "success": False,
                "message": (
                    "name, key and description "
                    "are required"
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if ServiceCategory.objects.filter(
        key=key
    ).exists():

        return Response(
            {
                "success": False,
                "message": (
                    "Service key already exists"
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    max_order = (
        ServiceCategory.objects.aggregate(max_order=Max("display_order"))["max_order"] or 0
    )

    service = ServiceCategory.objects.create(
        name=name,
        key=key,
        description=description,

        service_image=service_image,
        status=request.data.get("status", "coming_soon"),
        start_date=request.data.get("start_date", "Yet to start"),
        display_order=max_order + 1,
    )

    return Response({
        "success": True,
        "message": "Service category created successfully",
        "service_id": service.id,
        "service_image": media_url(request, service.service_image),
    }, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([
    IsAuthenticated,
    CanManageServices,
])
def update_service_category(
    request,
    service_id,
):

    service = (
        ServiceCategory.objects
        .filter(
            id=service_id
        )
        .first()
    )

    if not service:

        return Response(
            {
                "success": False,
                "message": (
                    "Service not found"
                ),
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    service.name = request.data.get("name", service.name)

    service.description = request.data.get(
        "description",
        service.description,
    )

    service.status = request.data.get(
        "status",
        service.status,
    )

    service.start_date = request.data.get(
        "start_date",
        service.start_date,
    )

    service.display_order = request.data.get(
        "display_order",
        service.display_order,
    )

    # -----------------------------------------
    # POPULAR SERVICE
    # -----------------------------------------

    if "is_popular" in request.data:

        service.is_popular = parse_boolean(
            request.data.get(
                "is_popular"
            )
        )

    # -----------------------------------------
    # IMAGE
    # -----------------------------------------

    service_image = request.FILES.get(
        "service_image"
    )

    if service_image:
        service.service_image = (
            service_image
        )

    service.save()

    # -----------------------------------------
    # RESPONSE
    # -----------------------------------------

    return Response({
        "success": True,

        "message": (
            "Service category updated "
            "successfully"
        ),

        "service": {
            "id": service.id,

            "name": service.name,

            "key": service.key,
            "description": service.description,
            "service_image": media_url(request, service.service_image),
            "status": service.status,

            "start_date": (
                service.start_date
            ),

            "display_order": (
                service.display_order
            ),

            "is_popular": (
                service.is_popular
            ),
        },
    })


@api_view(["POST"])
@permission_classes([IsAdminUser])
def reorder_service_categories(request):
    order = request.data.get("order")

    if not isinstance(order, list) or not order:
        return Response(
            {
                "success": False,
                "message": "order must be a non-empty list of service ids",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        service_ids = [int(service_id) for service_id in order]
    except (TypeError, ValueError):
        return Response(
            {
                "success": False,
                "message": "order must contain valid service ids",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    services = ServiceCategory.objects.filter(id__in=service_ids)
    services_by_id = {service.id: service for service in services}

    if len(services_by_id) != len(set(service_ids)):
        return Response(
            {
                "success": False,
                "message": "One or more service ids are invalid",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    updated = []
    for index, service_id in enumerate(service_ids):
        service = services_by_id[service_id]
        service.display_order = index + 1
        updated.append(service)

    ServiceCategory.objects.bulk_update(updated, ["display_order"])

    return Response({
        "success": True,
        "message": "Service order updated successfully",
    })


@api_view(["DELETE"])
@permission_classes([
    IsAuthenticated,
    CanManageServices,
])
def delete_service_category(request, service_id):

    reason = request.data.get("reason")

    if not reason:
        return Response(
            {
                "success": False,
                "message": "Delete reason is required"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    service = ServiceCategory.objects.filter(
        id=service_id
    ).first()

    if not service:
        return Response(
            {
                "success": False,
                "message": "Service not found"
            },
            status=status.HTTP_404_NOT_FOUND
        )

    service_name = service.name
    service_key = service.key

    service.delete()

    return Response({
        "success": True,
        "message": "Service category deleted successfully",
        "deleted_service": {
            "name": service_name,
            "key": service_key,
            "reason": reason
        }
    })


@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    CanManageProviders,
])
def all_providers(request):
    """
    Return all providers for admin management.
    """

    providers = list(
        User.objects
        .filter(role__in=provider_role_keys())
        .order_by("-date_joined")
        .only(
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "address",
            "role",
            "bio",
            "experience_years",
            "is_email_verified",
            "is_approved",
            "is_verified",
            "is_active",
            "status_note",
            "profile_picture",
            "date_joined",
            "last_login",
        )
    )

    providers_data = [
        {
            "id": provider.id,
            "username": provider.username,
            "email": provider.email,
            "first_name": provider.first_name,
            "last_name": provider.last_name,
            "full_name": provider.get_full_name() or provider.username,
            "phone": provider.phone,
            "address": provider.address,
            "role": provider.role,
            "bio": provider.bio,
            "experience_years": provider.experience_years,
            "is_email_verified": provider.is_email_verified,
            "is_approved": provider.is_approved,
            "is_verified": provider.is_verified,
            "is_active": provider.is_active,
            "status_note": provider.status_note or "",
            "profile_picture": (
                request.build_absolute_uri(provider.profile_picture.url)
                if provider.profile_picture
                else None
            ),
            "date_joined": provider.date_joined,
            "last_login": provider.last_login,
        }
        for provider in providers
    ]

    return Response(
        {
            "success": True,
            "message": "Providers fetched successfully.",
            "count": len(providers_data),
            "providers": providers_data,
        },
        status=status.HTTP_200_OK,
    )

@api_view(["POST"])
@permission_classes([
    IsAuthenticated,
    CanManageProviders,
])
def activate_provider(request, provider_id):
    """
    Reactivate an existing provider account.

    This does NOT approve a rejected/pending provider.
    It only activates an already approved provider.
    """

    provider = (
        User.objects
        .filter(
            id=provider_id,
            role__in=provider_role_keys(),
        )
        .first()
    )

    if not provider:
        return Response(
            {
                "success": False,
                "message": "Provider not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # A provider must be approved before activation.
    if not provider.is_approved:
        return Response(
            {
                "success": False,
                "message": (
                    "Provider must be approved before "
                    "the account can be activated."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    provider.is_active = True
    provider.deactivate_reason = None
    provider.status_note = ""

    provider.save(
        update_fields=[
            "is_active",
            "deactivate_reason",
            "status_note",
        ]
    )

    return Response(
        {
            "success": True,
            "message": (
                "Provider activated successfully."
            ),
            "data": {
                "id": provider.id,
                "username": provider.username,
                "email": provider.email,
                "role": provider.role,
                "is_approved": provider.is_approved,
                "is_verified": provider.is_verified,
                "is_active": provider.is_active,
                "deactivate_reason": None,
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([
    IsAuthenticated,
    CanManageProviders,
])
def deactivate_provider(request, provider_id):
    """
    Deactivate an existing provider account.

    A reason is required for audit/admin visibility.
    """

    reason = (
        request.data.get("reason")
        or ""
    ).strip()

    if not reason:
        return Response(
            {
                "success": False,
                "message": (
                    "Deactivation reason is required."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    provider = (
        User.objects
        .filter(
            id=provider_id,
            role__in=provider_role_keys(),
        )
        .first()
    )

    if not provider:
        return Response(
            {
                "success": False,
                "message": "Provider not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    provider.is_active = False
    provider.deactivate_reason = reason

    provider.save(
        update_fields=[
            "is_active",
            "deactivate_reason",
        ]
    )

    return Response(
        {
            "success": True,
            "message": (
                "Provider deactivated successfully."
            ),
            "data": {
                "id": provider.id,
                "username": provider.username,
                "email": provider.email,
                "role": provider.role,
                "is_approved": provider.is_approved,
                "is_verified": provider.is_verified,
                "is_active": provider.is_active,
                "deactivate_reason": (
                    provider.deactivate_reason
                ),
            },
        },
        status=status.HTTP_200_OK,
    )
@api_view(["POST"])
@permission_classes([
    IsAuthenticated,
    CanManageProviders,
])
def verify_provider(request, provider_id):
    """
    Mark an approved provider as verified.
    """

    reason = (
        request.data.get("reason")
        or ""
    ).strip()

    provider = (
        User.objects
        .filter(
            id=provider_id,
            role__in=provider_role_keys(),
        )
        .first()
    )

    if not provider:
        return Response(
            {
                "success": False,
                "message": "Provider not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if not provider.is_approved:
        return Response(
            {
                "success": False,
                "message": (
                    "Provider must be approved before "
                    "verification."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    provider.is_verified = True
    provider.status_note = ""

    provider.save(
        update_fields=[
            "is_verified",
            "status_note",
        ]
    )

    return Response(
        {
            "success": True,
            "message": "Provider verified successfully.",
            "data": {
                "id": provider.id,
                "username": provider.username,
                "email": provider.email,
                "role": provider.role,
                "is_approved": provider.is_approved,
                "is_verified": provider.is_verified,
                "is_active": provider.is_active,
                "reason": reason or None,
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([
    IsAuthenticated,
    CanManageProviders,
])
def unverify_provider(request, provider_id):
    """
    Remove provider verification.

    This does not automatically reject or deactivate
    the provider.
    """

    reason = (
        request.data.get("reason")
        or ""
    ).strip()

    if not reason:
        return Response(
            {
                "success": False,
                "message": (
                    "Unverify reason is required."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    provider = (
        User.objects
        .filter(
            id=provider_id,
            role__in=provider_role_keys(),
        )
        .first()
    )

    if not provider:
        return Response(
            {
                "success": False,
                "message": "Provider not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    provider.is_verified = False
    provider.status_note = reason

    provider.save(
        update_fields=[
            "is_verified",
            "status_note",
        ]
    )

    return Response(
        {
            "success": True,
            "message": "Provider unverified successfully.",
            "data": {
                "id": provider.id,
                "username": provider.username,
                "email": provider.email,
                "role": provider.role,
                "is_approved": provider.is_approved,
                "is_verified": provider.is_verified,
                "is_active": provider.is_active,
                "reason": reason,
            },
        },
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    CanManageCustomers,
])
def all_customers(request):
    """
    Return all customer accounts for admin management.
    """

    customers = list(
        User.objects
        .filter(role="customer")
        .order_by("-date_joined")
        .only(
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "address",
            "is_active",
            "is_email_verified",
            "profile_picture",
            "date_joined",
            "last_login",
        )
    )

    customers_data = [
        {
            "id": customer.id,
            "username": customer.username,
            "email": customer.email,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "full_name": customer.get_full_name() or customer.username,
            "phone": customer.phone,
            "address": customer.address,
            "is_active": customer.is_active,
            "is_email_verified": customer.is_email_verified,
            "profile_picture": (
                request.build_absolute_uri(customer.profile_picture.url)
                if customer.profile_picture
                else None
            ),
            "date_joined": customer.date_joined,
            "last_login": customer.last_login,
        }
        for customer in customers
    ]

    return Response(
        {
            "success": True,
            "message": "Customers fetched successfully.",
            "count": len(customers_data),
            "customers": customers_data,
        },
        status=status.HTTP_200_OK,
    )

@api_view(["POST"])
@permission_classes([
    IsAuthenticated,
    CanManageCustomers,
])
def activate_customer(request, customer_id):

    customer = (
        User.objects
        .filter(
            id=customer_id,
            role="customer",
        )
        .first()
    )

    if not customer:
        return Response(
            {
                "success": False,
                "message": "Customer not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    customer.is_active = True

    customer.save(
        update_fields=[
            "is_active",
        ]
    )

    return Response(
        {
            "success": True,
            "message": "Customer activated successfully.",
            "data": {
                "id": customer.id,
                "username": customer.username,
                "email": customer.email,
                "is_active": customer.is_active,
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([
    IsAuthenticated,
    CanManageCustomers,
])
def deactivate_customer(request, customer_id):

    customer = (
        User.objects
        .filter(
            id=customer_id,
            role="customer",
        )
        .first()
    )

    if not customer:
        return Response(
            {
                "success": False,
                "message": "Customer not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    customer.is_active = False

    customer.save(
        update_fields=[
            "is_active",
        ]
    )

    return Response(
        {
            "success": True,
            "message": "Customer deactivated successfully.",
            "data": {
                "id": customer.id,
                "username": customer.username,
                "email": customer.email,
                "is_active": customer.is_active,
            },
        },
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    CanManageBookings,
])
def all_bookings(request):
    """
    Return all bookings using the new marketplace booking model.
    """

    bookings = (
        ServiceBooking.objects
        .select_related(
            "service_request",
            "service_request__category",
            "customer",
            "provider_profile",
            "provider_profile__provider",
            "quotation",
        )
        .order_by("-created_at")
    )

    bookings_data = []

    for booking in bookings:

        provider_user = (
            booking.provider_profile.provider
        )

        bookings_data.append(
            {
                "id": booking.id,

                "service_request_id": str(
                    booking.service_request.id
                ),

                "service_request_title": (
                    booking.service_request.title
                ),

                "service": {
                    "id": (
                        booking.service_request.category.id
                    ),
                    "name": (
                        booking.service_request.category.name
                    ),
                    "key": (
                        booking.service_request.category.key
                    ),
                },

                "customer": {
                    "id": booking.customer.id,
                    "username": (
                        booking.customer.username
                    ),
                    "email": (
                        booking.customer.email
                    ),
                    "full_name": (
                        booking.customer.get_full_name()
                        or booking.customer.username
                    ),
                },

                "provider": {
                    "id": provider_user.id,
                    "username": (
                        provider_user.username
                    ),
                    "email": (
                        provider_user.email
                    ),
                    "full_name": (
                        provider_user.get_full_name()
                        or provider_user.username
                    ),
                },

                "quotation_id": (
                    booking.quotation.id
                ),

                "final_price": (
                    booking.final_price
                ),

                "scheduled_date": (
                    booking.scheduled_date
                ),

                "scheduled_start_time": (
                    booking.scheduled_start_time
                ),

                "scheduled_end_time": (
                    booking.scheduled_end_time
                ),

                "status": booking.status,

                "cancellation_reason": (
                    booking.cancellation_reason
                ),

                "completed_at": (
                    booking.completed_at
                ),

                "created_at": (
                    booking.created_at
                ),

                "updated_at": (
                    booking.updated_at
                ),
            }
        )

    return Response(
        {
            "success": True,
            "message": (
                "Bookings fetched successfully."
            ),
            "count": bookings.count(),
            "bookings": bookings_data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    CanManageQuotes,
])
def all_quotes(request):
    """
    Return all provider quotations using
    the new marketplace quotation model.
    """

    quotations = (
        ProviderQuotation.objects
        .select_related(
            "service_request",
            "service_request__category",
            "service_request__customer",
            "provider_profile",
            "provider_profile__provider",
        )
        .order_by("-created_at")
    )

    quotations_data = []

    for quotation in quotations:

        provider_user = (
            quotation.provider_profile.provider
        )

        customer = (
            quotation.service_request.customer
        )

        quotations_data.append(
            {
                "id": quotation.id,

                "service_request_id": str(
                    quotation.service_request.id
                ),

                "service_request_title": (
                    quotation.service_request.title
                ),

                "service": {
                    "id": (
                        quotation
                        .service_request
                        .category
                        .id
                    ),
                    "name": (
                        quotation
                        .service_request
                        .category
                        .name
                    ),
                    "key": (
                        quotation
                        .service_request
                        .category
                        .key
                    ),
                },

                "customer": {
                    "id": customer.id,
                    "username": customer.username,
                    "email": customer.email,
                    "full_name": (
                        customer.get_full_name()
                        or customer.username
                    ),
                },

                "provider": {
                    "id": provider_user.id,
                    "username": (
                        provider_user.username
                    ),
                    "email": (
                        provider_user.email
                    ),
                    "full_name": (
                        provider_user.get_full_name()
                        or provider_user.username
                    ),
                },

                "quoted_price": (
                    quotation.quoted_price
                ),

                "message": (
                    quotation.message
                ),

                "estimated_duration_minutes": (
                    quotation
                    .estimated_duration_minutes
                ),

                "status": (
                    quotation.status
                ),

                "created_at": (
                    quotation.created_at
                ),

                "updated_at": (
                    quotation.updated_at
                ),
            }
        )

    return Response(
        {
            "success": True,
            "message": (
                "Quotations fetched successfully."
            ),
            "count": quotations.count(),
            "quotes": quotations_data,
        },
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    CanViewReports,
])
def provider_performance(request):
    """
    Provider leaderboard and performance analytics.

    Supports:
        ?period=7d
        ?period=30d
        ?period=6m
        ?period=1y
        ?from=YYYY-MM-DD
        ?to=YYYY-MM-DD
        ?service=plumber
    """

    # =========================================================
    # FILTERS
    # =========================================================

    dashboard_filters = get_dashboard_filters(
        request
    )

    # We calculate accepted/completed/cancelled metrics
    # ourselves, so don't apply generic status filtering.
    analytics_filters = {
        **dashboard_filters,
        "status": None,
        "provider_id": None,
    }

    # =========================================================
    # PROVIDERS
    # =========================================================

    providers = (
        User.objects
        .filter(
            role__in=provider_role_keys()
        )
        .order_by("username")
    )

    data = []

    for provider in providers:

        # =====================================================
        # QUOTATIONS
        # =====================================================

        quotations = (
            ProviderQuotation.objects
            .filter(
                provider_profile__provider=provider
            )
        )

        quotations = (
            filter_provider_quotations(
                quotations,
                analytics_filters,
            )
        )

        total_quotes = quotations.count()

        accepted_quotes = (
            quotations
            .filter(
                status="accepted"
            )
            .count()
        )

        # =====================================================
        # BOOKINGS
        # =====================================================

        bookings = (
            ServiceBooking.objects
            .filter(
                provider_profile__provider=provider
            )
        )

        bookings = (
            filter_service_bookings(
                bookings,
                analytics_filters,
            )
        )

        total_bookings = bookings.count()

        completed_bookings = (
            bookings
            .filter(
                status="completed"
            )
            .count()
        )

        cancelled_bookings = (
            bookings
            .filter(
                status="cancelled"
            )
            .count()
        )

        # =====================================================
        # BOOKING VALUE
        # =====================================================

        # Cancelled bookings are excluded from
        # provider booking-value calculations.

        booking_value_data = (
            bookings
            .exclude(
                status="cancelled"
            )
            .aggregate(
                total=Sum(
                    "final_price"
                ),
                average=Avg(
                    "final_price"
                ),
            )
        )

        total_booking_value = (
            booking_value_data["total"]
            or 0
        )

        average_booking_value = (
            booking_value_data["average"]
            or 0
        )

        # =====================================================
        # REVIEWS
        # =====================================================

        reviews = (
            ServiceReview.objects
            .filter(
                provider_profile__provider=provider
            )
        )

        reviews = (
            filter_service_reviews(
                reviews,
                analytics_filters,
            )
        )

        total_reviews = reviews.count()

        rating_data = (
            reviews.aggregate(
                average=Avg(
                    "rating"
                )
            )
        )

        average_rating = (
            rating_data["average"]
            or 0
        )

        average_rating = round(
            float(average_rating),
            2,
        )

        # =====================================================
        # QUOTATION ACCEPTANCE RATE
        # =====================================================

        quotation_acceptance_rate = 0

        if total_quotes > 0:
            quotation_acceptance_rate = round(
                (
                    accepted_quotes
                    / total_quotes
                )
                * 100,
                2,
            )

        # =====================================================
        # COMPLETION RATE
        # =====================================================

        completion_rate = 0

        if total_bookings > 0:
            completion_rate = round(
                (
                    completed_bookings
                    / total_bookings
                )
                * 100,
                2,
            )

        # =====================================================
        # CANCELLATION RATE
        # =====================================================

        cancellation_rate = 0

        if total_bookings > 0:
            cancellation_rate = round(
                (
                    cancelled_bookings
                    / total_bookings
                )
                * 100,
                2,
            )

        # =====================================================
        # PROVIDER DATA
        # =====================================================

        data.append(
            {
                "provider_id": provider.id,

                "provider": provider.username,

                "full_name": (
                    provider.get_full_name()
                    or provider.username
                ),

                "email": provider.email,

                "phone": provider.phone,

                "role": provider.role,

                "is_active": (
                    provider.is_active
                ),

                "is_approved": (
                    provider.is_approved
                ),

                "is_verified": (
                    provider.is_verified
                ),

                "profile_picture": (
                    request.build_absolute_uri(
                        provider.profile_picture.url
                    )
                    if provider.profile_picture
                    else None
                ),

                # ---------------------------------------------
                # QUOTATIONS
                # ---------------------------------------------

                "total_quotes": (
                    total_quotes
                ),

                "accepted_quotes": (
                    accepted_quotes
                ),

                "quotation_acceptance_rate": (
                    quotation_acceptance_rate
                ),

                # Keep old field for frontend compatibility.
                "acceptance_rate": (
                    quotation_acceptance_rate
                ),

                # ---------------------------------------------
                # BOOKINGS
                # ---------------------------------------------

                "total_bookings": (
                    total_bookings
                ),

                "completed_bookings": (
                    completed_bookings
                ),

                "cancelled_bookings": (
                    cancelled_bookings
                ),

                "completion_rate": (
                    completion_rate
                ),

                "cancellation_rate": (
                    cancellation_rate
                ),

                "total_booking_value": (
                    total_booking_value
                ),

                "average_booking_value": (
                    average_booking_value
                ),

                # ---------------------------------------------
                # REVIEWS
                # ---------------------------------------------

                "total_reviews": (
                    total_reviews
                ),

                "average_rating": (
                    average_rating
                ),
            }
        )

    # =========================================================
    # LEADERBOARD RANKING
    # =========================================================
    #
    # Ranking priority:
    # 1. Completed bookings
    # 2. Total booking value
    # 3. Average rating
    # 4. Quotation acceptance rate
    #

    data.sort(
        key=lambda item: (
            item["completed_bookings"],
            float(
                item["total_booking_value"]
            ),
            item["average_rating"],
            item[
                "quotation_acceptance_rate"
            ],
        ),
        reverse=True,
    )

    for index, provider_data in enumerate(
        data,
        start=1,
    ):
        provider_data["rank"] = index

    # =========================================================
    # SUMMARY
    # =========================================================

    total_provider_booking_value = sum(
        (
            item["total_booking_value"]
            for item in data
        ),
        start=0,
    )

    total_completed_jobs = sum(
        item["completed_bookings"]
        for item in data
    )

    total_cancelled_jobs = sum(
        item["cancelled_bookings"]
        for item in data
    )

    # =========================================================
    # RESPONSE
    # =========================================================

    return Response(
        {
            "success": True,

            "message": (
                "Provider leaderboard and "
                "performance fetched successfully."
            ),

            "filters": {
                "period": (
                    dashboard_filters[
                        "period"
                    ]
                ),

                "from": (
                    dashboard_filters[
                        "start_date"
                    ]
                ),

                "to": (
                    dashboard_filters[
                        "end_date"
                    ]
                ),

                "service": (
                    dashboard_filters[
                        "service"
                    ]
                ),
            },

            "summary": {
                "total_providers": (
                    len(data)
                ),

                "total_completed_jobs": (
                    total_completed_jobs
                ),

                "total_cancelled_jobs": (
                    total_cancelled_jobs
                ),

                "total_booking_value": (
                    total_provider_booking_value
                ),
            },

            "count": len(data),

            "providers": data,
        },
        status=status.HTTP_200_OK,
    )
@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    IsAdminUser,
])
def marketplace_monitor_api(request):
    """
    Return recent bookings, quotations, and provider summary.

    Optional:
        ?sections=bookings,quotes,providers
    """

    sections_param = (
        request.query_params.get("sections", "")
        or ""
    ).strip()

    sections = {
        part.strip().lower()
        for part in sections_param.split(",")
        if part.strip()
    }

    include_all = not sections
    payload = {}

    if include_all or "bookings" in sections:
        bookings = (
            ServiceBooking.objects
            .select_related(
                "service_request",
                "service_request__category",
                "customer",
                "provider_profile",
                "provider_profile__provider",
            )
            .order_by("-created_at")[:50]
        )

        payload["bookings"] = [
            {
                "id": booking.id,
                "service_request_id": str(
                    booking.service_request.id
                ),
                "service": {
                    "id": booking.service_request.category.id,
                    "name": booking.service_request.category.name,
                    "key": booking.service_request.category.key,
                },
                "customer": {
                    "id": booking.customer.id,
                    "username": booking.customer.username,
                },
                "provider": {
                    "id": booking.provider_profile.provider.id,
                    "username": (
                        booking.provider_profile.provider.username
                    ),
                },
                "final_price": booking.final_price,
                "status": booking.status,
                "created_at": booking.created_at,
            }
            for booking in bookings
        ]

    if include_all or "quotes" in sections:
        quotations = (
            ProviderQuotation.objects
            .select_related(
                "service_request",
                "service_request__category",
                "service_request__customer",
                "provider_profile",
                "provider_profile__provider",
            )
            .order_by("-created_at")[:50]
        )

        payload["quotes"] = [
            {
                "id": quotation.id,
                "service_request_id": str(
                    quotation.service_request.id
                ),
                "service": {
                    "id": quotation.service_request.category.id,
                    "name": quotation.service_request.category.name,
                    "key": quotation.service_request.category.key,
                },
                "customer": {
                    "id": quotation.service_request.customer.id,
                    "username": (
                        quotation.service_request.customer.username
                    ),
                },
                "provider": {
                    "id": quotation.provider_profile.provider.id,
                    "username": (
                        quotation.provider_profile.provider.username
                    ),
                },
                "quoted_price": quotation.quoted_price,
                "status": quotation.status,
                "created_at": quotation.created_at,
            }
            for quotation in quotations
        ]

    if include_all or "providers" in sections:
        providers = (
            User.objects
            .filter(role__in=provider_role_keys())
            .order_by("username")
        )

        provider_rows = []

        for provider in providers:
            provider_bookings = ServiceBooking.objects.filter(
                provider_profile__provider=provider
            )
            provider_quotes = ProviderQuotation.objects.filter(
                provider_profile__provider=provider
            )
            provider_reviews = ServiceReview.objects.filter(
                provider_profile__provider=provider
            )

            provider_rows.append(
                {
                    "provider_id": provider.id,
                    "provider": provider.username,
                    "role": provider.role,
                    "total_quotes": provider_quotes.count(),
                    "accepted_quotes": provider_quotes.filter(
                        status="accepted"
                    ).count(),
                    "total_bookings": provider_bookings.count(),
                    "completed_bookings": provider_bookings.filter(
                        status="completed"
                    ).count(),
                    "cancelled_bookings": provider_bookings.filter(
                        status="cancelled"
                    ).count(),
                    "average_rating": round(
                        float(
                            provider_reviews.aggregate(
                                average=Avg("rating")
                            )["average"]
                            or 0
                        ),
                        2,
                    ),
                }
            )

        payload["providers"] = provider_rows

    return Response(
        {
            "success": True,
            "message": "Marketplace monitor fetched successfully.",
            "data": payload,
        },
        status=status.HTTP_200_OK,
    )



from .models import SpotlightImage
from .serializers import AdminUserSerializer, CreateAdminUserSerializer, SpotlightImageSerializer, UpdateAdminUserSerializer
from .permissions import IsAdminUser

# ==========================================================
# SPOTLIGHT IMAGES
# ==========================================================


@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    IsAdminUser,
])
def spotlight_list_api(request):

    spotlights = SpotlightImage.objects.all()

    serializer = SpotlightImageSerializer(
        spotlights,
        many=True,
        context={"request": request},
    )
    serialized = serializer.data

    return Response(
        {
            "success": True,
            "message": "Spotlight images fetched successfully.",
            "count": len(serialized),
            "data": serialized,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([
    IsAuthenticated,
    CanManageSpotlights,
])
def spotlight_create_api(request):

    serializer = SpotlightImageSerializer(
        data=request.data,
        context={"request": request},
    )

    if not serializer.is_valid():
        return Response(
            {
                "success": False,
                "message": "Spotlight image creation failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    spotlight = serializer.save()

    return Response(
        {
            "success": True,
            "message": "Spotlight image created successfully.",
            "data": SpotlightImageSerializer(
                spotlight,
                context={"request": request},
            ).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH", "PUT"])
@permission_classes([
    IsAuthenticated,
    IsAdminUser,
])
def spotlight_update_api(request, spotlight_id):

    try:
        spotlight = SpotlightImage.objects.get(
            id=spotlight_id
        )

    except SpotlightImage.DoesNotExist:
        return Response(
            {
                "success": False,
                "message": "Spotlight image not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = SpotlightImageSerializer(
        spotlight,
        data=request.data,
        partial=request.method == "PATCH",
        context={"request": request},
    )

    if not serializer.is_valid():
        return Response(
            {
                "success": False,
                "message": "Spotlight image update failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    spotlight = serializer.save()

    return Response(
        {
            "success": True,
            "message": "Spotlight image updated successfully.",
            "data": SpotlightImageSerializer(
                spotlight,
                context={"request": request},
            ).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["DELETE"])
@permission_classes([
    IsAuthenticated,
    IsAdminUser,
])
def spotlight_delete_api(request, spotlight_id):

    try:
        spotlight = SpotlightImage.objects.get(
            id=spotlight_id
        )

    except SpotlightImage.DoesNotExist:
        return Response(
            {
                "success": False,
                "message": "Spotlight image not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # Delete actual image file from storage
    if spotlight.image:
        spotlight.image.delete(
            save=False
        )

    spotlight.delete()

    return Response(
        {
            "success": True,
            "message": "Spotlight image deleted successfully.",
        },
        status=status.HTTP_200_OK,
    )

# =========================================
# PUBLIC SPOTLIGHT IMAGES
# =========================================

@api_view(["GET"])
@permission_classes([AllowAny])
def public_spotlights_api(request):

    spotlights = (
        SpotlightImage.objects
        .filter(is_active=True)
        .order_by("display_order", "-created_at")
    )

    serializer = SpotlightImageSerializer(
        spotlights,
        many=True,
        context={"request": request},
    )
    serialized = serializer.data

    return Response(
        {
            "success": True,
            "message": "Active spotlight images fetched successfully.",
            "count": len(serialized),
            "data": serialized,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def home_catalog_api(request):
    """
    Public home catalog:
    active services, popular services,
    coming-soon services, and spotlights.
    """

    active_services = (
        ServiceCategory.objects
        .filter(status="active")
        .order_by("display_order", "name")
    )

    popular_services = (
        ServiceCategory.objects
        .filter(
            status="active",
            is_popular=True,
        )
        .order_by("display_order", "name")
    )

    coming_soon_services = (
        ServiceCategory.objects
        .filter(status="coming_soon")
        .order_by("display_order", "name")
    )

    spotlights = (
        SpotlightImage.objects
        .filter(is_active=True)
        .order_by("display_order", "-created_at")
    )

    def serialize_service(service):
        return {
            "id": service.id,
            "name": service.name,
            "key": service.key,
            "description": service.description,
            "service_image": (
                request.build_absolute_uri(
                    service.service_image.url
                )
                if service.service_image
                else None
            ),
            "status": service.status,
            "start_date": service.start_date,
            "display_order": service.display_order,
            "is_popular": service.is_popular,
            "is_available": (
                service.status == "active"
            ),
        }

    serializer = SpotlightImageSerializer(
        spotlights,
        many=True,
        context={"request": request},
    )

    return Response(
        {
            "success": True,
            "message": "Home catalog fetched successfully.",
            "data": {
                "active_services": [
                    serialize_service(service)
                    for service in active_services
                ],
                "popular_services": [
                    serialize_service(service)
                    for service in popular_services
                ],
                "coming_soon_services": [
                    serialize_service(service)
                    for service in coming_soon_services
                ],
                "spotlights": serializer.data,
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def popular_services_api(request):
    """
    Return active service categories marked as popular.
    """

    services = (
        ServiceCategory.objects
        .filter(
            status="active",
            is_popular=True,
        )
        .order_by(
            "display_order",
            "name",
        )
    )

    data = []

    for service in services:

        service_image = None

        if service.service_image:
            service_image = request.build_absolute_uri(
                service.service_image.url
            )

        data.append(
            {
                "id": service.id,
                "name": service.name,
                "key": service.key,
                "description": service.description,
                "service_image": service_image,
                "status": service.status,
                "start_date": service.start_date,
                "display_order": service.display_order,
                "is_popular": service.is_popular,
            }
        )

    return Response(
        {
            "success": True,
            "message": "Popular services fetched successfully.",
            "count": len(data),
            "data": data,
        },
        status=status.HTTP_200_OK,
    )
@api_view(["GET"])
@permission_classes([AllowAny])
def public_services_api(request):
    """
    Public customer-facing service list.

    Query params:

    status=active
        -> only active services

    status=all
        -> active + coming soon services

    popular=true
        -> only active popular services

    Default:
        -> active + coming soon services
    """

    status_filter = (
        request.query_params.get("status")
        or "all"
    ).strip().lower()

    popular_filter = (
        request.query_params.get("popular")
        or ""
    ).strip().lower()

    # =========================================================
    # BASE QUERYSET
    # =========================================================

    services = ServiceCategory.objects.all()

    # =========================================================
    # POPULAR SERVICES
    # =========================================================

    if popular_filter in [
        "true",
        "1",
        "yes",
    ]:
        services = services.filter(
            status="active",
            is_popular=True,
        )

    # =========================================================
    # ACTIVE ONLY
    # =========================================================

    elif status_filter == "active":
        services = services.filter(
            status="active",
        )

    # =========================================================
    # ACTIVE + COMING SOON
    # =========================================================

    else:
        services = services.filter(
            status__in=[
                "active",
                "coming_soon",
            ]
        )

    # =========================================================
    # ORDERING
    # =========================================================

    services = services.order_by(
        "display_order",
        "name",
    )

    # =========================================================
    # RESPONSE DATA
    # =========================================================

    data = []

    for service in services:

        service_image = None

        if service.service_image:
            service_image = (
                request.build_absolute_uri(
                    service.service_image.url
                )
            )

        data.append(
            {
                "id": service.id,
                "name": service.name,
                "key": service.key,
                "description": service.description,
                "service_image": service_image,
                "status": service.status,
                "start_date": service.start_date,
                "display_order": service.display_order,
                "is_popular": service.is_popular,
                "is_available": (
                    service.status == "active"
                ),
            }
        )

    return Response(
        {
            "success": True,
            "message": "Services fetched successfully.",
            "filters": {
                "status": status_filter,
                "popular": (
                    popular_filter
                    in [
                        "true",
                        "1",
                        "yes",
                    ]
                ),
            },
            "count": len(data),
            "data": data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    CanManageAdminUsers,
])
def admin_users_api(request):
    """
    Return all staff admin users except superusers.
    """

    admin_users = (
        User.objects
        .filter(
            is_staff=True,
            is_superuser=False,
        )
        .select_related(
            "admin_permission_profile"
        )
        .order_by(
            "-date_joined"
        )
    )

    serializer = AdminUserSerializer(
        admin_users,
        many=True,
    )
    serialized = serializer.data

    return Response(
        {
            "success": True,
            "message": "Admin users fetched successfully.",
            "count": len(serialized),
            "data": serialized,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([
    IsAuthenticated,
    CanManageAdminUsers,
])
@transaction.atomic
def create_admin_user_api(request):
    """
    Create a new permission-based admin user.
    """

    serializer = CreateAdminUserSerializer(
        data=request.data
    )

    if not serializer.is_valid():
        return Response(
            {
                "success": False,
                "message": "Admin user creation failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    admin_user = serializer.save()

    return Response(
        {
            "success": True,
            "message": "Admin user created successfully.",
            "data": AdminUserSerializer(
                admin_user
            ).data,
        },
        status=status.HTTP_201_CREATED,
    )

@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    CanManageAdminUsers,
])
def admin_user_detail_api(
    request,
    admin_id,
):
    """
    Return one admin user's details and permissions.
    """

    try:
        admin_user = (
            User.objects
            .select_related(
                "admin_permission_profile"
            )
            .get(
                id=admin_id,
                is_staff=True,
                is_superuser=False,
            )
        )

    except User.DoesNotExist:
        return Response(
            {
                "success": False,
                "message": "Admin user not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        {
            "success": True,
            "message": "Admin user fetched successfully.",
            "data": AdminUserSerializer(
                admin_user
            ).data,
        },
        status=status.HTTP_200_OK,
    )

@api_view(["PATCH"])
@permission_classes([
    IsAuthenticated,
    CanManageAdminUsers,
])
@transaction.atomic
def update_admin_user_api(
    request,
    admin_id,
):
    """
    Update admin details and permissions.
    """

    try:
        admin_user = (
            User.objects
            .select_for_update()
            .get(
                id=admin_id,
                is_staff=True,
                is_superuser=False,
            )
        )

    except User.DoesNotExist:
        return Response(
            {
                "success": False,
                "message": "Admin user not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = UpdateAdminUserSerializer(
        admin_user,
        data=request.data,
        partial=True,
        context={
            "user": admin_user,
        },
    )

    if not serializer.is_valid():
        return Response(
            {
                "success": False,
                "message": "Admin user update failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    admin_user = serializer.save()

    return Response(
        {
            "success": True,
            "message": "Admin user updated successfully.",
            "data": AdminUserSerializer(
                admin_user
            ).data,
        },
        status=status.HTTP_200_OK,
    )

@api_view(["POST"])
@permission_classes([
    IsAuthenticated,
    CanManageAdminUsers,
])
def activate_admin_user_api(
    request,
    admin_id,
):

    try:
        admin_user = User.objects.get(
            id=admin_id,
            is_staff=True,
            is_superuser=False,
        )

    except User.DoesNotExist:
        return Response(
            {
                "success": False,
                "message": "Admin user not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    admin_user.is_active = True

    admin_user.save(
        update_fields=[
            "is_active",
        ]
    )

    return Response(
        {
            "success": True,
            "message": "Admin user activated successfully.",
            "data": AdminUserSerializer(
                admin_user
            ).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([
    IsAuthenticated,
    CanManageAdminUsers,
])
def deactivate_admin_user_api(
    request,
    admin_id,
):

    try:
        admin_user = User.objects.get(
            id=admin_id,
            is_staff=True,
            is_superuser=False,
        )

    except User.DoesNotExist:
        return Response(
            {
                "success": False,
                "message": "Admin user not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # Prevent admin from disabling themselves.
    if admin_user.id == request.user.id:
        return Response(
            {
                "success": False,
                "message": (
                    "You cannot deactivate your own account."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    admin_user.is_active = False

    admin_user.save(
        update_fields=[
            "is_active",
        ]
    )

    return Response(
        {
            "success": True,
            "message": "Admin user deactivated successfully.",
            "data": AdminUserSerializer(
                admin_user
            ).data,
        },
        status=status.HTTP_200_OK,
    )

@api_view(["DELETE"])
@permission_classes([
    IsAuthenticated,
    CanManageAdminUsers,
])
@transaction.atomic
def delete_admin_user_api(
    request,
    admin_id,
):

    try:
        admin_user = User.objects.get(
            id=admin_id,
            is_staff=True,
            is_superuser=False,
        )

    except User.DoesNotExist:
        return Response(
            {
                "success": False,
                "message": "Admin user not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if admin_user.id == request.user.id:
        return Response(
            {
                "success": False,
                "message": (
                    "You cannot delete your own account."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    admin_user.delete()

    return Response(
        {
            "success": True,
            "message": "Admin user deleted successfully.",
        },
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    CanManageCustomers,
])
def customer_detail_api(request, customer_id):
    """
    Return one customer's complete admin-editable details.
    """

    customer = (
        User.objects
        .filter(
            id=customer_id,
            role="customer",
        )
        .first()
    )

    if not customer:
        return Response(
            {
                "success": False,
                "message": "Customer not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        {
            "success": True,
            "message": "Customer fetched successfully.",
            "data": {
                "id": customer.id,
                "username": customer.username,
                "email": customer.email,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "full_name": (
                    customer.get_full_name()
                    or customer.username
                ),
                "phone": customer.phone,
                "address": customer.address,
                "profile_picture": (
                    request.build_absolute_uri(
                        customer.profile_picture.url
                    )
                    if customer.profile_picture
                    else None
                ),
                "is_active": customer.is_active,
                "is_email_verified": (
                    customer.is_email_verified
                ),
                "date_joined": customer.date_joined,
                "last_login": customer.last_login,
            },
        },
        status=status.HTTP_200_OK,
    )

@api_view(["PATCH"])
@permission_classes([
    IsAuthenticated,
    CanManageCustomers,
])
def update_customer_api(request, customer_id):
    """
    Update editable customer information.
    """

    customer = (
        User.objects
        .filter(
            id=customer_id,
            role="customer",
        )
        .first()
    )

    if not customer:
        return Response(
            {
                "success": False,
                "message": "Customer not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # ---------------------------------------------------------
    # USERNAME
    # ---------------------------------------------------------

    if "username" in request.data:

        username = (
            request.data.get("username")
            or ""
        ).strip()

        if not username:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Username cannot be empty."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            User.objects
            .filter(
                username__iexact=username
            )
            .exclude(
                id=customer.id
            )
            .exists()
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Username already exists."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer.username = username

    # ---------------------------------------------------------
    # EMAIL
    # ---------------------------------------------------------

    if "email" in request.data:

        email = (
            request.data.get("email")
            or ""
        ).strip().lower()

        if not email:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Email cannot be empty."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            User.objects
            .filter(
                email__iexact=email
            )
            .exclude(
                id=customer.id
            )
            .exists()
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Email already exists."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # If admin changes customer email,
        # require re-verification.
        if email != customer.email.lower():
            customer.email = email
            customer.is_email_verified = False

    # ---------------------------------------------------------
    # BASIC PROFILE
    # ---------------------------------------------------------

    if "first_name" in request.data:
        customer.first_name = (
            request.data.get("first_name")
            or ""
        ).strip()

    if "last_name" in request.data:
        customer.last_name = (
            request.data.get("last_name")
            or ""
        ).strip()

    if "phone" in request.data:
        customer.phone = (
            request.data.get("phone")
            or ""
        ).strip()

    if "address" in request.data:
        customer.address = (
            request.data.get("address")
            or ""
        ).strip()

    # ---------------------------------------------------------
    # PROFILE PICTURE
    # ---------------------------------------------------------

    profile_picture = request.FILES.get(
        "profile_picture"
    )

    if profile_picture:
        customer.profile_picture = (
            profile_picture
        )

    # ---------------------------------------------------------
    # SAVE
    # ---------------------------------------------------------

    customer.save()

    # ---------------------------------------------------------
    # RESPONSE
    # ---------------------------------------------------------

    return Response(
        {
            "success": True,
            "message": (
                "Customer updated successfully."
            ),
            "data": {
                "id": customer.id,
                "username": customer.username,
                "email": customer.email,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "full_name": (
                    customer.get_full_name()
                    or customer.username
                ),
                "phone": customer.phone,
                "address": customer.address,
                "profile_picture": (
                    request.build_absolute_uri(
                        customer.profile_picture.url
                    )
                    if customer.profile_picture
                    else None
                ),
                "is_active": customer.is_active,
                "is_email_verified": (
                    customer.is_email_verified
                ),
            },
        },
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    CanManageProviders,
])
def provider_detail_api(request, provider_id):
    """
    Return one provider's details for admin management.
    """

    provider = (
        User.objects
        .filter(
            id=provider_id,
            role__in=provider_role_keys(),
        )
        .first()
    )

    if not provider:
        return Response(
            {
                "success": False,
                "message": "Provider not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        {
            "success": True,
            "message": (
                "Provider fetched successfully."
            ),
            "data": {
                "id": provider.id,
                "username": provider.username,
                "email": provider.email,

                "first_name": provider.first_name,
                "last_name": provider.last_name,

                "full_name": (
                    provider.get_full_name()
                    or provider.username
                ),

                "phone": provider.phone,
                "address": provider.address,

                "role": provider.role,

                "bio": provider.bio,

                "experience_years": (
                    provider.experience_years
                ),

                "is_email_verified": (
                    provider.is_email_verified
                ),

                "is_approved": provider.is_approved,
                "is_verified": provider.is_verified,
                "is_active": provider.is_active,

                "status_note": (
                    provider.status_note or ""
                ),

                "deactivate_reason": (
                    provider.deactivate_reason or ""
                ),

                "profile_picture": (
                    request.build_absolute_uri(
                        provider.profile_picture.url
                    )
                    if provider.profile_picture
                    else None
                ),

                "date_joined": provider.date_joined,
                "last_login": provider.last_login,
            },
        },
        status=status.HTTP_200_OK,
    )

@api_view(["PATCH"])
@permission_classes([
    IsAuthenticated,
    CanManageProviders,
])
def update_provider_api(request, provider_id):
    """
    Allow an authorized admin to edit provider data.
    """

    provider = (
        User.objects
        .filter(
            id=provider_id,
            role__in=provider_role_keys(),
        )
        .first()
    )

    if not provider:
        return Response(
            {
                "success": False,
                "message": "Provider not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # =========================================================
    # USERNAME
    # =========================================================

    if "username" in request.data:

        username = (
            request.data.get("username")
            or ""
        ).strip()

        if not username:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Username cannot be empty."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            User.objects
            .filter(
                username__iexact=username
            )
            .exclude(id=provider.id)
            .exists()
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Username already exists."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        provider.username = username

    # =========================================================
    # EMAIL
    # =========================================================

    if "email" in request.data:

        email = (
            request.data.get("email")
            or ""
        ).strip().lower()

        if not email:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Email cannot be empty."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            User.objects
            .filter(
                email__iexact=email
            )
            .exclude(id=provider.id)
            .exists()
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Email already exists."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if email != provider.email.lower():

            provider.email = email

            # New email must be verified again.
            provider.is_email_verified = False

    # =========================================================
    # BASIC PROFILE
    # =========================================================

    if "first_name" in request.data:
        provider.first_name = (
            request.data.get("first_name")
            or ""
        ).strip()

    if "last_name" in request.data:
        provider.last_name = (
            request.data.get("last_name")
            or ""
        ).strip()

    if "phone" in request.data:
        provider.phone = (
            request.data.get("phone")
            or ""
        ).strip()

    if "address" in request.data:
        provider.address = (
            request.data.get("address")
            or ""
        ).strip()

    if "bio" in request.data:
        provider.bio = (
            request.data.get("bio")
            or ""
        ).strip()

    # =========================================================
    # EXPERIENCE
    # =========================================================

    if "experience_years" in request.data:

        experience_years = request.data.get(
            "experience_years"
        )

        if experience_years in [
            "",
            None,
        ]:
            provider.experience_years = None

        else:
            try:
                experience_years = int(
                    experience_years
                )
            except (TypeError, ValueError):
                return Response(
                    {
                        "success": False,
                        "message": (
                            "Experience years must "
                            "be a valid number."
                        ),
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )

            if experience_years < 0:
                return Response(
                    {
                        "success": False,
                        "message": (
                            "Experience years cannot "
                            "be negative."
                        ),
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )

            provider.experience_years = (
                experience_years
            )

    # =========================================================
    # PROFILE PICTURE
    # =========================================================

    profile_picture = request.FILES.get(
        "profile_picture"
    )

    if profile_picture:
        provider.profile_picture = (
            profile_picture
        )

    # =========================================================
    # SAVE
    # =========================================================

    provider.save()

    return Response(
        {
            "success": True,
            "message": (
                "Provider updated successfully."
            ),
            "data": {
                "id": provider.id,
                "username": provider.username,
                "email": provider.email,

                "first_name": provider.first_name,
                "last_name": provider.last_name,

                "full_name": (
                    provider.get_full_name()
                    or provider.username
                ),

                "phone": provider.phone,
                "address": provider.address,

                "role": provider.role,

                "bio": provider.bio,

                "experience_years": (
                    provider.experience_years
                ),

                "profile_picture": (
                    request.build_absolute_uri(
                        provider.profile_picture.url
                    )
                    if provider.profile_picture
                    else None
                ),

                "is_email_verified": (
                    provider.is_email_verified
                ),

                "is_approved": provider.is_approved,
                "is_verified": provider.is_verified,
                "is_active": provider.is_active,
            },
        },
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    CanViewReports,
])
def service_performance_api(request):
    """
    Return performance analytics for marketplace services.

    Supports:
        ?period=7d
        ?period=30d
        ?period=6m
        ?period=1y
        ?from=YYYY-MM-DD
        ?to=YYYY-MM-DD
        ?service=plumber
    """

    dashboard_filters = get_dashboard_filters(
        request
    )

    # We calculate status-specific metrics ourselves below.
    # Do not let a generic ?status filter accidentally
    # remove completed/cancelled bookings before aggregation.
    analytics_filters = {
        **dashboard_filters,
        "status": None,
    }

    # =========================================================
    # SERVICE QUERYSET
    # =========================================================

    services = (
        ServiceCategory.objects
        .all()
        .order_by(
            "display_order",
            "name",
        )
    )

    # If a particular service was requested,
    # return analytics only for that service.

    service_filter = dashboard_filters.get(
        "service"
    )

    if service_filter:
        services = services.filter(
            key__iexact=service_filter
        )

    data = []

    # =========================================================
    # SERVICE PERFORMANCE
    # =========================================================

    for service in services:

        # -----------------------------------------------------
        # REQUESTS
        # -----------------------------------------------------

        requests_queryset = (
            CustomerServiceRequest.objects
            .filter(
                category=service
            )
        )

        requests_queryset = (
            filter_service_requests(
                requests_queryset,
                analytics_filters,
            )
        )

        total_requests = (
            requests_queryset.count()
        )

        # -----------------------------------------------------
        # QUOTATIONS
        # -----------------------------------------------------

        quotations_queryset = (
            ProviderQuotation.objects
            .filter(
                service_request__category=service
            )
        )

        quotations_queryset = (
            filter_provider_quotations(
                quotations_queryset,
                analytics_filters,
            )
        )

        total_quotations = (
            quotations_queryset.count()
        )

        accepted_quotations = (
            quotations_queryset
            .filter(
                status="accepted"
            )
            .count()
        )

        # -----------------------------------------------------
        # BOOKINGS
        # -----------------------------------------------------

        bookings_queryset = (
            ServiceBooking.objects
            .filter(
                service_request__category=service
            )
        )

        bookings_queryset = (
            filter_service_bookings(
                bookings_queryset,
                analytics_filters,
            )
        )

        total_bookings = (
            bookings_queryset.count()
        )

        completed_jobs = (
            bookings_queryset
            .filter(
                status="completed"
            )
            .count()
        )

        cancelled_jobs = (
            bookings_queryset
            .filter(
                status="cancelled"
            )
            .count()
        )

        # -----------------------------------------------------
        # BOOKING VALUE
        # -----------------------------------------------------

        booking_value_result = (
            bookings_queryset
            .exclude(
                status="cancelled"
            )
            .aggregate(
                total=Sum(
                    "final_price"
                )
            )
        )

        total_booking_value = (
            booking_value_result["total"]
            or 0
        )

        # -----------------------------------------------------
        # REVIEWS
        # -----------------------------------------------------

        reviews_queryset = (
            ServiceReview.objects
            .filter(
                booking__service_request__category=service
            )
        )

        reviews_queryset = (
            filter_service_reviews(
                reviews_queryset,
                analytics_filters,
            )
        )

        total_reviews = (
            reviews_queryset.count()
        )

        rating_result = (
            reviews_queryset.aggregate(
                average=Avg(
                    "rating"
                )
            )
        )

        average_rating = (
            rating_result["average"]
            or 0
        )

        average_rating = round(
            float(average_rating),
            2,
        )

        # -----------------------------------------------------
        # REQUEST -> BOOKING CONVERSION RATE
        # -----------------------------------------------------

        conversion_rate = 0

        if total_requests > 0:
            conversion_rate = round(
                (
                    total_bookings
                    / total_requests
                )
                * 100,
                2,
            )

        # -----------------------------------------------------
        # QUOTATION ACCEPTANCE RATE
        # -----------------------------------------------------

        quotation_acceptance_rate = 0

        if total_quotations > 0:
            quotation_acceptance_rate = round(
                (
                    accepted_quotations
                    / total_quotations
                )
                * 100,
                2,
            )

        # -----------------------------------------------------
        # COMPLETION RATE
        # -----------------------------------------------------

        completion_rate = 0

        if total_bookings > 0:
            completion_rate = round(
                (
                    completed_jobs
                    / total_bookings
                )
                * 100,
                2,
            )

        # -----------------------------------------------------
        # CANCELLATION RATE
        # -----------------------------------------------------

        cancellation_rate = 0

        if total_bookings > 0:
            cancellation_rate = round(
                (
                    cancelled_jobs
                    / total_bookings
                )
                * 100,
                2,
            )

        # -----------------------------------------------------
        # RESPONSE ITEM
        # -----------------------------------------------------

        data.append(
            {
                "service_id": service.id,
                "service_name": service.name,
                "service_key": service.key,
                "status": service.status,
                "is_popular": service.is_popular,

                "total_requests": total_requests,

                "total_quotations": (
                    total_quotations
                ),

                "accepted_quotations": (
                    accepted_quotations
                ),

                "quotation_acceptance_rate": (
                    quotation_acceptance_rate
                ),

                "total_bookings": (
                    total_bookings
                ),

                "completed_jobs": (
                    completed_jobs
                ),

                "cancelled_jobs": (
                    cancelled_jobs
                ),

                "completion_rate": (
                    completion_rate
                ),

                "cancellation_rate": (
                    cancellation_rate
                ),

                "total_booking_value": (
                    total_booking_value
                ),

                "total_reviews": (
                    total_reviews
                ),

                "average_rating": (
                    average_rating
                ),

                "conversion_rate": (
                    conversion_rate
                ),
            }
        )

    # =========================================================
    # RANK SERVICES
    # =========================================================

    data.sort(
        key=lambda item: (
            item["total_bookings"],
            float(item["total_booking_value"]),
            item["average_rating"],
        ),
        reverse=True,
    )

    for index, item in enumerate(
        data,
        start=1,
    ):
        item["rank"] = index

    # =========================================================
    # RESPONSE
    # =========================================================

    return Response(
        {
            "success": True,
            "message": (
                "Service performance analytics "
                "fetched successfully."
            ),

            "filters": {
                "period": (
                    dashboard_filters["period"]
                ),

                "from": (
                    dashboard_filters[
                        "start_date"
                    ]
                ),

                "to": (
                    dashboard_filters[
                        "end_date"
                    ]
                ),

                "service": (
                    dashboard_filters["service"]
                ),
            },

            "count": len(data),

            "services": data,
        },
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    CanViewReports,
])
def service_request_funnel_api(request):
    """
    Marketplace conversion funnel.

    Supports:
        ?period=7d
        ?period=30d
        ?period=6m
        ?period=1y
        ?from=YYYY-MM-DD
        ?to=YYYY-MM-DD
        ?service=plumber
    """

    dashboard_filters = get_dashboard_filters(
        request
    )

    # We calculate stage statuses ourselves.
    analytics_filters = {
        **dashboard_filters,
        "status": None,
        "provider_id": None,
    }

    # =========================================================
    # REQUESTS
    # =========================================================

    requests_queryset = filter_service_requests(
        CustomerServiceRequest.objects.all(),
        analytics_filters,
    )

    total_requests = requests_queryset.count()

    request_ids = requests_queryset.values_list(
        "id",
        flat=True,
    )

    # =========================================================
    # QUOTED REQUESTS
    # =========================================================
    # Count requests that received at least one quotation,
    # not the total number of quotations.

    quoted_requests = (
        ProviderQuotation.objects
        .filter(
            service_request_id__in=request_ids
        )
        .values(
            "service_request_id"
        )
        .distinct()
        .count()
    )

    # =========================================================
    # ACCEPTED / BOOKED REQUESTS
    # =========================================================
    # A booking represents a request that successfully
    # progressed beyond quotation selection.

    booking_queryset = (
        ServiceBooking.objects
        .filter(
            service_request_id__in=request_ids
        )
    )

    accepted_requests = (
        booking_queryset
        .values(
            "service_request_id"
        )
        .distinct()
        .count()
    )

    # =========================================================
    # IN-PROGRESS REQUESTS
    # =========================================================

    in_progress_requests = (
        booking_queryset
        .filter(
            status="in_progress"
        )
        .values(
            "service_request_id"
        )
        .distinct()
        .count()
    )

    # =========================================================
    # COMPLETED REQUESTS
    # =========================================================

    completed_requests = (
        booking_queryset
        .filter(
            status="completed"
        )
        .values(
            "service_request_id"
        )
        .distinct()
        .count()
    )

    # =========================================================
    # CANCELLED REQUESTS
    # =========================================================

    cancelled_requests = (
        booking_queryset
        .filter(
            status="cancelled"
        )
        .values(
            "service_request_id"
        )
        .distinct()
        .count()
    )

    # =========================================================
    # HELPER FUNCTIONS
    # =========================================================

    def percentage(value, total):
        if total <= 0:
            return 0

        return round(
            (value / total) * 100,
            2,
        )

    def drop_off(previous, current):
        if previous <= 0:
            return 0

        return round(
            (
                (previous - current)
                / previous
            )
            * 100,
            2,
        )

    # =========================================================
    # FUNNEL
    # =========================================================

    funnel = [
        {
            "stage": "requests",
            "label": "Requests",
            "count": total_requests,
            "overall_conversion_rate": 100.0,
            "previous_stage_conversion_rate": 100.0,
            "drop_off_rate": 0,
        },
        {
            "stage": "quoted",
            "label": "Quoted",
            "count": quoted_requests,
            "overall_conversion_rate": percentage(
                quoted_requests,
                total_requests,
            ),
            "previous_stage_conversion_rate": percentage(
                quoted_requests,
                total_requests,
            ),
            "drop_off_rate": drop_off(
                total_requests,
                quoted_requests,
            ),
        },
        {
            "stage": "accepted",
            "label": "Accepted / Booked",
            "count": accepted_requests,
            "overall_conversion_rate": percentage(
                accepted_requests,
                total_requests,
            ),
            "previous_stage_conversion_rate": percentage(
                accepted_requests,
                quoted_requests,
            ),
            "drop_off_rate": drop_off(
                quoted_requests,
                accepted_requests,
            ),
        },
        {
            "stage": "in_progress",
            "label": "In Progress",
            "count": in_progress_requests,
            "overall_conversion_rate": percentage(
                in_progress_requests,
                total_requests,
            ),
            "previous_stage_conversion_rate": percentage(
                in_progress_requests,
                accepted_requests,
            ),
            "drop_off_rate": drop_off(
                accepted_requests,
                in_progress_requests,
            ),
        },
        {
            "stage": "completed",
            "label": "Completed",
            "count": completed_requests,
            "overall_conversion_rate": percentage(
                completed_requests,
                total_requests,
            ),
            "previous_stage_conversion_rate": percentage(
                completed_requests,
                in_progress_requests,
            ),
            "drop_off_rate": drop_off(
                in_progress_requests,
                completed_requests,
            ),
        },
    ]

    # =========================================================
    # RESPONSE
    # =========================================================

    return Response(
        {
            "success": True,
            "message": (
                "Service request funnel "
                "fetched successfully."
            ),

            "filters": {
                "period": dashboard_filters["period"],
                "from": dashboard_filters["start_date"],
                "to": dashboard_filters["end_date"],
                "service": dashboard_filters["service"],
            },

            "summary": {
                "total_requests": total_requests,
                "quoted_requests": quoted_requests,
                "accepted_requests": accepted_requests,
                "in_progress_requests": in_progress_requests,
                "completed_requests": completed_requests,
                "cancelled_requests": cancelled_requests,

                "request_to_booking_rate": percentage(
                    accepted_requests,
                    total_requests,
                ),

                "request_to_completion_rate": percentage(
                    completed_requests,
                    total_requests,
                ),
            },

            "funnel": funnel,
        },
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    CanViewReports,
])
def customer_analytics_api(request):
    """
    Customer analytics for the admin dashboard.

    Supports:
        ?period=7d
        ?period=30d
        ?period=6m
        ?period=1y
        ?from=YYYY-MM-DD
        ?to=YYYY-MM-DD
        ?service=plumber
    """

    dashboard_filters = get_dashboard_filters(
        request
    )

    analytics_filters = {
        **dashboard_filters,
        "status": None,
        "provider_id": None,
    }

    # =========================================================
    # ALL CUSTOMERS
    # =========================================================

    customers = (
        User.objects
        .filter(
            role="customer"
        )
    )

    total_customers = customers.count()

    active_customers = (
        customers
        .filter(
            is_active=True
        )
        .count()
    )

    inactive_customers = (
        customers
        .filter(
            is_active=False
        )
        .count()
    )

    # =========================================================
    # NEW CUSTOMERS IN SELECTED PERIOD
    # =========================================================

    start_date = dashboard_filters.get(
        "start_date"
    )

    end_date = dashboard_filters.get(
        "end_date"
    )

    new_customers_queryset = customers

    if start_date:
        new_customers_queryset = (
            new_customers_queryset
            .filter(
                date_joined__date__gte=start_date
            )
        )

    if end_date:
        new_customers_queryset = (
            new_customers_queryset
            .filter(
                date_joined__date__lte=end_date
            )
        )

    new_customers = (
        new_customers_queryset.count()
    )

    # =========================================================
    # FILTERED BOOKINGS
    # =========================================================

    bookings = (
        filter_service_bookings(
            ServiceBooking.objects.all(),
            analytics_filters,
        )
    )

    # =========================================================
    # CUSTOMERS WITH BOOKINGS
    # =========================================================

    customer_ids_with_bookings = (
        bookings
        .values_list(
            "customer_id",
            flat=True,
        )
        .distinct()
    )

    customers_with_bookings = (
        customers
        .filter(
            id__in=customer_ids_with_bookings
        )
        .count()
    )

    customers_with_no_bookings = (
        total_customers
        - customers_with_bookings
    )

    # =========================================================
    # REPEAT CUSTOMERS
    # =========================================================
    # Repeat customer = customer with at least 2 bookings
    # in the selected analytics period.

    repeat_customer_rows = (
        bookings
        .values(
            "customer_id"
        )
        .annotate(
            booking_count=Count("id")
        )
        .filter(
            booking_count__gte=2
        )
    )

    repeat_customers = (
        repeat_customer_rows.count()
    )

    # =========================================================
    # REPEAT BOOKING RATE
    # =========================================================

    repeat_booking_rate = 0

    if customers_with_bookings > 0:
        repeat_booking_rate = round(
            (
                repeat_customers
                / customers_with_bookings
            )
            * 100,
            2,
        )

    # =========================================================
    # CUSTOMER BOOKING ANALYTICS
    # =========================================================

    customer_booking_data = (
        bookings
        .values(
            "customer_id"
        )
        .annotate(
            total_bookings=Count(
                "id"
            ),

            completed_bookings=Count(
                "id",
                filter=Q(
                    status="completed"
                ),
            ),

            cancelled_bookings=Count(
                "id",
                filter=Q(
                    status="cancelled"
                ),
            ),

            total_spend=Sum(
                "final_price",
                filter=~Q(
                    status="cancelled"
                ),
            ),

            average_booking_value=Avg(
                "final_price",
                filter=~Q(
                    status="cancelled"
                ),
            ),
        )
    )

    # =========================================================
    # BUILD TOP CUSTOMER DATA
    # =========================================================

    customer_map = {
        customer.id: customer
        for customer in customers
    }

    top_customers = []

    for item in customer_booking_data:

        customer = customer_map.get(
            item["customer_id"]
        )

        if not customer:
            continue

        total_spend = (
            item["total_spend"]
            or 0
        )

        average_booking_value = (
            item["average_booking_value"]
            or 0
        )

        top_customers.append(
            {
                "customer_id": customer.id,

                "username": (
                    customer.username
                ),

                "full_name": (
                    customer.get_full_name()
                    or customer.username
                ),

                "email": customer.email,

                "phone": customer.phone,

                "is_active": (
                    customer.is_active
                ),

                "profile_picture": (
                    request.build_absolute_uri(
                        customer.profile_picture.url
                    )
                    if customer.profile_picture
                    else None
                ),

                "total_bookings": (
                    item["total_bookings"]
                ),

                "completed_bookings": (
                    item["completed_bookings"]
                ),

                "cancelled_bookings": (
                    item["cancelled_bookings"]
                ),

                "total_spend": (
                    total_spend
                ),

                "average_booking_value": (
                    average_booking_value
                ),
            }
        )

    # =========================================================
    # RANK TOP CUSTOMERS
    # =========================================================

    top_customers.sort(
        key=lambda item: (
            float(item["total_spend"]),
            item["total_bookings"],
        ),
        reverse=True,
    )

    for index, customer in enumerate(
        top_customers,
        start=1,
    ):
        customer["rank"] = index

    # Keep dashboard response manageable.
    top_customers = top_customers[:10]

    # =========================================================
    # RESPONSE
    # =========================================================

    return Response(
        {
            "success": True,

            "message": (
                "Customer analytics "
                "fetched successfully."
            ),

            "filters": {
                "period": (
                    dashboard_filters[
                        "period"
                    ]
                ),

                "from": (
                    dashboard_filters[
                        "start_date"
                    ]
                ),

                "to": (
                    dashboard_filters[
                        "end_date"
                    ]
                ),

                "service": (
                    dashboard_filters[
                        "service"
                    ]
                ),
            },

            "summary": {
                "total_customers": (
                    total_customers
                ),

                "active_customers": (
                    active_customers
                ),

                "inactive_customers": (
                    inactive_customers
                ),

                "new_customers": (
                    new_customers
                ),

                "customers_with_bookings": (
                    customers_with_bookings
                ),

                "customers_with_no_bookings": (
                    customers_with_no_bookings
                ),

                "repeat_customers": (
                    repeat_customers
                ),

                "repeat_booking_rate": (
                    repeat_booking_rate
                ),
            },

            "top_customers": (
                top_customers
            ),
        },
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    CanViewReports,
])
def geographic_analytics_api(request):
    """
    Geographic marketplace demand analytics.

    Supports:
        ?period=7d
        ?period=30d
        ?period=6m
        ?period=1y
        ?from=YYYY-MM-DD
        ?to=YYYY-MM-DD
        ?service=plumber

    Returns:
        - demand by city/state
        - completed/cancelled requests
        - unique customers
        - top service per area
        - map points for frontend heatmaps
    """

    # =========================================================
    # FILTERS
    # =========================================================

    dashboard_filters = get_dashboard_filters(
        request
    )

    analytics_filters = {
        **dashboard_filters,
        "status": None,
        "provider_id": None,
    }

    # =========================================================
    # FILTERED SERVICE REQUESTS
    # =========================================================

    service_requests = (
        filter_service_requests(
            CustomerServiceRequest.objects
            .select_related(
                "category",
                "customer",
            ),
            analytics_filters,
        )
    )

    # Ignore records without useful geographic information.
    geographic_requests = (
        service_requests
        .exclude(
            city=""
        )
    )

    # =========================================================
    # GENERAL SUMMARY
    # =========================================================

    total_requests = (
        geographic_requests.count()
    )

    total_cities = (
        geographic_requests
        .values(
            "city",
            "state",
        )
        .distinct()
        .count()
    )

    total_states = (
        geographic_requests
        .values(
            "state"
        )
        .exclude(
            state=""
        )
        .distinct()
        .count()
    )

    # =========================================================
    # DEMAND BY CITY
    # =========================================================

    city_rows = (
        geographic_requests
        .values(
            "city",
            "state",
        )
        .annotate(
            total_requests=Count(
                "id"
            ),

            unique_customers=Count(
                "customer_id",
                distinct=True,
            ),

            completed_requests=Count(
                "id",
                filter=Q(
                    status="completed"
                ),
            ),

            cancelled_requests=Count(
                "id",
                filter=Q(
                    status="cancelled"
                ),
            ),

            urgent_requests=Count(
                "id",
                filter=Q(
                    urgency="urgent"
                ),
            ),

            emergency_requests=Count(
                "id",
                filter=Q(
                    urgency="emergency"
                ),
            ),
        )
        .order_by(
            "-total_requests"
        )
    )

    # =========================================================
    # BUILD CITY ANALYTICS
    # =========================================================

    cities = []

    for city_row in city_rows:

        city_name = city_row["city"]
        state_name = city_row["state"]

        # -----------------------------------------------------
        # FIND TOP SERVICE IN THIS CITY
        # -----------------------------------------------------

        city_service_data = (
            geographic_requests
            .filter(
                city=city_name,
                state=state_name,
            )
            .values(
                "category__id",
                "category__name",
                "category__key",
            )
            .annotate(
                request_count=Count(
                    "id"
                )
            )
            .order_by(
                "-request_count"
            )
            .first()
        )

        top_service = None

        if city_service_data:
            top_service = {
                "service_id": (
                    city_service_data[
                        "category__id"
                    ]
                ),

                "service_name": (
                    city_service_data[
                        "category__name"
                    ]
                ),

                "service_key": (
                    city_service_data[
                        "category__key"
                    ]
                ),

                "request_count": (
                    city_service_data[
                        "request_count"
                    ]
                ),
            }

        # -----------------------------------------------------
        # COMPLETION RATE
        # -----------------------------------------------------

        completion_rate = 0

        if city_row["total_requests"] > 0:
            completion_rate = round(
                (
                    city_row[
                        "completed_requests"
                    ]
                    / city_row[
                        "total_requests"
                    ]
                )
                * 100,
                2,
            )

        # -----------------------------------------------------
        # CANCELLATION RATE
        # -----------------------------------------------------

        cancellation_rate = 0

        if city_row["total_requests"] > 0:
            cancellation_rate = round(
                (
                    city_row[
                        "cancelled_requests"
                    ]
                    / city_row[
                        "total_requests"
                    ]
                )
                * 100,
                2,
            )

        cities.append(
            {
                "city": city_name,
                "state": state_name,

                "total_requests": (
                    city_row[
                        "total_requests"
                    ]
                ),

                "unique_customers": (
                    city_row[
                        "unique_customers"
                    ]
                ),

                "completed_requests": (
                    city_row[
                        "completed_requests"
                    ]
                ),

                "cancelled_requests": (
                    city_row[
                        "cancelled_requests"
                    ]
                ),

                "urgent_requests": (
                    city_row[
                        "urgent_requests"
                    ]
                ),

                "emergency_requests": (
                    city_row[
                        "emergency_requests"
                    ]
                ),

                "completion_rate": (
                    completion_rate
                ),

                "cancellation_rate": (
                    cancellation_rate
                ),

                "top_service": (
                    top_service
                ),
            }
        )

    # =========================================================
    # DEMAND BY STATE
    # =========================================================

    states = list(
        geographic_requests
        .exclude(
            state=""
        )
        .values(
            "state"
        )
        .annotate(
            total_requests=Count(
                "id"
            ),

            unique_customers=Count(
                "customer_id",
                distinct=True,
            ),
        )
        .order_by(
            "-total_requests"
        )
    )

    # =========================================================
    # MAP / HEATMAP POINTS
    # =========================================================
    #
    # Frontend can use these points for:
    # - heatmap
    # - markers
    # - demand visualization
    #

    map_queryset = (
        geographic_requests
        .exclude(
            latitude__isnull=True
        )
        .exclude(
            longitude__isnull=True
        )
    )

    map_points = []

    for item in map_queryset:

        map_points.append(
            {
                "request_id": str(
                    item.id
                ),

                "latitude": float(
                    item.latitude
                ),

                "longitude": float(
                    item.longitude
                ),

                "city": item.city,

                "state": item.state,

                "postal_code": (
                    item.postal_code
                ),

                "service": {
                    "id": (
                        item.category.id
                    ),

                    "name": (
                        item.category.name
                    ),

                    "key": (
                        item.category.key
                    ),
                },

                "status": item.status,

                "urgency": item.urgency,
            }
        )

    # =========================================================
    # TOP DEMAND LOCATION
    # =========================================================

    top_location = None

    if cities:
        top_location = cities[0]

    # =========================================================
    # RESPONSE
    # =========================================================

    return Response(
        {
            "success": True,

            "message": (
                "Geographic analytics "
                "fetched successfully."
            ),

            "filters": {
                "period": (
                    dashboard_filters[
                        "period"
                    ]
                ),

                "from": (
                    dashboard_filters[
                        "start_date"
                    ]
                ),

                "to": (
                    dashboard_filters[
                        "end_date"
                    ]
                ),

                "service": (
                    dashboard_filters[
                        "service"
                    ]
                ),
            },

            "summary": {
                "total_requests": (
                    total_requests
                ),

                "total_cities": (
                    total_cities
                ),

                "total_states": (
                    total_states
                ),

                "map_points": (
                    len(map_points)
                ),

                "top_demand_location": (
                    top_location
                ),
            },

            "cities": cities,

            "states": states,

            "map_points": map_points,
        },
        status=status.HTTP_200_OK,
    )