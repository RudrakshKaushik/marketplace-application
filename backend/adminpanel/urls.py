from django.urls import path

from .views import (
    # Dashboard
    admin_dashboard,
    customer_analytics_api,
    dashboard_trends_api,
    geographic_analytics_api,

    # Provider management
    pending_providers,
    all_providers,
    provider_detail_api,
    service_performance_api,
    service_request_funnel_api,
    update_provider_api,
    approve_provider,
    reject_provider,
    activate_provider,
    deactivate_provider,
    verify_provider,
    unverify_provider,
    provider_performance,

    # Customer management
    all_customers,
    customer_detail_api,
    update_customer_api,
    activate_customer,
    deactivate_customer,

    # Service category management
    service_categories,
    create_service_category,
    update_service_category,
    reorder_service_categories,
    delete_service_category,
    popular_services_api,
    public_services_api,
    home_catalog_api,

    # Marketplace
    all_bookings,
    all_quotes,
    marketplace_monitor_api,

    # Spotlight
    spotlight_list_api,
    spotlight_create_api,
    spotlight_update_api,
    spotlight_delete_api,
    public_spotlights_api,

    # Admin user management
    admin_users_api,
    create_admin_user_api,
    admin_user_detail_api,
    update_admin_user_api,
    activate_admin_user_api,
    deactivate_admin_user_api,
    delete_admin_user_api,
)


urlpatterns = [

    # =========================================================
    # ADMIN DASHBOARD
    # =========================================================

    path(
        "dashboard/",
        admin_dashboard,
        name="admin-dashboard",
    ),

    # =========================================================
    # PROVIDER MANAGEMENT
    # =========================================================

    path(
        "providers/",
        all_providers,
        name="all-providers",
    ),

    path(
        "providers/pending/",
        pending_providers,
        name="pending-providers",
    ),

    path(
        "providers/<int:provider_id>/",
        provider_detail_api,
        name="provider-detail",
    ),

    path(
        "providers/<int:provider_id>/update/",
        update_provider_api,
        name="update-provider",
    ),

    path(
        "providers/<int:provider_id>/approve/",
        approve_provider,
        name="approve-provider",
    ),

    path(
        "providers/<int:provider_id>/reject/",
        reject_provider,
        name="reject-provider",
    ),

    path(
        "providers/<int:provider_id>/activate/",
        activate_provider,
        name="activate-provider",
    ),

    path(
        "providers/<int:provider_id>/deactivate/",
        deactivate_provider,
        name="deactivate-provider",
    ),

    path(
        "providers/<int:provider_id>/verify/",
        verify_provider,
        name="verify-provider",
    ),

    path(
        "providers/<int:provider_id>/unverify/",
        unverify_provider,
        name="unverify-provider",
    ),

    path(
        "provider-performance/",
        provider_performance,
        name="provider-performance",
    ),

    # =========================================================
    # CUSTOMER MANAGEMENT
    # =========================================================

    path(
        "customers/",
        all_customers,
        name="all-customers",
    ),

    path(
        "customers/<int:customer_id>/",
        customer_detail_api,
        name="customer-detail",
    ),

    path(
        "customers/<int:customer_id>/update/",
        update_customer_api,
        name="update-customer",
    ),

    path(
        "customers/<int:customer_id>/activate/",
        activate_customer,
        name="activate-customer",
    ),

    path(
        "customers/<int:customer_id>/deactivate/",
        deactivate_customer,
        name="deactivate-customer",
    ),

    # =========================================================
    # SERVICE CATEGORY MANAGEMENT
    # =========================================================

    path(
        "services/",
        service_categories,
        name="service-categories",
    ),

    path(
        "services/create/",
        create_service_category,
        name="create-service-category",
    ),

    path(
        "services/reorder/",
        reorder_service_categories,
        name="reorder-service-categories",
    ),

    path(
        "services/<int:service_id>/update/",
        update_service_category,
        name="update-service-category",
    ),

    path(
        "services/<int:service_id>/delete/",
        delete_service_category,
        name="delete-service-category",
    ),

    # =========================================================
    # PUBLIC / POPULAR SERVICES
    # =========================================================

    path(
        "services/popular/",
        popular_services_api,
        name="popular-services",
    ),

    path(
        "services/public/",
        public_services_api,
        name="public-services",
    ),

    path(
        "catalog/home/",
        home_catalog_api,
        name="home-catalog",
    ),

    # =========================================================
    # BOOKINGS & QUOTES
    # =========================================================

    path(
        "marketplace/monitor/",
        marketplace_monitor_api,
        name="marketplace-monitor",
    ),

    path(
        "bookings/",
        all_bookings,
        name="all-bookings",
    ),

    path(
        "quotes/",
        all_quotes,
        name="all-quotes",
    ),

    # =========================================================
    # SPOTLIGHT MANAGEMENT
    # =========================================================

    path(
        "spotlights/",
        spotlight_list_api,
        name="spotlight-list",
    ),

    path(
        "spotlights/create/",
        spotlight_create_api,
        name="spotlight-create",
    ),

    path(
        "spotlights/<int:spotlight_id>/update/",
        spotlight_update_api,
        name="spotlight-update",
    ),

    path(
        "spotlights/<int:spotlight_id>/delete/",
        spotlight_delete_api,
        name="spotlight-delete",
    ),

    # =========================================================
    # PUBLIC SPOTLIGHTS
    # =========================================================

    path(
        "spotlights/public/",
        public_spotlights_api,
        name="public-spotlights",
    ),

    # =========================================================
    # ADMIN USER MANAGEMENT
    # =========================================================

    path(
        "admin-users/",
        admin_users_api,
        name="admin-users",
    ),

    path(
        "admin-users/create/",
        create_admin_user_api,
        name="create-admin-user",
    ),

    path(
        "admin-users/<int:admin_id>/",
        admin_user_detail_api,
        name="admin-user-detail",
    ),

    path(
        "admin-users/<int:admin_id>/update/",
        update_admin_user_api,
        name="update-admin-user",
    ),

    path(
        "admin-users/<int:admin_id>/activate/",
        activate_admin_user_api,
        name="activate-admin-user",
    ),

    path(
        "admin-users/<int:admin_id>/deactivate/",
        deactivate_admin_user_api,
        name="deactivate-admin-user",
    ),

    path(
        "admin-users/<int:admin_id>/delete/",
        delete_admin_user_api,
        name="delete-admin-user",
    ),
    path(
    "dashboard/trends/",
    dashboard_trends_api,
    name="dashboard-trends",
),
path(
    "dashboard/service-performance/",
    service_performance_api,
    name="dashboard-service-performance",
),
path(
    "dashboard/funnel/",
    service_request_funnel_api,
    name="dashboard-funnel",
),
path(
    "dashboard/customer-analytics/",
    customer_analytics_api,
    name="dashboard-customer-analytics",
),
path(
    "dashboard/geographic-analytics/",
    geographic_analytics_api,
    name="dashboard-geographic-analytics",
),
]