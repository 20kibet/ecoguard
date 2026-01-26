from django.shortcuts import render
from django.http import JsonResponse
from .models import SensorReading
from django.views.decorators.csrf import csrf_exempt
import json

# Dashboard page
def dashboard(request):
    return render(request, "ecoguardian/dashboard.html")

# Receive sensor data (from ESP32 or simulation)
@csrf_exempt
def receive_data(request):
    if request.method == "POST":
        data = json.loads(request.body)
        SensorReading.objects.create(
            temperature=data.get("temperature"),
            noise=data.get("noise"),
            air_quality=data.get("air_quality")
        )
        return JsonResponse({"status": "success"})

# Latest data for dashboard
def latest_data(request):
    reading = SensorReading.objects.last()
    if not reading:
        return JsonResponse({})
    return JsonResponse({
        "temperature": reading.temperature,
        "noise": reading.noise,
        "air_quality": reading.air_quality,
        "timestamp": reading.timestamp
    })
