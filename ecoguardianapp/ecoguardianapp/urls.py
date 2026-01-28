from django.contrib import admin
from django.urls import path, include
from ecoguardian import views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Main views
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # API endpoints
    path('api/data/', views.receive_sensor_data, name='receive_data'),
    path('api/latest/', views.get_latest_data, name='latest_all'),
    path('api/latest/<str:device_id>/', views.get_latest_data, name='latest_device'),
    path('api/summary/', views.get_dashboard_summary, name='dashboard_summary'),
    path('api/test/', views.api_test, name='api_test'),
    path('health/', views.health_check, name='health_check'),
    
    # Additional endpoints (from Option 1)
    path('api/simulate/', views.simulate_arduino_data, name='simulate_data'),
    path('api/docs/', views.api_documentation, name='api_docs'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('api/devices/status/', views.device_status, name='device_status'),
    path('api/export/', views.export_data, name='export_data'),
    path('api/export/<str:format>/', views.export_data, name='export_format'),
]