
import json
import requests
import re
import time

# Django API endpoint - CHANGE THIS to your server address if needed
DJANGO_API = "http://127.0.0.1:8000/api/data/"

# Device ID for this Arduino
DEVICE_ID = "arduino_01"


def parse_csv_format(data):
    """
    Parse CSV format: TEMP:29.0,AIR:872,NOISE:583
    Returns: dict with temperature, air_quality, noise_level
    """
    try:
        # Extract values using regex
        temp_match = re.search(r'TEMP:([\d.]+)', data)
        air_match = re.search(r'AIR:([\d.]+)', data)
        noise_match = re.search(r'NOISE:([\d.]+)', data)
        
        if temp_match and air_match and noise_match:
            # Convert raw sensor values to proper ranges
            temp = float(temp_match.group(1))
            air_raw = float(air_match.group(1))
            noise_raw = float(noise_match.group(1))
            
            # Map raw values (0-1023) to actual ranges
            # Air Quality: 0-1023 -> 20-80 AQI
            air_quality = 20 + (air_raw / 1023) * 60
            
            # Noise: 0-1023 -> 30-90 dB
            noise_level = 30 + (noise_raw / 1023) * 60
            
            return {
                "device_id": DEVICE_ID,
                "temperature": round(temp, 1),
                "air_quality": round(air_quality, 1),
                "noise_level": round(noise_level, 1)
            }
        return None
    except Exception as e:
        print(f" CSV parse error: {e}")
        return None


def parse_json_format(data):
    """
    Parse JSON format: {"temperature":24.5,"noise_level":45.2,"air_quality":38.7}
    """
    try:
        parsed = json.loads(data)
        
        # Check for required fields (handle both noise and noise_level)
        if 'temperature' in parsed and 'air_quality' in parsed:
            if 'noise' in parsed:
                parsed['noise_level'] = parsed.pop('noise')
            
            if 'noise_level' in parsed:
                # Add device_id if not present
                if 'device_id' not in parsed:
                    parsed['device_id'] = DEVICE_ID
                return parsed
        
        return None
    except Exception as e:
        return None


def send_to_django(data):
    """Send data to Django API"""
    try:
        print(f"\n Sending to Django: {json.dumps(data, indent=2)}")
        
        response = requests.post(
            DJANGO_API,
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(" Success!")
            print(f"   Reading ID: {result.get('reading_id')}")
            print(f"   Total readings: {result.get('reading_count')}")
            
            # Show automation results
            automation = result.get('automation', {})
            if automation.get('ac_activated'):
                print("     AC activated")
            if automation.get('ventilation_activated'):
                print("    Ventilation activated")
            if automation.get('alerts_sent'):
                print(f"    Alerts sent: {', '.join(automation['alerts_sent'])}")
            
            # Show AI analysis
            ai = result.get('ai_analysis')
            if ai and ai.get('is_anomaly'):
                print(f"     ANOMALY DETECTED! Score: {ai.get('score', 0):.2f}")
            
        else:
            print(f" Django returned status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(" Connection failed! Is Django running on http://127.0.0.1:8000?")
        print("   Start Django with: python manage.py runserver")
    except Exception as e:
        print(f" Error: {e}")


def process_input(user_input):
    """Process user input - try both CSV and JSON formats"""
    user_input = user_input.strip()
    
    # Skip empty input
    if not user_input:
        return
    
    # Skip system messages
    skip_messages = ['System Starting', 'System Ready', 'ECO-GUARDIAN', 
                     'Initializing', 'Starting']
    if any(msg in user_input for msg in skip_messages):
        print("ℹ  Skipping system message")
        return
    
    # Try CSV format first (TEMP:X,AIR:Y,NOISE:Z)
    if 'TEMP:' in user_input:
        data = parse_csv_format(user_input)
        if data:
            send_to_django(data)
            return
    
    # Try JSON format
    data = parse_json_format(user_input)
    if data:
        send_to_django(data)
        return
    
    print(" Invalid format! Expected:")
    print("   CSV: TEMP:29.0,AIR:872,NOISE:583")
    print("   JSON: {\"temperature\":24.5,\"noise_level\":45.2,\"air_quality\":38.7}")


def auto_mode():
    """Generate automatic test data"""
    import random
    
    test_data = {
        "device_id": DEVICE_ID,
        "temperature": round(random.uniform(22, 30), 1),
        "air_quality": round(random.uniform(35, 70), 1),
        "noise_level": round(random.uniform(40, 75), 1)
    }
    print("\n🤖 Auto mode - sending test data...")
    send_to_django(test_data)


def continuous_mode():
    """Continuously generate test data"""
    import random
    
    print("\n🔄 Continuous mode started (Ctrl+C to stop)")
    print("Sending data every 5 minutes...\n")
    
    try:
        while True:
            test_data = {
                "device_id": DEVICE_ID,
                "temperature": round(random.uniform(22, 30), 1),
                "air_quality": round(random.uniform(35, 70), 1),
                "noise_level": round(random.uniform(40, 75), 1)
            }
            send_to_django(test_data)
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n\n⏹  Continuous mode stopped")


def check_connection():
    """Check if Django server is running"""
    try:
        response = requests.get("http://127.0.0.1:8000/health/", timeout=3)
        if response.status_code == 200:
            print(" Django server is running and healthy")
            return True
        else:
            print("  Django server responded but may have issues")
            return False
    except:
        print(" Cannot connect to Django server")
        print("   Make sure Django is running: python manage.py runserver")
        return False


def main():
    print("=" * 70)
    print(" EcoGuardian Tinkercad → Django Bridge (v3.0)")
    print("=" * 70)
    print(f" Django API: {DJANGO_API}")
    print(f" Device ID: {DEVICE_ID}")
    print("-" * 70)
    
    # Check connection
    check_connection()
    
    print("\nCommands:")
    print("  'auto'       - Send one test reading")
    print("  'continuous' - Send test data every 5 seconds")
    print("  'check'      - Check Django server connection")
    print("  'quit'       - Exit")
    print("  Or paste data from Tinkercad (CSV or JSON format)")
    print("-" * 70)
    
    while True:
        try:
            user_input = input("\n Enter command or data: ").strip()
            
            if user_input.lower() == 'quit':
                print("\n👋 Goodbye!\n")
                break
            elif user_input.lower() == 'auto':
                auto_mode()
            elif user_input.lower() == 'continuous':
                continuous_mode()
            elif user_input.lower() == 'check':
                check_connection()
            elif user_input:
                process_input(user_input)
            
        except KeyboardInterrupt:
            print("\n\n Goodbye!\n")
            break
        except Exception as e:
            print(f" Unexpected error: {e}")


if __name__ == "__main__":
    main()