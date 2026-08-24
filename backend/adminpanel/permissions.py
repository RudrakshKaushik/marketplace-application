from backend.cache_utils import cache_get, cache_set
from rest_framework.permissions import BasePermission


# ============================================================
# ADMIN PERMISSION NAMES
# ============================================================

ADMIN_PERMISSION_NAMES = [
    "manage_providers",
    "manage_customers",
    "manage_services",
    "manage_bookings",
    "manage_quotes",
    "view_reports",
    "manage_spotlights",
    "manage_admin_users",
]


# ============================================================
# ADMIN USER CHECK
# ============================================================

def is_admin_user(user):
    """
    Return True when the user is either:

    - Active Super Admin
    - Active Staff Admin
    """

    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and (
            user.is_superuser
            or user.is_staff
        )
    )


# ============================================================
# CHECK SINGLE ADMIN PERMISSION
# ============================================================

def has_admin_permission(
    user,
    permission_name,
):
    """
    Check one admin permission.

    Super Admin:
        Always allowed.

    Staff Admin:
        Permission comes from
        AdminPermissionProfile.
    """

    # User must first be an admin.
    if not is_admin_user(user):
        return False

    # Super Admin has full access.
    if user.is_superuser:
        return True

    # Safety check.
    if permission_name not in ADMIN_PERMISSION_NAMES:
        return False

    try:
        profile = (
            user.admin_permission_profile
        )

    except Exception:
        return False

    return bool(
        getattr(
            profile,
            permission_name,
            False,
        )
    )


# ============================================================
# GET ALL ADMIN PERMISSIONS
# ============================================================

ADMIN_PERMISSIONS_CACHE_TTL = 120


def get_admin_permissions(user):
    """
    Return all admin permissions.

    Used mainly for:
    - Admin dashboard response
    - Login response
    - Frontend sidebar/menu visibility

    Super Admin:
        Every permission = True

    Staff Admin:
        Permissions come from
        AdminPermissionProfile

    Non-admin:
        Every permission = False
    """

    # --------------------------------------------------------
    # NON-ADMIN USER
    # --------------------------------------------------------

    if not is_admin_user(user):

        return {
            permission: False
            for permission
            in ADMIN_PERMISSION_NAMES
        }

    # --------------------------------------------------------
    # SUPER ADMIN
    # --------------------------------------------------------

    if user.is_superuser:

        return {
            permission: True
            for permission
            in ADMIN_PERMISSION_NAMES
        }

    # --------------------------------------------------------
    # STAFF ADMIN
    # --------------------------------------------------------

    cache_key = f"admin:permissions:{user.id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        profile = (
            user.admin_permission_profile
        )

    except Exception:
        permissions = {
            permission: False
            for permission
            in ADMIN_PERMISSION_NAMES
        }
        cache_set(cache_key, permissions, ADMIN_PERMISSIONS_CACHE_TTL)
        return permissions

    # --------------------------------------------------------
    # RETURN PERMISSION PROFILE
    # --------------------------------------------------------

    permissions = {
        permission: bool(
            getattr(
                profile,
                permission,
                False,
            )
        )
        for permission
        in ADMIN_PERMISSION_NAMES
    }
    cache_set(cache_key, permissions, ADMIN_PERMISSIONS_CACHE_TTL)
    return permissions


# ============================================================
# GENERAL ADMIN ACCESS
# ============================================================

class IsAdminUser(BasePermission):
    """
    Allows active Super Admin or Staff Admin
    to access the admin panel.

    Specific actions are controlled using
    the permission classes below.
    """

    message = "Admin access required."

    def has_permission(
        self,
        request,
        view,
    ):
        return is_admin_user(
            request.user
        )


# ============================================================
# ADMIN USER MANAGEMENT
# ============================================================

class CanManageAdminUsers(BasePermission):

    message = (
        "You do not have permission "
        "to manage admin users."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return has_admin_permission(
            request.user,
            "manage_admin_users",
        )


# ============================================================
# PROVIDER MANAGEMENT
# ============================================================

class CanManageProviders(BasePermission):

    message = (
        "You do not have permission "
        "to manage providers."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return has_admin_permission(
            request.user,
            "manage_providers",
        )


# ============================================================
# CUSTOMER MANAGEMENT
# ============================================================

class CanManageCustomers(BasePermission):

    message = (
        "You do not have permission "
        "to manage customers."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return has_admin_permission(
            request.user,
            "manage_customers",
        )


# ============================================================
# SERVICE MANAGEMENT
# ============================================================

class CanManageServices(BasePermission):

    message = (
        "You do not have permission "
        "to manage services."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return has_admin_permission(
            request.user,
            "manage_services",
        )


# ============================================================
# BOOKING MANAGEMENT
# ============================================================

class CanManageBookings(BasePermission):

    message = (
        "You do not have permission "
        "to manage bookings."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return has_admin_permission(
            request.user,
            "manage_bookings",
        )


# ============================================================
# QUOTE MANAGEMENT
# ============================================================

class CanManageQuotes(BasePermission):

    message = (
        "You do not have permission "
        "to manage quotations."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return has_admin_permission(
            request.user,
            "manage_quotes",
        )


# ============================================================
# REPORT ACCESS
# ============================================================

class CanViewReports(BasePermission):

    message = (
        "You do not have permission "
        "to view reports."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return has_admin_permission(
            request.user,
            "view_reports",
        )


# ============================================================
# SPOTLIGHT MANAGEMENT
# ============================================================

class CanManageSpotlights(BasePermission):

    message = (
        "You do not have permission "
        "to manage spotlight images."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        return has_admin_permission(
            request.user,
            "manage_spotlights",
        )