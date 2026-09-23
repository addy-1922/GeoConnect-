"""GeoConnect accounts: auth URL configuration (mounted at /api/auth/)."""

from django.urls import path

from . import views

urlpatterns = [
    path("csrf/", views.csrf_view, name="api-csrf"),
    path("register/", views.register_view, name="api-register"),
    path("login/", views.login_view, name="api-login"),
    path("logout/", views.logout_view, name="api-logout"),
]