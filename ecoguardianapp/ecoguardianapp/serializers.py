# serializers.py - For REST Framework (optional, kept for expansion)

from rest_framework import serializers
from .models import EnvironmentalData, EcoGuardianDevice, AlertLog, AITrainingModel


class EcoGuardianDeviceSerializer(serializers.ModelSerializer):
    is_online = serializers.SerializerMethodField()
    last_reading = serializers.SerializerMethodField()
    
    class Meta:
        model = EcoGuardianDevice
        fields = ['device_id', 'device_name', 'location', 'is_active', 
                 'created_at', 'last_seen', 'is_online', 'last_reading']
        read_only_fields = ['created_at', 'last_seen']
    
    def get_is_online(self, obj):
        return obj.is_online()
    
    def get_last_reading(self, obj):
        latest = EnvironmentalData.objects.filter(device=obj).order_by('-timestamp').first()
        if latest:
            return {
                'temperature': latest.temperature,
                'air_quality': latest.air_quality,
                'noise_level': latest.noise_level,
                'timestamp': latest.timestamp.isoformat(),
                'is_anomaly': latest.is_anomaly
            }
        return None


class EnvironmentalDataSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.device_name', read_only=True)
    device_location = serializers.CharField(source='device.location', read_only=True)
    
    class Meta:
        model = EnvironmentalData
        fields = ['id', 'device', 'device_name', 'device_location', 'timestamp',
                 'temperature', 'air_quality', 'noise_level', 'ai_score',
                 'is_anomaly', 'anomaly_type', 'system_status', 
                 'ac_activated', 'ventilation_activated', 'alert_sent']
        read_only_fields = ['timestamp', 'created_at']


class AlertLogSerializer(serializers.ModelSerializer):
    device_id = serializers.CharField(source='data.device.device_id', read_only=True)
    device_name = serializers.CharField(source='data.device.device_name', read_only=True)
    
    class Meta:
        model = AlertLog
        fields = ['id', 'alert_type', 'severity', 'channel', 'message', 
                 'recipient', 'created_at', 'is_resolved', 'resolved_at',
                 'device_id', 'device_name']
        read_only_fields = ['created_at']


class AITrainingModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AITrainingModel
        fields = ['id', 'device', 'model_version', 'training_date', 
                 'accuracy', 'samples_trained', 'is_active']
        read_only_fields = ['training_date']