# models.py - Enhanced with control systems

from django.db import models
from django.utils import timezone

class SensorReading(models.Model):
    temperature = models.FloatField()
    noise = models.FloatField()
    air_quality = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Automated responses triggered
    ac_activated = models.BooleanField(default=False)
    ventilation_activated = models.BooleanField(default=False)
    alert_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] T:{self.temperature}°C N:{self.noise}dB AQ:{self.air_quality}"

    class Meta:
        ordering = ['-timestamp']


class ControlDevice(models.Model):
    """Track all controllable devices in the system"""
    DEVICE_TYPES = [
        ('AC', 'Air Conditioner'),
        ('FAN', 'Ventilation Fan'),
        ('ALARM', 'Alarm System'),
        ('SCREEN', 'Alert Screen'),
    ]
    
    name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    location = models.CharField(max_length=100)
    is_active = models.BooleanField(default=False)
    last_activated = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.location}) - {'ON' if self.is_active else 'OFF'}"


class AlertLog(models.Model):
    """Log all alerts sent"""
    ALERT_TYPES = [
        ('TEMP_HIGH', 'High Temperature'),
        ('NOISE_HIGH', 'High Noise Level'),
        ('AIR_POOR', 'Poor Air Quality'),
        ('MULTIPLE', 'Multiple Alerts'),
    ]
    
    ALERT_CHANNELS = [
        ('SMS', 'SMS Message'),
        ('EMAIL', 'Email'),
        ('SCREEN', 'C4DLab Screen'),
        ('WHATSAPP', 'WhatsApp'),
        ('SYSTEM', 'System Notification'),
        ('GUARD', 'Security Guard'),
    ]
    
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    channel = models.CharField(max_length=20, choices=ALERT_CHANNELS)
    message = models.TextField()
    recipient = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    sensor_reading = models.ForeignKey(
        SensorReading, 
        on_delete=models.CASCADE, 
        related_name='alerts'
    )
    
    def __str__(self):
        return f"{self.get_alert_type_display()} via {self.channel} at {self.timestamp.strftime('%H:%M:%S')}"
    
    class Meta:
        ordering = ['-timestamp']


class SystemConfiguration(models.Model):
    """System settings and thresholds"""
    # Thresholds
    temp_threshold = models.FloatField(default=26.0, help_text="Temperature threshold in °C")
    noise_threshold = models.FloatField(default=60.0, help_text="Noise threshold in dB")
    air_quality_threshold = models.FloatField(default=55.0, help_text="AQI threshold")
    
    # Contact information
    guard_phone = models.CharField(max_length=20, default="+254700000000")
    admin_email = models.EmailField(default="admin@uon.ac.ke")
    
    # Auto-control settings
    auto_ac_enabled = models.BooleanField(default=True)
    auto_ventilation_enabled = models.BooleanField(default=True)
    alerts_enabled = models.BooleanField(default=True)
    
    # Alert cooldown (prevent spam)
    alert_cooldown_minutes = models.IntegerField(default=5, help_text="Minutes between repeated alerts")
    
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"System Config (Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"
    
    class Meta:
        verbose_name = "System Configuration"
        verbose_name_plural = "System Configuration"


class ExamSchedule(models.Model):
    """Track exam schedules for stricter monitoring"""
    exam_name = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    room = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    
    # Stricter thresholds during exams
    strict_noise_threshold = models.FloatField(default=50.0)
    
    def __str__(self):
        return f"{self.exam_name} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"
    
    def is_ongoing(self):
        now = timezone.now()
        return self.start_time <= now <= self.end_time
    
    class Meta:
        ordering = ['-start_time']