from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("api/upload/", views.receive_data),
    path("api/latest/", views.latest_data),
]
