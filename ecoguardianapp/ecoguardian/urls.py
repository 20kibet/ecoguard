# urls.py - FIXED & ORGANIZED

from django.contrib import admin
from django.urls import path
from ecoguardian import views

urlpatterns = [
    # ============================================
    # ADMIN
    # ============================================
    path('admin/', admin.site.urls, name='django_admin'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # ============================================
    # MAIN PAGES
    # ============================================
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # ============================================
    # API - DATA RECEPTION (Arduino/IoT)
    # ============================================
    path('api/data/', views.receive_sensor_data, name='receive_data'),
    path('api/simulate/', views.simulate_arduino_data, name='simulate_data'),
    
    # ============================================
    # API - DATA RETRIEVAL
    # ============================================
    path('api/latest/', views.get_latest_data, name='latest_all'),
    path('api/latest/<str:device_id>/', views.get_latest_data, name='latest_device'),
    path('api/live/<str:device_id>/', views.get_live_data, name='live_data'),
    path('api/summary/', views.get_dashboard_summary, name='dashboard_summary'),
    
    # ============================================
    # API - AI & INSIGHTS
    # ============================================
    path('api/insights/<str:device_id>/', views.get_ai_insights, name='ai_insights'),
    
    # ============================================
    # API - DEVICE MANAGEMENT
    # ============================================
    path('api/devices/status/', views.device_status, name='device_status'),
    
    # ============================================
    # API - EXPORT & UTILITIES
    # ============================================
    path('api/export/', views.export_data, name='export_data'),
    path('api/export/<str:format>/', views.export_data, name='export_format'),
    path('api/docs/', views.api_documentation, name='api_docs'),
    path('api/test/', views.api_test, name='api_test'),
    
    # ============================================
    # SYSTEM HEALTH
    # ============================================
    path('health/', views.health_check, name='health_check'),
]