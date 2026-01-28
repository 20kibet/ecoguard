# views.py - FIXED & COMPLETE (AI Processor Removed)

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Avg, Max, Min, Count
from datetime import timedelta
import json
import csv
from io import StringIO

from .models import (
    EcoGuardianDevice, EnvironmentalData, ControlDevice, 
    AlertLog, SystemConfiguration, ExamSchedule, AITrainingModel
)


# ============================================
# MAIN VIEWS
# ============================================

def home(request):
    """Home page"""
    return render(request, 'ecoguardian/home.html')


def dashboard(request):
    """Main dashboard"""
    devices = EcoGuardianDevice.objects.all()
    recent_alerts = AlertLog.objects.filter(is_resolved=False)[:10]
    config = SystemConfiguration.objects.first()
    
    context = {
        'devices': devices,
        'recent_alerts': recent_alerts,
        'config': config,
    }
    return render(request, 'ecoguardian/dashboard.html', context)


def admin_dashboard(request):
    """Admin control panel"""
    devices = ControlDevice.objects.all()
    alerts = AlertLog.objects.all()[:20]
    config = SystemConfiguration.objects.first()
    
    stats = {
        'total_devices': EcoGuardianDevice.objects.count(),
        'online_devices': sum(1 for d in EcoGuardianDevice.objects.all() if d.is_online()),
        'total_readings': EnvironmentalData.objects.count(),
        'unresolved_alerts': AlertLog.objects.filter(is_resolved=False).count(),
    }
    
    context = {
        'devices': devices,
        'alerts': alerts,
        'config': config,
        'stats': stats,
    }
    return render(request, 'ecoguardian/admin_dashboard.html', context)


# ============================================
# API ENDPOINTS - DATA RECEPTION
# ============================================

@csrf_exempt
@require_http_methods(["POST"])
def receive_sensor_data(request):
    """
    Main API endpoint to receive sensor data from Arduino/IoT devices
    Accepts JSON: {"device_id": "arduino_01", "temperature": 25.5, "air_quality": 45.0, "noise_level": 50.0}
    """
    try:
        data = json.loads(request.body)
        
        # Get or create device
        device_id = data.get('device_id', 'default_device')
        device, created = EcoGuardianDevice.objects.get_or_create(
            device_id=device_id,
            defaults={
                'device_name': f'Device {device_id}',
                'location': 'Unknown Location'
            }
        )
        
        # Update last_seen
        device.last_seen = timezone.now()
        device.save()
        
        # Create environmental data reading
        env_data = EnvironmentalData.objects.create(
            device=device,
            temperature=float(data.get('temperature', 0)),
            air_quality=float(data.get('air_quality', 0)),
            noise_level=float(data.get('noise_level', 0))
        )
        
        # Get system configuration
        config = SystemConfiguration.objects.first()
        if not config:
            config = SystemConfiguration.objects.create()
        
        # Simple rule-based analysis (AI processor disabled)
        env_data.is_anomaly = False
        env_data.ai_score = None
        env_data.anomaly_type = None
        
        # Basic threshold checks
        if env_data.temperature > config.temp_threshold:
            env_data.is_anomaly = True
            env_data.anomaly_type = 'high_temperature'
        elif env_data.noise_level > config.noise_threshold:
            env_data.is_anomaly = True
            env_data.anomaly_type = 'high_noise'
        elif env_data.air_quality > config.air_quality_threshold:
            env_data.is_anomaly = True
            env_data.anomaly_type = 'poor_air_quality'
        
        env_data.save()
        
        # Run automation logic
        automation_results = run_automation(env_data, config)
        
        return JsonResponse({
            "status": "success",
            "reading_id": env_data.id,
            "device_id": device_id,
            "timestamp": env_data.timestamp.isoformat(),
            "ai_analysis": {
                "is_anomaly": env_data.is_anomaly,
                "score": env_data.ai_score,
            } if config.ai_analysis_enabled else None,
            "automation": automation_results,
            "reading_count": EnvironmentalData.objects.filter(device=device).count()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ============================================
# AUTOMATION LOGIC
# ============================================

def run_automation(env_data, config):
    """Core automation logic - triggers devices and alerts"""
    results = {
        "ac_activated": False,
        "ventilation_activated": False,
        "alerts_sent": []
    }
    
    # Check for exam period (stricter thresholds)
    ongoing_exam = ExamSchedule.objects.filter(
        start_time__lte=timezone.now(),
        end_time__gte=timezone.now(),
        is_active=True
    ).first()
    
    noise_threshold = (
        ongoing_exam.strict_noise_threshold 
        if ongoing_exam 
        else config.noise_threshold
    )
    
    # 1. TEMPERATURE CONTROL
    if env_data.temperature > config.temp_threshold and config.auto_ac_enabled:
        activate_device('AC')
        env_data.ac_activated = True
        results["ac_activated"] = True
        
        if config.alerts_enabled and should_send_alert('TEMP_HIGH', config):
            send_alert('TEMP_HIGH', env_data, 
                      f"High temperature: {env_data.temperature}°C. AC activated.", 
                      config)
            results["alerts_sent"].append("temperature")
    
    # 2. AIR QUALITY CONTROL
    if env_data.air_quality > config.air_quality_threshold and config.auto_ventilation_enabled:
        activate_device('FAN')
        env_data.ventilation_activated = True
        results["ventilation_activated"] = True
        
        if config.alerts_enabled and should_send_alert('AIR_POOR', config):
            send_alert('AIR_POOR', env_data,
                      f"Poor air quality: {env_data.air_quality} AQI. Ventilation activated.",
                      config)
            results["alerts_sent"].append("air_quality")
    
    # 3. NOISE CONTROL
    if env_data.noise_level > noise_threshold:
        if config.alerts_enabled and should_send_alert('NOISE_HIGH', config):
            send_alert('NOISE_HIGH', env_data,
                      f"High noise: {env_data.noise_level} dB detected!",
                      config, severity='high')
            env_data.alert_sent = True
            results["alerts_sent"].append("noise")
    
    # 4. ANOMALY DETECTION (rule-based)
    if env_data.is_anomaly and config.ai_analysis_enabled:
        if config.alerts_enabled and should_send_alert('ANOMALY', config):
            send_alert('ANOMALY', env_data,
                      f"Anomaly detected: {env_data.anomaly_type}",
                      config, severity='medium')
            results["alerts_sent"].append("anomaly")
    
    env_data.save()
    return results


def activate_device(device_type):
    """Activate control devices by type"""
    devices = ControlDevice.objects.filter(device_type=device_type)
    
    for device in devices:
        device.is_active = True
        device.last_activated = timezone.now()
        device.save()
    
    print(f"✅ {device_type} activated: {devices.count()} units")


def should_send_alert(alert_type, config):
    """Check if enough time has passed since last alert (prevent spam)"""
    cooldown_time = timezone.now() - timedelta(minutes=config.alert_cooldown_minutes)
    
    recent_alert = AlertLog.objects.filter(
        alert_type=alert_type,
        created_at__gte=cooldown_time
    ).first()
    
    return recent_alert is None


def send_alert(alert_type, env_data, message, config, severity='medium'):
    """Send alerts via multiple channels"""
    alerts_created = []
    
    # Make sure env_data is saved first
    if env_data.id is None:
        env_data.save()
    
    try:
        # SMS to guard
        alert = AlertLog.objects.create(
            data=env_data,
            alert_type=alert_type,
            severity=severity,
            channel='SMS',
            message=message,
            recipient=config.guard_phone
        )
        alerts_created.append(alert)
        
        # Email to admin
        alert = AlertLog.objects.create(
            data=env_data,
            alert_type=alert_type,
            severity=severity,
            channel='EMAIL',
            message=message,
            recipient=config.admin_email
        )
        alerts_created.append(alert)
        
        print(f"📢 Alert sent: {alert_type} - {message}")
    except Exception as e:
        print(f" Error sending alert: {e}")
    
    return alerts_created

# ============================================
# API ENDPOINTS - DATA RETRIEVAL
# ============================================

def get_latest_data(request, device_id=None):
    """Get latest sensor reading(s)"""
    if device_id:
        try:
            device = EcoGuardianDevice.objects.get(device_id=device_id)
            reading = EnvironmentalData.objects.filter(device=device).latest('timestamp')
            
            return JsonResponse({
                "device_id": device.device_id,
                "device_name": device.device_name,
                "location": device.location,
                "reading": {
                    "temperature": reading.temperature,
                    "air_quality": reading.air_quality,
                    "noise_level": reading.noise_level,
                    "timestamp": reading.timestamp.isoformat(),
                    "is_anomaly": reading.is_anomaly,
                    "ai_score": reading.ai_score,
                }
            })
        except EcoGuardianDevice.DoesNotExist:
            return JsonResponse({"error": "Device not found"}, status=404)
        except EnvironmentalData.DoesNotExist:
            return JsonResponse({"error": "No data available"}, status=404)
    else:
        # Get latest from all devices
        devices = EcoGuardianDevice.objects.all()
        data = []
        
        for device in devices:
            try:
                reading = EnvironmentalData.objects.filter(device=device).latest('timestamp')
                data.append({
                    "device_id": device.device_id,
                    "device_name": device.device_name,
                    "temperature": reading.temperature,
                    "air_quality": reading.air_quality,
                    "noise_level": reading.noise_level,
                    "timestamp": reading.timestamp.isoformat(),
                })
            except EnvironmentalData.DoesNotExist:
                continue
        
        return JsonResponse({"devices": data, "count": len(data)})


def get_live_data(request, device_id):
    """Get live data for a specific device"""
    return get_latest_data(request, device_id)


def get_ai_insights(request, device_id):
    """Get insights for a device (simple statistical analysis)"""
    try:
        device = EcoGuardianDevice.objects.get(device_id=device_id)
        
        # Get historical data (last 24 hours)
        time_threshold = timezone.now() - timedelta(hours=24)
        historical_data = EnvironmentalData.objects.filter(
            device=device,
            timestamp__gte=time_threshold
        ).order_by('timestamp')
        
        if not historical_data:
            return JsonResponse({"error": "No data available for analysis"}, status=404)
        
        # Prepare data for analysis
        data_list = list(historical_data.values(
            'timestamp', 'temperature', 'air_quality', 'noise_level'
        ))
        
        # Simple statistical analysis
        avg_temp = sum(d['temperature'] for d in data_list) / len(data_list)
        avg_air = sum(d['air_quality'] for d in data_list) / len(data_list)
        avg_noise = sum(d['noise_level'] for d in data_list) / len(data_list)
        
        max_temp = max(d['temperature'] for d in data_list)
        max_air = max(d['air_quality'] for d in data_list)
        max_noise = max(d['noise_level'] for d in data_list)
        
        insights = {
            "averages": {
                "temperature": round(avg_temp, 2),
                "air_quality": round(avg_air, 2),
                "noise_level": round(avg_noise, 2)
            },
            "maximums": {
                "temperature": round(max_temp, 2),
                "air_quality": round(max_air, 2),
                "noise_level": round(max_noise, 2)
            }
        }
        
        # Generate simple recommendations
        recommendations = []
        if avg_temp > 26:
            recommendations.append("Average temperature is high. Consider improving cooling.")
        if avg_noise > 60:
            recommendations.append("Noise levels are elevated. Implement noise reduction measures.")
        if avg_air > 55:
            recommendations.append("Air quality needs attention. Increase ventilation.")
        
        if not recommendations:
            recommendations.append("All parameters are within normal range.")
        
        return JsonResponse({
            "device_id": device_id,
            "analysis_period": "24 hours",
            "insights": insights,
            "recommendations": recommendations,
            "data_points": len(data_list)
        })
        
    except EcoGuardianDevice.DoesNotExist:
        return JsonResponse({"error": "Device not found"}, status=404)


def get_dashboard_summary(request):
    """Get comprehensive dashboard summary"""
    # Get all devices
    devices = EcoGuardianDevice.objects.all()
    device_count = devices.count()
    online_count = sum(1 for d in devices if d.is_online())
    
    # Get recent data (last hour)
    time_threshold = timezone.now() - timedelta(hours=1)
    recent_readings = EnvironmentalData.objects.filter(timestamp__gte=time_threshold)
    
    # Calculate averages
    avg_stats = recent_readings.aggregate(
        avg_temp=Avg('temperature'),
        avg_air=Avg('air_quality'),
        avg_noise=Avg('noise_level'),
        max_temp=Max('temperature'),
        max_noise=Max('noise_level')
    )
    
    # Get alerts
    unresolved_alerts = AlertLog.objects.filter(is_resolved=False).count()
    recent_alerts = list(AlertLog.objects.filter(
        created_at__gte=time_threshold
    ).values('alert_type', 'severity', 'message', 'created_at')[:5])
    
    # Get anomalies
    anomaly_count = recent_readings.filter(is_anomaly=True).count()
    
    # Get device statuses
    ac_active = ControlDevice.objects.filter(device_type='AC', is_active=True).count()
    fan_active = ControlDevice.objects.filter(device_type='FAN', is_active=True).count()
    
    return JsonResponse({
        "devices": {
            "total": device_count,
            "online": online_count,
            "offline": device_count - online_count
        },
        "current_averages": {
            "temperature": round(avg_stats['avg_temp'] or 0, 1),
            "air_quality": round(avg_stats['avg_air'] or 0, 1),
            "noise_level": round(avg_stats['avg_noise'] or 0, 1)
        },
        "alerts": {
            "unresolved": unresolved_alerts,
            "recent": recent_alerts
        },
        "anomalies": {
            "last_hour": anomaly_count
        },
        "control_systems": {
            "ac_units_active": ac_active,
            "ventilation_active": fan_active
        },
        "readings": {
            "last_hour": recent_readings.count(),
            "total": EnvironmentalData.objects.count()
        }
    })


# ============================================
# UTILITY ENDPOINTS
# ============================================

def device_status(request):
    """Get status of all devices"""
    devices = EcoGuardianDevice.objects.all()
    
    device_list = []
    for device in devices:
        latest = EnvironmentalData.objects.filter(device=device).order_by('-timestamp').first()
        
        device_list.append({
            "device_id": device.device_id,
            "device_name": device.device_name,
            "location": device.location,
            "is_online": device.is_online(),
            "last_seen": device.last_seen.isoformat(),
            "latest_reading": {
                "temperature": latest.temperature,
                "air_quality": latest.air_quality,
                "noise_level": latest.noise_level,
                "timestamp": latest.timestamp.isoformat()
            } if latest else None
        })
    
    return JsonResponse({"devices": device_list, "count": len(device_list)})


@csrf_exempt
def simulate_arduino_data(request):
    """Simulate Arduino data for testing"""
    import random
    
    test_data = {
        "device_id": "test_arduino",
        "temperature": round(random.uniform(20, 32), 1),
        "air_quality": round(random.uniform(30, 80), 1),
        "noise_level": round(random.uniform(40, 75), 1)
    }
    
    # Process through normal endpoint
    request._body = json.dumps(test_data).encode('utf-8')
    return receive_sensor_data(request)


def export_data(request, format='csv'):
    """Export data in CSV or JSON format"""
    from django.http import HttpResponse
    
    # Get time range from query params
    hours = int(request.GET.get('hours', 24))
    time_threshold = timezone.now() - timedelta(hours=hours)
    
    data = EnvironmentalData.objects.filter(
        timestamp__gte=time_threshold
    ).select_related('device').order_by('timestamp')
    
    if format == 'json':
        data_list = list(data.values(
            'device__device_id', 'device__device_name', 'device__location',
            'timestamp', 'temperature', 'air_quality', 'noise_level',
            'is_anomaly', 'ai_score'
        ))
        return JsonResponse({"data": data_list, "count": len(data_list)})
    
    elif format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="ecoguardian_data_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Timestamp', 'Device ID', 'Device Name', 'Location',
            'Temperature (°C)', 'Air Quality (AQI)', 'Noise Level (dB)',
            'Is Anomaly', 'AI Score'
        ])
        
        for reading in data:
            writer.writerow([
                reading.timestamp.isoformat(),
                reading.device.device_id,
                reading.device.device_name,
                reading.device.location,
                reading.temperature,
                reading.air_quality,
                reading.noise_level,
                reading.is_anomaly,
                reading.ai_score or 'N/A'
            ])
        
        return response
    
    return JsonResponse({"error": "Invalid format. Use 'csv' or 'json'"}, status=400)


def api_test(request):
    """Test API endpoint"""
    return JsonResponse({
        "status": "OK",
        "message": "EcoGuardian API is running",
        "timestamp": timezone.now().isoformat(),
        "endpoints": {
            "receive_data": "/api/data/",
            "latest_all": "/api/latest/",
            "latest_device": "/api/latest/<device_id>/",
            "dashboard_summary": "/api/summary/",
            "ai_insights": "/api/insights/<device_id>/",
            "device_status": "/api/devices/status/",
            "export": "/api/export/<format>/"
        }
    })


def health_check(request):
    """Health check endpoint"""
    try:
        # Check database
        device_count = EcoGuardianDevice.objects.count()
        reading_count = EnvironmentalData.objects.count()
        
        return JsonResponse({
            "status": "healthy",
            "database": "connected",
            "devices": device_count,
            "total_readings": reading_count,
            "timestamp": timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            "status": "unhealthy",
            "error": str(e)
        }, status=500)


def api_documentation(request):
    """API documentation page"""
    return render(request, 'ecoguardian/api_docs.html')