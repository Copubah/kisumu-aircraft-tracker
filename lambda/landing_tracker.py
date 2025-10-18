import json
import os
import time
import math
import requests
import boto3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# AWS clients
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Environment variables
AIRCRAFT_STATE_TABLE = os.environ['AIRCRAFT_STATE_TABLE']
LANDINGS_TABLE = os.environ['LANDINGS_TABLE']
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']
AIRPORT_LAT = float(os.environ['AIRPORT_LAT'])
AIRPORT_LON = float(os.environ['AIRPORT_LON'])
DETECTION_RADIUS_KM = float(os.environ['DETECTION_RADIUS_KM'])
LANDING_ALTITUDE_THRESHOLD = float(os.environ['LANDING_ALTITUDE_THRESHOLD'])
OPENSKY_USERNAME = os.environ.get('OPENSKY_USERNAME', '')
OPENSKY_PASSWORD = os.environ.get('OPENSKY_PASSWORD', '')

# DynamoDB tables
aircraft_state_table = dynamodb.Table(AIRCRAFT_STATE_TABLE)
landings_table = dynamodb.Table(LANDINGS_TABLE)

# OpenSky API configuration
OPENSKY_BASE_URL = "https://opensky-network.org/api"


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth.
    Returns distance in kilometers.
    """
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of Earth in kilometers
    r = 6371
    return c * r


def get_bounding_box(lat: float, lon: float, radius_km: float) -> Tuple[float, float, float, float]:
    """
    Calculate bounding box coordinates for OpenSky API query.
    Returns (lamin, lomin, lamax, lomax).
    """
    # Approximate degrees per kilometer
    lat_deg_per_km = 1 / 111.0
    lon_deg_per_km = 1 / (111.0 * math.cos(math.radians(lat)))
    
    lat_offset = radius_km * lat_deg_per_km
    lon_offset = radius_km * lon_deg_per_km
    
    return (
        lat - lat_offset,  # lamin
        lon - lon_offset,  # lomin
        lat + lat_offset,  # lamax
        lon + lon_offset   # lomax
    )


def fetch_aircraft_data() -> List[Dict]:
    """
    Fetch aircraft data from OpenSky Network API for Kisumu area.
    """
    lamin, lomin, lamax, lomax = get_bounding_box(
        AIRPORT_LAT, AIRPORT_LON, DETECTION_RADIUS_KM
    )
    
    url = f"{OPENSKY_BASE_URL}/states/all"
    params = {
        'lamin': lamin,
        'lomin': lomin,
        'lamax': lamax,
        'lomax': lomax
    }
    
    auth = None
    if OPENSKY_USERNAME and OPENSKY_PASSWORD:
        auth = (OPENSKY_USERNAME, OPENSKY_PASSWORD)
    
    try:
        response = requests.get(url, params=params, auth=auth, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        if not data or 'states' not in data or not data['states']:
            return []
        
        aircraft_list = []
        for state in data['states']:
            if len(state) >= 17 and state[5] is not None and state[6] is not None:
                aircraft = {
                    'icao24': state[0],
                    'callsign': state[1].strip() if state[1] else None,
                    'origin_country': state[2],
                    'time_position': state[3],
                    'last_contact': state[4],
                    'longitude': state[5],
                    'latitude': state[6],
                    'baro_altitude': state[7],  # meters
                    'on_ground': state[8],
                    'velocity': state[9],  # m/s
                    'true_track': state[10],
                    'vertical_rate': state[11],  # m/s
                    'sensors': state[12],
                    'geo_altitude': state[13],  # meters
                    'squawk': state[14],
                    'spi': state[15],
                    'position_source': state[16]
                }
                
                # Filter aircraft within detection radius
                distance = calculate_distance(
                    AIRPORT_LAT, AIRPORT_LON,
                    aircraft['latitude'], aircraft['longitude']
                )
                
                if distance <= DETECTION_RADIUS_KM:
                    aircraft['distance_to_airport'] = distance
                    aircraft_list.append(aircraft)
        
        return aircraft_list
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching OpenSky data: {e}")
        return []


def get_previous_state(icao24: str) -> Optional[Dict]:
    """
    Get the previous state of an aircraft from DynamoDB.
    """
    try:
        response = aircraft_state_table.get_item(Key={'icao24': icao24})
        return response.get('Item')
    except Exception as e:
        print(f"Error getting previous state for {icao24}: {e}")
        return None


def update_aircraft_state(aircraft: Dict) -> None:
    """
    Update aircraft state in DynamoDB.
    """
    try:
        # TTL: expire records after 1 hour
        ttl = int(time.time()) + 3600
        
        item = {
            'icao24': aircraft['icao24'],
            'callsign': aircraft['callsign'],
            'latitude': aircraft['latitude'],
            'longitude': aircraft['longitude'],
            'baro_altitude': aircraft['baro_altitude'],
            'vertical_rate': aircraft['vertical_rate'],
            'velocity': aircraft['velocity'],
            'on_ground': aircraft['on_ground'],
            'distance_to_airport': aircraft['distance_to_airport'],
            'last_updated': int(time.time()),
            'ttl': ttl
        }
        
        aircraft_state_table.put_item(Item=item)
        
    except Exception as e:
        print(f"Error updating aircraft state for {aircraft['icao24']}: {e}")


def detect_landing(current_aircraft: Dict, previous_state: Optional[Dict]) -> bool:
    """
    Detect if an aircraft has landed based on current and previous state.
    
    Landing criteria:
    1. Aircraft altitude is below threshold (converted from meters to feet)
    2. Aircraft has negative vertical rate (descending)
    3. Aircraft was previously at higher altitude
    4. Aircraft is not already on ground
    """
    if not previous_state:
        return False
    
    # Convert altitude from meters to feet
    current_altitude_ft = current_aircraft['baro_altitude'] * 3.28084 if current_aircraft['baro_altitude'] else 0
    previous_altitude_ft = previous_state['baro_altitude'] * 3.28084 if previous_state['baro_altitude'] else 0
    
    # Check landing conditions
    conditions = [
        current_altitude_ft < LANDING_ALTITUDE_THRESHOLD,  # Below altitude threshold
        current_aircraft['vertical_rate'] is not None and current_aircraft['vertical_rate'] < -1,  # Descending
        previous_altitude_ft > LANDING_ALTITUDE_THRESHOLD,  # Was previously higher
        not current_aircraft['on_ground'],  # Not already marked as on ground
        current_aircraft['distance_to_airport'] <= 2.0  # Within 2km of airport
    ]
    
    return all(conditions)


def record_landing(aircraft: Dict) -> None:
    """
    Record a detected landing in DynamoDB and send notification.
    """
    try:
        timestamp = int(time.time())
        landing_id = f"{aircraft['icao24']}_{timestamp}"
        
        # Convert altitude to feet for storage
        altitude_ft = aircraft['baro_altitude'] * 3.28084 if aircraft['baro_altitude'] else 0
        
        landing_record = {
            'landing_id': landing_id,
            'timestamp': timestamp,
            'icao24': aircraft['icao24'],
            'callsign': aircraft['callsign'],
            'latitude': aircraft['latitude'],
            'longitude': aircraft['longitude'],
            'altitude_feet': round(altitude_ft, 2),
            'vertical_rate_ms': aircraft['vertical_rate'],
            'velocity_ms': aircraft['velocity'],
            'distance_to_airport_km': round(aircraft['distance_to_airport'], 2),
            'detection_time': datetime.now(timezone.utc).isoformat()
        }
        
        # Store in DynamoDB
        landings_table.put_item(Item=landing_record)
        
        # Send SNS notification
        message = {
            'event': 'aircraft_landing_detected',
            'airport': 'Kisumu International Airport',
            'aircraft': {
                'icao24': aircraft['icao24'],
                'callsign': aircraft['callsign'] or 'Unknown',
                'altitude_feet': round(altitude_ft, 2),
                'distance_km': round(aircraft['distance_to_airport'], 2)
            },
            'timestamp': landing_record['detection_time']
        }
        
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"Aircraft Landing Detected - {aircraft['callsign'] or aircraft['icao24']}",
            Message=json.dumps(message, indent=2)
        )
        
        print(f"Landing recorded for aircraft {aircraft['icao24']} ({aircraft['callsign']})")
        
    except Exception as e:
        print(f"Error recording landing for {aircraft['icao24']}: {e}")


def lambda_handler(event, context):
    """
    Main Lambda handler function.
    """
    try:
        print("Starting aircraft landing detection...")
        
        # Fetch current aircraft data
        aircraft_list = fetch_aircraft_data()
        print(f"Found {len(aircraft_list)} aircraft in Kisumu area")
        
        landings_detected = 0
        
        for aircraft in aircraft_list:
            # Get previous state
            previous_state = get_previous_state(aircraft['icao24'])
            
            # Check for landing
            if detect_landing(aircraft, previous_state):
                record_landing(aircraft)
                landings_detected += 1
            
            # Update current state
            update_aircraft_state(aircraft)
        
        result = {
            'statusCode': 200,
            'body': {
                'message': 'Aircraft tracking completed successfully',
                'aircraft_tracked': len(aircraft_list),
                'landings_detected': landings_detected,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }
        
        print(f"Tracking completed: {len(aircraft_list)} aircraft, {landings_detected} landings detected")
        return result
        
    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        return {
            'statusCode': 500,
            'body': {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }