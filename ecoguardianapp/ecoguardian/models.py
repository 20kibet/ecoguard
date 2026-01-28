# models.py - FIXED & INTEGRATED

from django.db import models
from django.utils import timezone
from datetime import timedelta

class EcoGuardianDevice(models.Model):
    """IoT devices registered in the system"""
    device_id = models.CharField(max_length=100, unique=True, primary_key=True)
    device_name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.device_name} ({self.location})"
    
    def is_online(self):
        """Device is online if last seen within 5 minutes"""
        return self.last_seen >= timezone.now() - timedelta(minutes=5)


class EnvironmentalData(models.Model):
    """Sensor readings with AI analysis"""
    device = models.ForeignKey(EcoGuardianDevice, on_delete=models.CASCADE, related_name='readings')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Sensor readings
    temperature = models.FloatField()
    air_quality = models.FloatField()
    noise_level = models.FloatField()
    
    # AI Analysis results
    ai_score = models.FloatField(null=True, blank=True)
    anomaly_type = models.CharField(max_length=50, null=True, blank=True)
    is_anomaly = models.BooleanField(default=False)
    
    # System status
    system_status = models.CharField(max_length=20, default='normal')
    
    # Automated responses (from your automation system)
    ac_activated = models.BooleanField(default=False)
    ventilation_activated = models.BooleanField(default=False)
    alert_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.device.device_name} - T:{self.temperature}°C"
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Environmental Data"


class ControlDevice(models.Model):
    """Controllable devices (AC, fans, alarms)"""
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
    """Alert logs for notifications"""
    ALERT_TYPES = [
        ('TEMP_HIGH', 'High Temperature'),
        ('NOISE_HIGH', 'High Noise Level'),
        ('AIR_POOR', 'Poor Air Quality'),
        ('ANOMALY', 'AI Detected Anomaly'),
        ('MULTIPLE', 'Multiple Alerts'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    ALERT_CHANNELS = [
        ('SMS', 'SMS Message'),
        ('EMAIL', 'Email'),
        ('SCREEN', 'C4DLab Screen'),
        ('WHATSAPP', 'WhatsApp'),
        ('SYSTEM', 'System Notification'),
    ]
    
    data = models.ForeignKey(EnvironmentalData, on_delete=models.CASCADE, related_name='alerts', null=True, blank=True)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    channel = models.CharField(max_length=20, choices=ALERT_CHANNELS)
    message = models.TextField()
    recipient = models.CharField(max_length=100)
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.severity} at {self.created_at.strftime('%H:%M:%S')}"
    
    class Meta:
        ordering = ['-created_at']


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
    ai_analysis_enabled = models.BooleanField(default=True)
    
    # Alert cooldown
    alert_cooldown_minutes = models.IntegerField(default=5)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"System Config (Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"
    
    class Meta:
        verbose_name = "System Configuration"
        verbose_name_plural = "System Configuration"
    
    def save(self, *args, **kwargs):
        # Ensure only one config exists
        if not self.pk and SystemConfiguration.objects.exists():
            raise ValueError("Only one SystemConfiguration instance allowed")
        return super().save(*args, **kwargs)


class AITrainingModel(models.Model):
    """Store AI model metadata"""
    device = models.ForeignKey(EcoGuardianDevice, on_delete=models.CASCADE)
    model_version = models.CharField(max_length=50)
    training_date = models.DateTimeField(auto_now_add=True)
    accuracy = models.FloatField(null=True, blank=True)
    samples_trained = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.device.device_name} - v{self.model_version}"
    
    class Meta:
        ordering = ['-training_date']


class ExamSchedule(models.Model):
    """Exam schedules for stricter monitoring"""
    exam_name = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    room = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    strict_noise_threshold = models.FloatField(default=50.0)
    
    def __str__(self):
        return f"{self.exam_name} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"
    
    def is_ongoing(self):
        now = timezone.now()
        return self.start_time <= now <= self.end_time
    
    class Meta:
        ordering = ['-start_time']

        