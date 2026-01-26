from django.db import models

class SensorReading(models.Model):
    temperature = models.FloatField()
    noise = models.FloatField()
    air_quality = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Temp: {self.temperature}, Noise: {self.noise}, Air Quality: {self.air_quality}"
