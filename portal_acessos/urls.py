from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin-cat/", admin.site.urls),
    path("", include("usuarios.urls")),
]
