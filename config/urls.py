from django.contrib import admin
from django.urls import path, include
from core.views import health

urlpatterns = [
  path("admin/", admin.site.urls),
  path("health/", health),
  path("", include("accounts.urls")),
  path("", include("django.contrib.auth.urls")),
]
