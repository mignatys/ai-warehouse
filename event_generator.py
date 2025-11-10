import random
import datetime
import json
import os
from config import RESTRICTED_AREAS, RULES

PERSONS = [
    {"id": "P1", "name": "Alice", "authorized_zones": ["Vault", "Equipment Room"]},
    {"id": "P2", "name": "Bob", "authorized_zones": ["Server Room"]},
    {"id": "P3", "name": "Charlie", "authorized_zones": []},
    {"id": "P4", "name": "Dave", "authorized_zones": ["Vault", "Server Room"]},
]

ZONE_COORDS = {area["name"]: area for area in RESTRICTED_AREAS}

def get_zone_center(zone_name):
    # Calculates the center pixel coordinate for a given zone name.
    area = ZONE_COORDS.get(zone_name)
    if not area: return None
    r1, c1 = area['top_left']
    r2, c2 = area['bottom_right']
    return (int((r1 + r2) / 2), int((c1 + c2) / 2))

def random_time(start_time):
    # Generate a random datetime shortly after a given start time.
    return start_time + datetime.timedelta(minutes=random.randint(1, 5), seconds=random.randint(0, 59))

def generate_person_journey(person, num_zones_to_visit=2, force_after_hours=False):
    # Generates a full journey for a single person, from entering to exiting the warehouse.
    journey = []
    
    # Generate a time for the journey, with a chance for it to be after hours
    if force_after_hours:
        hour = random.randint(18, 20) # Force after-hours event
    else:
        hour = random.randint(8, 17) # Normal operating hours
        
    base_time = datetime.datetime(2025, 11, 6, hour, random.randint(0, 59))
    current_time = base_time

    coords = get_zone_center("Entrance")
    journey.append({
        "timestamp": current_time.isoformat(), "person_id": person["id"], "person_name": person["name"],
        "zone": "Entrance", "event_type": "enter_warehouse", "authorized": True, "coords": coords
    })

    available_zones = [name for name in ZONE_COORDS if name != 'Entrance']
    num_to_visit = min(num_zones_to_visit, len(available_zones))
    zones_to_visit = random.sample(available_zones, k=num_to_visit)
    
    for zone in zones_to_visit:
        entry_time = random_time(current_time)
        authorized = zone in person["authorized_zones"]
        coords = get_zone_center(zone)
        
        journey.append({
            "timestamp": entry_time.isoformat(), "person_id": person["id"], "person_name": person["name"],
            "zone": zone, "event_type": "person_entered", "authorized": authorized, "camera_id": f"C{random.randint(1,4)}", "coords": coords
        })

        duration_minutes = random.randint(4, 10)
        exit_time = entry_time + datetime.timedelta(minutes=duration_minutes)
        journey.append({
            "timestamp": exit_time.isoformat(), "person_id": person["id"], "person_name": person["name"],
            "zone": zone, "event_type": "person_exited", "authorized": authorized, "camera_id": f"C{random.randint(1,4)}",
            "coords": coords, "duration_minutes": duration_minutes, "allowed_minutes": RULES['loitering']['threshold_minutes']
        })
        current_time = exit_time

    current_time = random_time(current_time)
    coords = get_zone_center("Entrance")
    journey.append({
        "timestamp": current_time.isoformat(), "person_id": person["id"], "person_name": person["name"],
        "zone": "Entrance", "event_type": "exit_warehouse", "authorized": True, "coords": coords
    })
    return journey

def generate_synthetic_dataset(num_events_per_person=2):
    # Generates a full dataset, ensuring at least one person has an after-hours journey.
    dataset = []
    # Ensure the first person (Alice) has an after-hours journey for demonstration
    dataset.extend(generate_person_journey(PERSONS[0], num_zones_to_visit=1, force_after_hours=True))

    for person in PERSONS[1:]:
        dataset.extend(generate_person_journey(person, num_zones_to_visit=num_events_per_person))
    
    dataset.sort(key=lambda x: x["timestamp"])
    return dataset

def save_dataset(dataset, filename="data/warehouse_events.json"):
    # Saves the dataset to a JSON file.
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as f:
        json.dump(dataset, f, indent=2)
