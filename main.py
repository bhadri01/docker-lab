from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import subprocess
import json
import uvicorn

app = FastAPI()

# Mount templates and static
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Your data (You can move this to a separate file later)
with open("wg0.json") as file:
    data = json.load(file)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    names = list(data.keys())
    return templates.TemplateResponse("index.html", {"request": request, "names": names})

@app.post("/trigger")
async def trigger(name: str = Form(...)):
    try:
        # Run docker_build.py with the selected name
        result = subprocess.run(
            ["python3", "docker_build.py", name],
            capture_output=True,
            text=True,
            check=True
        )
        return JSONResponse(content={"output": result.stdout})
    except subprocess.CalledProcessError as e:
        return JSONResponse(status_code=400, content={"error": e.stderr})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)