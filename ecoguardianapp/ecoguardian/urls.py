# urls.py - Enhanced with new endpoints

from django.urls import path
from . import views

urlpatterns = [
    # Main dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Control panel
    path('control/', views.control_panel, name='control_panel'),
    
    # API endpoints
    path('api/receive/', views.receive_data, name='receive_data'),
    path('api/latest/', views.latest_data, name='latest_data'),
    path('api/manual-control/', views.manual_control, name='manual_control'),
    path('api/alerts/', views.alert_history, name='alert_history'),
    path('api/alerts/<int:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
]