# ai_processor.py - AI Analysis Engine

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
import json


class AIProcessor:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        
    def analyze_data(self, env_data):
        """Analyze incoming data for anomalies"""
        device_id = env_data.device.device_id
        
        # Initialize model for device if not exists
        if device_id not in self.models:
            self.models[device_id] = IsolationForest(contamination=0.1, random_state=42)
            self.scalers[device_id] = StandardScaler()
            self._train_initial_model(device_id)
        
        # Prepare features
        features = np.array([[env_data.temperature, env_data.air_quality, env_data.noise_level]])
        
        # Handle scaler
        try:
            features_scaled = self.scalers[device_id].transform(features)
        except:
            # If not fitted, fit first
            self.scalers[device_id].fit(features)
            features_scaled = self.scalers[device_id].transform(features)
        
        # Predict anomaly
        try:
            prediction = self.models[device_id].predict(features_scaled)
            is_anomaly = prediction[0] == -1
            
            # Calculate anomaly score
            scores = self.models[device_id].score_samples(features_scaled)
            anomaly_score = float(1 - (scores[0] + 1) / 2)  # Convert to 0-1 scale
        except:
            # Model not trained yet
            is_anomaly = False
            anomaly_score = 0.0
        
        insights = {
            'is_anomaly': bool(is_anomaly),
            'anomaly_score': anomaly_score,
            'prediction': 'Anomaly' if is_anomaly else 'Normal',
            'confidence': min(anomaly_score * 100, 100),
            'features': {
                'temperature': env_data.temperature,
                'air_quality': env_data.air_quality,
                'noise_level': env_data.noise_level
            }
        }
        
        # Update model periodically
        self._update_model(device_id, features_scaled)
        
        return insights
    
    def _train_initial_model(self, device_id):
        """Train initial model with historical data"""
        try:
            # Import here to avoid circular imports
            from .models import EnvironmentalData
            from django.utils import timezone
            
            # Get historical data (last 7 days)
            time_threshold = timezone.now() - timedelta(days=7)
            historical_data = EnvironmentalData.objects.filter(
                device__device_id=device_id,
                timestamp__gte=time_threshold
            ).values_list('temperature', 'air_quality', 'noise_level')
            
            if len(historical_data) > 10:
                data_array = np.array(list(historical_data))
                scaled_data = self.scalers[device_id].fit_transform(data_array)
                self.models[device_id].fit(scaled_data)
                print(f"✅ AI model trained for {device_id} with {len(historical_data)} samples")
        except Exception as e:
            print(f"⚠️ Could not train model for {device_id}: {e}")
    
    def _update_model(self, device_id, new_data):
        """Update model with new data (incremental learning placeholder)"""
        # For now, we retrain periodically in _train_initial_model
        # Full incremental learning can be added here
        pass
    
    def generate_insights(self, data_list):
        """Generate insights from historical data"""
        if not data_list:
            return {"error": "No data available"}
        
        # Convert to lists
        timestamps = [d['timestamp'] for d in data_list]
        temperatures = [float(d['temperature']) for d in data_list]
        air_quality = [float(d['air_quality']) for d in data_list]
        noise_levels = [float(d['noise_level']) for d in data_list]
        
        insights = {
            'trends': {
                'temperature': self._calculate_trend(temperatures),
                'air_quality': self._calculate_trend(air_quality),
                'noise': self._calculate_trend(noise_levels)
            },
            'patterns': self._detect_patterns(timestamps, temperatures, air_quality, noise_levels),
            'correlations': self._calculate_correlations(temperatures, air_quality, noise_levels),
            'peak_hours': self._find_peak_hours(timestamps, noise_levels),
            'statistics': {
                'temperature': {
                    'min': round(min(temperatures), 1),
                    'max': round(max(temperatures), 1),
                    'avg': round(np.mean(temperatures), 1),
                    'std': round(np.std(temperatures), 1)
                },
                'air_quality': {
                    'min': round(min(air_quality), 1),
                    'max': round(max(air_quality), 1),
                    'avg': round(np.mean(air_quality), 1),
                    'std': round(np.std(air_quality), 1)
                },
                'noise': {
                    'min': round(min(noise_levels), 1),
                    'max': round(max(noise_levels), 1),
                    'avg': round(np.mean(noise_levels), 1),
                    'std': round(np.std(noise_levels), 1)
                }
            }
        }
        
        return insights
    
    def _calculate_trend(self, values):
        """Calculate trend (percentage change)"""
        if len(values) < 2:
            return 0
        start_avg = np.mean(values[:min(5, len(values))])
        end_avg = np.mean(values[-min(5, len(values)):])
        if start_avg == 0:
            return 0
        return round(((end_avg - start_avg) / start_avg) * 100, 2)
    
    def _detect_patterns(self, timestamps, *metrics):
        """Detect patterns in the data"""
        patterns = {}
        metric_names = ['temperature', 'air_quality', 'noise']
        
        for i, metric in enumerate(metrics):
            if len(metric) > 10:
                mean_val = np.mean(metric)
                std_val = np.std(metric)
                
                # Check stability (low variance)
                patterns[f'{metric_names[i]}_stable'] = std_val < mean_val * 0.1
                
                # Check for spikes
                patterns[f'{metric_names[i]}_has_spikes'] = any(
                    abs(v - mean_val) > 2 * std_val for v in metric
                )
        
        return patterns
    
    def _calculate_correlations(self, *metrics):
        """Calculate correlations between metrics"""
        correlations = {}
        metric_names = ['temperature', 'air_quality', 'noise']
        
        for i in range(len(metrics)):
            for j in range(i+1, len(metrics)):
                if len(metrics[i]) > 2 and len(metrics[j]) > 2:
                    try:
                        corr = np.corrcoef(metrics[i], metrics[j])[0,1]
                        if not np.isnan(corr):
                            correlations[f'{metric_names[i]}_vs_{metric_names[j]}'] = round(float(corr), 3)
                    except:
                        pass
        
        return correlations
    
    def _find_peak_hours(self, timestamps, values):
        """Find peak hours for noise"""
        if not timestamps or not values:
            return []
        
        # Group by hour
        hours = {}
        for ts, val in zip(timestamps, values):
            if isinstance(ts, str):
                try:
                    hour = datetime.fromisoformat(ts.replace('Z', '+00:00')).hour
                except:
                    continue
            else:
                hour = ts.hour
            hours.setdefault(hour, []).append(val)
        
        # Find average per hour
        avg_by_hour = {h: np.mean(vals) for h, vals in hours.items()}
        
        # Find top 3 peak hours
        peak_hours = sorted(avg_by_hour.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return [{'hour': h, 'average_value': round(avg, 1)} for h, avg in peak_hours]
    
    def get_recommendations(self, insights):
        """Generate AI-powered recommendations"""
        recommendations = []
        
        if 'trends' in insights:
            trends = insights['trends']
            
            if trends.get('temperature', 0) > 8:
                recommendations.append({
                    'priority': 'high',
                    'category': 'temperature',
                    'message': 'Significant temperature increase detected. Consider: 1) Check HVAC system 2) Increase ventilation 3) Monitor for overheating equipment'
                })
            
            if trends.get('air_quality', 0) > 15:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'air_quality',
                    'message': 'Air quality declining. Recommendations: 1) Verify air filters 2) Increase fresh air intake 3) Schedule air quality audit'
                })
            
            if trends.get('noise', 0) > 20:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'noise',
                    'message': 'Noise levels increasing. Consider soundproofing or scheduling maintenance during quieter hours.'
                })
        
        if 'peak_hours' in insights and insights['peak_hours']:
            top_hour = insights['peak_hours'][0]
            recommendations.append({
                'priority': 'low',
                'category': 'noise',
                'message': f"Noise peaks detected at hour {top_hour['hour']}:00. Consider scheduling quiet activities during this time."
            })
        
        if 'patterns' in insights:
            patterns = insights['patterns']
            
            if patterns.get('temperature_has_spikes'):
                recommendations.append({
                    'priority': 'medium',
                    'category': 'temperature',
                    'message': 'Temperature spikes detected. Check for equipment issues or door/window opening patterns.'
                })
        
        if not recommendations:
            recommendations.append({
                'priority': 'info',
                'category': 'system',
                'message': 'All parameters within optimal ranges. Continue regular monitoring.'
            })
        
        return recommendations