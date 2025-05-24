from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import numpy as np

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def normalize_columns(df):
    rename_map = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if "altitude" in col_lower:
            rename_map[col] = "Altitude"
        elif "heading" in col_lower:
            rename_map[col] = "WindDirection"
        elif "speed" in col_lower:
            rename_map[col] = "WindSpeed"
    df = df.rename(columns=rename_map)
    return df


def collapse_low_levels(df):
    return df


def simulate_descent(df, release_height, target_height):
    release_height_m = release_height * 0.3048
    target_height_m = target_height * 0.3048
    df = df[(df['Altitude'] <= release_height_m)
            & (df['Altitude'] >= target_height_m)].sort_values(
                by='Altitude', ascending=False).reset_index(drop=True)
    positions = [(0, 0)]
    altitudes = df['Altitude'].tolist()
    directions = df['WindDirection'].tolist()
    speeds = df['WindSpeed'].tolist()
    descent_rate = 10.7
    for i in range(1, len(altitudes)):
        h1 = altitudes[i - 1]
        h2 = altitudes[i]
        delta_h = h1 - h2
        t = delta_h / descent_rate

        dir1 = directions[i - 1]
        dir2 = directions[i]
        spd1 = speeds[i - 1]
        spd2 = speeds[i]

        dir_avg = np.deg2rad((dir1 + dir2) / 2)
        spd_avg = (spd1 + spd2) / 2

        dx = spd_avg * t * np.sin(dir_avg)
        dy = spd_avg * t * np.cos(dir_avg)

        last_x, last_y = positions[-1]
        positions.append((last_x + dx, last_y + dy))

    final_x, final_y = positions[-1]
    distance = np.sqrt(final_x**2 + final_y**2)
    heading_rad = np.arctan2(final_x, final_y)
    heading_deg = (np.rad2deg(heading_rad) + 360) % 360
    return heading_deg, distance, final_x, final_y


def generate_visual(final_x, final_y, heading_deg, distance):
    fig, ax = plt.subplots(figsize=(6, 6))
    margin = distance * 1.2
    ax.set_xlim(-margin, margin)
    ax.set_ylim(-margin, margin)
    ax.set_aspect('equal')
    ax.set_xlabel("East")
    ax.set_ylabel("North")
    ax.plot(0, 0, 'ro')  # Red dot at center (target)

    # Ring around target
    circle = plt.Circle((0, 0),
                        distance,
                        color='gray',
                        linestyle='--',
                        fill=False)
    ax.add_patch(circle)

    # Arrow from wind origin to center
    ax.arrow(-final_x,
             -final_y,
             final_x,
             final_y,
             head_width=15,
             head_length=20,
             fc='blue',
             ec='blue')

    # Annotate heading and distance
    ax.text(final_x / 2,
            final_y / 2,
            f"{heading_deg:.0f}°\n{distance:.0f} m",
            fontsize=13,
            ha='center',
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray"))

    plt.grid(True)
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    return f"<img src='data:image/png;base64,{img_str}'/>"


@app.get("/drop", response_class=HTMLResponse)
async def drop_form():
    return """
    <html>
        <body>
            <h2>DROP Task - Upload Wind CSV</h2>
            <form action="/drop" enctype="multipart/form-data" method="post">
                <label for='file'>CSV Wind Data File:</label><br>
                <input name="file" type="file"><br><br>
                <label for='release_height'>Release Height (ft MSL):</label><br>
                <input name="release_height" type="number" placeholder="e.g. 2000" value="2000"><br><br>
                <label for='target_height'>Target Height (ft MSL):</label><br>
                <input name="target_height" type="number" placeholder="e.g. 100" value="100"><br><br>
                <input type="submit" value="Submit">
            </form>
        </body>
    </html>
    """


@app.post("/drop", response_class=HTMLResponse)
async def drop_task(
        file: UploadFile = File(...),
        release_height: float = Form(...),
        target_height: float = Form(...),
):
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        df = normalize_columns(df)
        required_cols = {'Altitude', 'WindDirection', 'WindSpeed'}
        if not required_cols.issubset(df.columns):
            return "<h3>Error: Missing required columns after normalization.</h3>"
        df = collapse_low_levels(df)
        heading, distance, final_x, final_y = simulate_descent(
            df, release_height, target_height)
        visual = generate_visual(final_x, final_y, heading, distance)
        summary = f"""
        <h2>DROP Result</h2>
        <p><b>Release height:</b> {release_height} ft MSL</p>
        <p><b>Target height:</b> {target_height} ft MSL</p>
        <p><b>Descent rate:</b> 10.7 m/s</p>
        <p><b>Drift heading:</b> {heading:.1f}° (direction of travel)</p>
        <p><b>Total drift distance:</b> {distance:.1f} meters</p>
        {visual}
        """
        return summary
    except Exception as e:
        return f"<h3>Error processing file: {str(e)}</h3>"
@app.get("/", response_class=HTMLResponse)
async def root_redirect():
    return await drop_form()
# trigger redeploy
