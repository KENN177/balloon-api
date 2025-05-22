from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, HTMLResponse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import StringIO, BytesIO
import base64

app = FastAPI()

@app.get("/")
def status():
    return {"message": "Balloon Task API is running"}

@app.get("/drop", response_class=HTMLResponse)
async def drop_form():
    return '''
    <html>
        <body>
            <h2>DROP Task - Upload Wind CSV</h2>
            <form action="/drop" enctype="multipart/form-data" method="post">
                <input name="file" type="file"><br><br>
                <input name="release_height" type="number" placeholder="Release Height (ft MSL)" value="2000"><br><br>
                <input name="target_height" type="number" placeholder="Target Height (ft MSL)" value="1000"><br><br>
                <input type="submit">
            </form>
        </body>
    </html>
    '''

@app.post("/drop")
async def run_drop(
    file: UploadFile = File(...),
    release_height: int = Form(...),
    target_height: int = Form(...)
):
    contents = await file.read()
    df = pd.read_csv(StringIO(contents.decode("utf-8")))

    dx, dy = 0, 0
    for i in range(len(df)-1):
        h1, h2 = df.iloc[i]['Altitude'], df.iloc[i+1]['Altitude']
        if not (target_height <= h1 <= release_height or target_height <= h2 <= release_height):
            continue
        dz = abs(h2 - h1)
        dir_avg = (df.iloc[i]['WindDirection'] + df.iloc[i+1]['WindDirection']) / 2
        spd_avg = (df.iloc[i]['WindSpeed'] + df.iloc[i+1]['WindSpeed']) / 2
        t = dz / 10.7
        drift = spd_avg * 1000 / 3600 * t
        rad = np.deg2rad(dir_avg)
        dx += drift * np.sin(rad)
        dy += drift * np.cos(rad)

    distance = np.sqrt(dx**2 + dy**2)
    heading = (np.degrees(np.arctan2(dx, dy)) + 360) % 360

    fig, ax = plt.subplots()
    ax.arrow(-dx, -dy, dx, dy, head_width=30, head_length=30, fc='blue', ec='blue')
    ax.plot(0, 0, 'ro')
    ax.set_title("DROP Drift Path")
    ax.set_aspect('equal')
    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    img_str = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {
        "release_height": release_height,
        "target_height": target_height,
        "heading": round(heading),
        "distance_m": round(distance, 1),
        "visual": f"data:image/png;base64,{img_str}"
    }
