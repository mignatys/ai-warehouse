from config import RULES

def analyze_person_journey_locally(events):
    # Analyzes a person's event journey locally to detect violations and calculate a risk score.
    violations = []
    
    for event in events:
        # Check for unauthorized access on entry
        if event['event_type'] == 'person_entered' and not event['authorized']:
            violations.append({"type": "unauthorized_access", "zone": event["zone"]})
            
        # Check for loitering on exit
        if event['event_type'] == 'person_exited' and event.get('duration_minutes', 0) > event.get('allowed_minutes', 5):
            violations.append({"type": "loitering", "zone": event["zone"]})
            
        # Check for after-hours access
        ts = event['timestamp']
        hour = int(ts[11:13])
        if hour < 8 or hour >= 18:
            # To avoid spam, we only add one after-hours violation per journey
            if not any(v['type'] == 'after_hours_access' for v in violations):
                violations.append({"type": "after_hours_access", "zone": event["zone"]})

    if not violations:
        return None

    # --- Calculate Risk Score ---
    total_score = 0
    issue_types_found = set()
    
    # Create a count of each violation type
    violation_counts = {}
    for v in violations:
        violation_counts[v["type"]] = violation_counts.get(v["type"], 0) + 1
        issue_types_found.add(v["type"])

    # Calculate score based on counts
    for issue_type, count in violation_counts.items():
        if issue_type in RULES:
            base = RULES[issue_type]['penalty']
            total_score += base * (1 + (count - 1) * 0.5)

    # Apply cross-category multiplier
    if len(issue_types_found) > 1:
        total_score *= 1.2

    return {
        "violations": violations, # Return the detailed list
        "issues": ", ".join(sorted(list(issue_types_found))),
        "risk_score": int(total_score)
    }
