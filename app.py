from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
import pandas as pd
from tasks import drop, crt, pdg, landrun, elbow, angle, race

app = FastAPI()

@app.get("/")
def status():
    return {"message": "Balloon Task API is running"}

@app.post("/task")
async def handle_task(
    task: str = Form(...),
    ref_deg: float = Form(0.0),
    min_dist: float = Form(0.0),
    launch_height: int = Form(0),
    target_height: int = Form(0),
    min_cruise: int = Form(0),
    max_cruise: int = Form(0),
    q1: str = Form(""),
    csv_file: UploadFile = File(...)
):
    df = pd.read_csv(csv_file.file)
    if task == "drop":
        return drop.run(df, q1)
    if task == "crt":
        return crt.run(df, min_dist, launch_height, target_height, min_cruise, max_cruise)
    if task == "pdg":
        return pdg.run(df, launch_height, target_height, min_dist)
    if task == "landrun":
        return landrun.run(df)
    if task == "elbow":
        return elbow.run(df)
    if task == "angle":
        return angle.run(df, ref_deg)
    if task == "race":
        return race.run(df, min_dist, min_cruise, max_cruise, q1)
    return JSONResponse(content={"error": "Task not found"}, status_code=400)
