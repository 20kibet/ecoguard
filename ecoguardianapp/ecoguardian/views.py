# views.py - Enhanced with automation and alerts

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
import json

from .models import (
    SensorReading, ControlDevice, AlertLog, 
    SystemConfiguration, ExamSchedule
)


# Dashboard page
def dashboard(request):
    return render(request, "ecoguardian/dashboard.html")


# Control panel page
def control_panel(request):
    devices = ControlDevice.objects.all()
    recent_alerts = AlertLog.objects.all()[:10]
    config = SystemConfiguration.objects.first()
    
    context = {
        'devices': devices,
        'recent_alerts': recent_alerts,
        'config': config,
    }
    return render(request, "ecoguardian/control_panel.html", context)

@csrf_exempt
def receive_data(request):
    """
    Enhanced data receiver with automated control logic
    """
    if request.method == "POST":
        data = json.loads(request.body)
        
        # Create sensor reading
        reading = SensorReading.objects.create(
            temperature=data.get("temperature"),
            noise=data.get("noise"),
            air_quality=data.get("air_quality")
        )
        
        # Get system configuration
        config = SystemConfiguration.objects.first()
        if not config:
            # Create default config if none exists
            config = SystemConfiguration.objects.create()
        
        # Run automation logic
        automation_results = run_automation(reading, config)
        
        return JsonResponse({
            "status": "success",
            "reading_id": reading.id,
            "automation": automation_results
        })
    
    return JsonResponse({"error": "POST required"}, status=400)


def run_automation(reading, config):
    """
    Core automation logic - triggers devices and alerts
    """
    results = {
        "ac_activated": False,
        "ventilation_activated": False,
        "alerts_sent": []
    }
    
    # Check if we're in exam period (stricter thresholds)
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
    
    # 1. TEMPERATURE CONTROL - Auto AC
    if reading.temperature > config.temp_threshold and config.auto_ac_enabled:
        activate_ac()
        reading.ac_activated = True
        results["ac_activated"] = True
        
        # Send alert
        if config.alerts_enabled and should_send_alert('TEMP_HIGH', config):
            alert = send_alert(
                alert_type='TEMP_HIGH',
                reading=reading,
                message=f" High temperature detected: {reading.temperature}°C. AC activated automatically.",
                config=config
            )
            results["alerts_sent"].append("temperature")
    
    # 2. AIR QUALITY CONTROL - Auto Ventilation
    if reading.air_quality > config.air_quality_threshold and config.auto_ventilation_enabled:
        activate_ventilation()
        reading.ventilation_activated = True
        results["ventilation_activated"] = True
        
        if config.alerts_enabled and should_send_alert('AIR_POOR', config):
            alert = send_alert(
                alert_type='AIR_POOR',
                reading=reading,
                message=f" Poor air quality: {reading.air_quality} AQI. Ventilation activated.",
                config=config
            )
            results["alerts_sent"].append("air_quality")
    
    # 3. NOISE CONTROL - Alert C4DLab & Guard
    if reading.noise > noise_threshold:
        if config.alerts_enabled and should_send_alert('NOISE_HIGH', config):
            # Alert to C4DLab screen
            send_c4dlab_screen_alert(reading)
            
            # Alert to guard
            alert = send_alert(
                alert_type='NOISE_HIGH',
                reading=reading,
                message=f"🚨 HIGH NOISE ALERT: {reading.noise} dB detected! Possible C4DLab celebration. Please investigate.",
                config=config
            )
            
            reading.alert_sent = True
            results["alerts_sent"].append("noise")
    
    reading.save()
    return results

def activate_ac():
    """Activate air conditioning system"""
    ac_devices = ControlDevice.objects.filter(device_type='AC')
    
    for device in ac_devices:
        device.is_active = True
        device.last_activated = timezone.now()
        device.save()
    
    print(f"✅ AC activated: {ac_devices.count()} units")


def activate_ventilation():
    """Activate ventilation fans"""
    fans = ControlDevice.objects.filter(device_type='FAN')
    
    for fan in fans:
        fan.is_active = True
        fan.last_activated = timezone.now()
        fan.save()
    
    print(f"✅ Ventilation activated: {fans.count()} fans")


def send_c4dlab_screen_alert(reading):
    """Send alert to C4DLab screen display"""
    screen = ControlDevice.objects.filter(device_type='SCREEN').first()
    
    if screen:
        screen.is_active = True
        screen.last_activated = timezone.now()
        screen.save()
        
        # In production, this would trigger the actual screen display
        # For now, we log it
        print(f"📺 C4DLab Screen Alert: {reading.noise} dB noise detected!")


def should_send_alert(alert_type, config):
    """
    Check if enough time has passed since last alert (prevent spam)
    """
    cooldown_time = timezone.now() - timedelta(minutes=config.alert_cooldown_minutes)
    
    recent_alert = AlertLog.objects.filter(
        alert_type=alert_type,
        timestamp__gte=cooldown_time
    ).first()
    
    return recent_alert is None


def send_alert(alert_type, reading, message, config):
    """
    Send alerts via multiple channels
    """
    alerts_created = []
    
    # 1. SMS to guard
    alert = AlertLog.objects.create(
        alert_type=alert_type,
        channel='SMS',
        message=message,
        recipient=config.guard_phone,
        sensor_reading=reading
    )
    alerts_created.append(alert)
    print(f"📱 SMS sent to guard: {config.guard_phone}")
    
    # 2. Email to admin
    alert = AlertLog.objects.create(
        alert_type=alert_type,
        channel='EMAIL',
        message=message,
        recipient=config.admin_email,
        sensor_reading=reading
    )
    alerts_created.append(alert)
    print(f"📧 Email sent to admin: {config.admin_email}")
    
    # 3. C4DLab screen notification
    alert = AlertLog.objects.create(
        alert_type=alert_type,
        channel='SCREEN',
        message=message,
        recipient='C4DLab Main Screen',
        sensor_reading=reading
    )
    alerts_created.append(alert)
    print(f"📺 Screen notification sent")
    
    return alerts_created


def latest_data(request):
    """Latest sensor data with control status"""
    reading = SensorReading.objects.last()
    if not reading:
        return JsonResponse({})
    
    # Get device statuses
    ac_status = ControlDevice.objects.filter(device_type='AC', is_active=True).exists()
    fan_status = ControlDevice.objects.filter(device_type='FAN', is_active=True).exists()
    
    # Get recent alerts
    recent_alerts = AlertLog.objects.filter(
        timestamp__gte=timezone.now() - timedelta(minutes=5)
    ).count()
    
    return JsonResponse({
        "temperature": reading.temperature,
        "noise": reading.noise,
        "air_quality": reading.air_quality,
        "timestamp": reading.timestamp,
        "ac_active": ac_status,
        "ventilation_active": fan_status,
        "ac_activated": reading.ac_activated,
        "ventilation_activated": reading.ventilation_activated,
        "alert_sent": reading.alert_sent,
        "recent_alerts": recent_alerts,
    })

@csrf_exempt
def manual_control(request):
    """Manual override for devices"""
    if request.method == "POST":
        data = json.loads(request.body)
        device_id = data.get('device_id')
        action = data.get('action')  # 'on' or 'off'
        
        try:
            device = ControlDevice.objects.get(id=device_id)
            device.is_active = (action == 'on')
            if action == 'on':
                device.last_activated = timezone.now()
            device.save()
            
            return JsonResponse({
                "status": "success",
                "device": device.name,
                "state": "active" if device.is_active else "inactive"
            })
        except ControlDevice.DoesNotExist:
            return JsonResponse({"error": "Device not found"}, status=404)
    
    return JsonResponse({"error": "POST required"}, status=400)


def alert_history(request):
    """Get alert history"""
    alerts = AlertLog.objects.select_related('sensor_reading').all()[:50]
    
    data = [{
        "id": alert.id,
        "type": alert.get_alert_type_display(),
        "channel": alert.channel,
        "message": alert.message,
        "recipient": alert.recipient,
        "timestamp": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "acknowledged": alert.acknowledged,
    } for alert in alerts]
    
    return JsonResponse({"alerts": data})


@csrf_exempt
def acknowledge_alert(request, alert_id):
    """Mark alert as acknowledged"""
    if request.method == "POST":
        try:
            alert = AlertLog.objects.get(id=alert_id)
            alert.acknowledged = True
            alert.acknowledged_at = timezone.now()
            alert.save()
            
            return JsonResponse({"status": "success"})
        except AlertLog.DoesNotExist:
            return JsonResponse({"error": "Alert not found"}, status=404)
        

    
    return JsonResponse({"error": "POST required"}, status=400)

