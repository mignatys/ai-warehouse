import json
import time
from openai import OpenAI
from config import RULES
from event_generator import PERSONS
from analyzer import analyze_person_journey_locally

# --- DEBUG FLAG ---
DEBUG = True

def get_api_key():
    # Reads the API key from the data/token file.
    try:
        with open("data/token") as f:
            return f.read().strip()
    except FileNotFoundError:
        print("ERROR: `data/token` file not found. Please create it and add your OpenAI API key.")
        return None

api_key = get_api_key()
client = OpenAI(api_key=api_key) if api_key else None

MODEL_NAME = "gpt-4o-mini"
COST_INPUT_PER_MILLION_TOKENS = 0.60
COST_OUTPUT_PER_MILLION_TOKENS = 2.40

def _make_ai_call_with_retry(prompt, system_message, retries=1):
    if not client:
        return None, None
    if DEBUG:
        print("\n----- AI PROMPT -----\n")
        print(prompt)
        print("\n---------------------\n")
    for i in range(retries + 1):
        try:
            response = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "system", "content": system_message}, {"role": "user", "content": prompt}], temperature=0)
            content = response.choices[0].message.content
            if DEBUG:
                print(f"\n----- AI RAW OUTPUT (Attempt {i+1}) -----\n")
                print(content)
                print("\n----------------------------------\n")
            if content:
                if content.strip().startswith("```json"):
                    content = content.strip()[7:-3]
                return json.loads(content), response.usage
        except Exception as e:
            print(f"AI call attempt {i+1} failed. Error: {e}")
            if i < retries:
                time.sleep(1)
    return None, None

def get_incident_summary_prompt(person_id, authorized_zones, local_analysis, events):
    # Generates the prompt for the AI to act as a storyteller for an incident.
    event_text = "\n".join([f"{e['timestamp']} | {e['event_type']} in {e['zone']}" for e in events])
    # NEW: Instruct the AI to use a placeholder.
    return f"""A security analysis for person ID '{person_id}' has flagged violations with a risk score of {local_analysis['risk_score']}.
This person is authorized for the following zones: {authorized_zones}.
The detected violations are:
- {local_analysis['issues']}

Based on the full event log below, write a human-readable narrative summary and provide actionable recommendations.
IMPORTANT: In your response, use the placeholder '[PERSON_NAME]' instead of the person's actual ID.

Event Log:
{event_text}

Respond with a single JSON object with two keys:
1. "summary": A narrative of the person's journey (e.g., "[PERSON_NAME] entered the warehouse at...").
2. "recommendation": A list of brief, actionable steps (e.g., "Issue a formal warning to [PERSON_NAME]")."""

def get_daily_summary_prompt(incidents):
    # Generates the analytical prompt for the daily summary.
    if not incidents:
        return None
    
    incidents_for_prompt = []
    for i in incidents:
        issues_dict = {v["type"]: v["zone"] for v in i["violations"]}
        incidents_for_prompt.append({
            "person_id": i["person_id"],
            "issues": issues_dict
        })

    return f"""You are a security shift supervisor analyzing all incidents from the day. Your task is to identify patterns and provide a high-level analytical summary.

Today's Incidents:
{json.dumps(incidents_for_prompt, indent=2)}

Based on the data, respond with a single JSON object with two keys:
1. "summary": An analytical overview object with keys "offenders" (a list of objects with "person_id" and "violations"), "hot_spot_zones", and "common_violations".
2. "actionable_items": A list of objects with well argumented actionable recomendations, where each object has an "action" and other relevant details."""

def process_all_events(json_file="data/warehouse_events.json"):
    # The main processing pipeline with local-first analysis and AI calls for natural language summary.
    with open(json_file) as f:
        events = json.load(f)

    events_by_person = {p["id"]: [] for p in PERSONS}
    for event in events:
        if event["person_id"] in events_by_person:
            events_by_person[event["person_id"]].append(event)

    person_details_map = {p["id"]: p for p in PERSONS}
    all_incidents = []
    total_input_tokens, total_output_tokens = 0, 0

    for person_id, person_events in events_by_person.items():
        if not person_events: continue
        local_analysis = analyze_person_journey_locally(person_events)
        
        if local_analysis:
            person_info = person_details_map[person_id]
            prompt = get_incident_summary_prompt(person_id, person_info["authorized_zones"], local_analysis, person_events)
            ai_summary, usage = _make_ai_call_with_retry(prompt, "You are a security AI writing an incident summary in JSON.")
            
            if usage:
                total_input_tokens += usage.prompt_tokens
                total_output_tokens += usage.completion_tokens
            
            # Substitute the [PERSON_NAME] placeholder with the actual name
            if ai_summary and ai_summary.get("summary"):
                ai_summary["summary"] = ai_summary["summary"].replace("[PERSON_NAME]", person_info["name"])
            if ai_summary and ai_summary.get("recommendation"):
                ai_summary["recommendation"] = [rec.replace("[PERSON_NAME]", person_info["name"]) for rec in ai_summary["recommendation"]]

            full_incident = {
                "person_id": person_id,
                "person_name": person_info["name"],
                **local_analysis,
                **(ai_summary or {"summary": "AI summary failed.", "recommendation": "Review logs."})
            }
            all_incidents.append(full_incident)

    summary_prompt = get_daily_summary_prompt(all_incidents)
    summary_data, summary_usage = {"summary": "No incidents to summarize.", "actionable_items": []}, None
    if summary_prompt:
        summary_data, summary_usage = _make_ai_call_with_retry(summary_prompt, "You are a security manager creating a daily report in JSON.")
        if summary_usage:
            total_input_tokens += summary_usage.prompt_tokens
            total_output_tokens += summary_usage.completion_tokens

    input_cost = (total_input_tokens / 1_000_000) * COST_INPUT_PER_MILLION_TOKENS
    output_cost = (total_output_tokens / 1_000_000) * COST_OUTPUT_PER_MILLION_TOKENS

    return {
        "analysis": all_incidents,
        "daily_summary": summary_data or {"summary": "AI summary generation failed.", "actionable_items": ["Check logs."]},
        "events": events,
        "usage_stats": {
            "model": MODEL_NAME, "input_tokens": total_input_tokens, "output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens, "input_cost": f"{input_cost:.6f}",
            "output_cost": f"{output_cost:.6f}", "total_cost": f"{input_cost + output_cost:.6f}"
        }
    }
