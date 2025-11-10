import numpy as np
from config import WAREHOUSE_ROWS, WAREHOUSE_COLS, ZONE_WALKWAY, ZONE_RESTRICTED, ZONE_SAFE, ZONE_CAMERA, ZONE_ENTRANCE, RESTRICTED_AREAS, SAFE_AREAS, CAMERAS

def build_warehouse_matrix():
    # Builds the warehouse grid and returns it along with text labels for UI rendering.
    warehouse = np.full((WAREHOUSE_ROWS, WAREHOUSE_COLS), ZONE_WALKWAY)
    labels = []

    # Mark restricted zones and add labels
    for area in RESTRICTED_AREAS:
        r1, c1 = area['top_left']
        r2, c2 = area['bottom_right']
        zone_type = ZONE_ENTRANCE if area['name'] == 'Entrance' else ZONE_RESTRICTED
        warehouse[r1:r2+1, c1:c2+1] = zone_type
        labels.append({"text": area['name'], "y": (r1 + r2 + 1) / 2, "x": (c1 + c2 + 1) / 2})

    # Mark safe areas
    for area in SAFE_AREAS:
        r1, c1 = area['top_left']
        r2, c2 = area['bottom_right']
        warehouse[r1:r2+1, c1:c2+1] = ZONE_SAFE

    # Mark cameras and add labels
    for cam in CAMERAS:
        r, c = cam['pos']
        warehouse[r, c] = ZONE_CAMERA
        labels.append({"text": str(cam['id']), "y": r, "x": c})

    return warehouse, labels
