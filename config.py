# =========================
# CONFIG & RULES
# =========================

# Warehouse size
WAREHOUSE_ROWS = 25
WAREHOUSE_COLS = 30

# Zone types
ZONE_WALKWAY = 0
ZONE_RESTRICTED = 1
ZONE_SAFE = 2
ZONE_CAMERA = 3
ZONE_ENTRANCE = 4

# Zone Definitions
RESTRICTED_AREAS = [
    {'name': 'Entrance', 'top_left': (10, 0), 'bottom_right': (14, 2)},
    {'name': 'Vault', 'top_left': (2,2), 'bottom_right': (6,6)},
    {'name': 'Server Room', 'top_left': (2,20), 'bottom_right': (6,25)},
    {'name': 'Equipment Room', 'top_left': (15,5), 'bottom_right': (20,10)},
]

SAFE_AREAS = [
    {'top_left': (0,0), 'bottom_right': (2,29)},
    {'top_left': (22,0), 'bottom_right': (24,29)},
]

# Add IDs to cameras
CAMERAS = [
    {'id': 1, 'pos': (1,1)},
    {'id': 2, 'pos': (1,28)},
    {'id': 3, 'pos': (12,15)},
    {'id': 4, 'pos': (23,15)}
]

# Rules for AI analysis
RULES = {
    "loitering": {
        "description": "Person stays in restricted area too long",
        "threshold_minutes": 5,
        "penalty": 25
    },
    "unauthorized_access": {
        "description": "Person enters a zone they are not authorized for",
        "penalty": 50
    },
    "after_hours_access": {
        "description": "Access outside of normal operating hours (8am-6pm)",
        "penalty": 15
    }
}
