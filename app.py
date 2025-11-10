import json
import zipfile
import io
import os
import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from layout import build_warehouse_matrix
from event_generator import generate_synthetic_dataset, save_dataset, PERSONS
from ai_openai import process_all_events, get_incident_summary_prompt, get_daily_summary_prompt
from config import ZONE_ENTRANCE, ZONE_RESTRICTED, ZONE_SAFE, ZONE_CAMERA
from analyzer import analyze_person_journey_locally

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def _create_debug_dumps(analysis_result):
    """Helper function to create all data dumps for debugging."""
    os.makedirs("data/", exist_ok=True)
    # 1. Create the aggregated AI input data
    ai_input_prompts = {}
    events_by_person = {}
    person_map = {p["id"]: p for p in PERSONS}

    for event in analysis_result["events"]:
        person_id = event["person_id"]
        if person_id not in events_by_person: events_by_person[person_id] = []
        events_by_person[person_id].append(event)

    for person_id, person_events in events_by_person.items():
        local_analysis = analyze_person_journey_locally(person_events)
        if local_analysis:
            person_info = person_map[person_id]
            ai_input_prompts[f"incident_prompt_{person_info['name']}"] = get_incident_summary_prompt(person_id, person_info["authorized_zones"], local_analysis, person_events)
    
    ai_input_prompts["daily_summary_prompt"] = get_daily_summary_prompt(analysis_result["analysis"])
    
    with open("data/ai_prompts.json", "w") as f:
        json.dump(ai_input_prompts, f, indent=2)

    # 2. Create the final AI analysis output dump
    with open("data/ai_analysis_output.json", "w") as f:
        json.dump(analysis_result, f, indent=2)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    person_data = {p["name"]: p["authorized_zones"] for p in PERSONS}
    return templates.TemplateResponse("dashboard.html", {"request": request, "person_data": person_data})

@app.get("/layout", response_class=HTMLResponse)
async def get_layout():
    warehouse, labels = build_warehouse_matrix()
    grid_html = ""
    for row in warehouse:
        for cell in row:
            css_class = "walkway"
            if cell == ZONE_RESTRICTED: css_class = "restricted"
            elif cell == ZONE_SAFE: css_class = "safe"
            elif cell == ZONE_CAMERA: css_class = "camera"
            elif cell == ZONE_ENTRANCE: css_class = "entrance"
            grid_html += f'<div class="grid-item {css_class}"></div>'
    labels_html = ""
    for label in labels:
        y_pos = label["y"] * 20 + 10
        x_pos = label["x"] * 20 + 10
        labels_html += f'<div class="grid-label" style="top: {y_pos}px; left: {x_pos}px;">{label["text"]}</div>'
    return HTMLResponse(content=grid_html + labels_html)

@app.post("/generate_and_analyze")
async def generate_and_analyze():
    # Generate fresh event data
    events = generate_synthetic_dataset(num_events_per_person=1)
    save_dataset(events, "data/warehouse_events.json")
    
    # Run the full analysis pipeline
    analysis_result = process_all_events()
    
    # Create all necessary data dumps for debugging
    _create_debug_dumps(analysis_result)
        
    return analysis_result

@app.get("/download")
async def download_files():
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        files_to_zip = {
            "data/warehouse_events.json": "raw_events.json",
            "data/ai_prompts.json": "ai_prompts.json",
            "data/ai_analysis_output.json": "ai_outputs.json"
        }
        for file_path, arc_name in files_to_zip.items():
            if os.path.exists(file_path):
                zf.write(file_path, arc_name)
    
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": f"attachment; filename=warehouse_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"}
    )
