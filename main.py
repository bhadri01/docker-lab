from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import json
import asyncio
from pathlib import Path
import uvicorn


app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Your data (You can move this to a separate file later)
with open("wg0.json") as file:
    data = json.load(file)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    names = list(data.keys())
    return templates.TemplateResponse("index.html", {"request": request, "names": names})

@app.get("/stream/{name}")
async def stream(name: str):
    async def event_generator():
        # Step 1: Reset Docker config before running anything
        docker_config_path = Path.home() / ".docker" / "config.json"
        docker_config_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure ~/.docker folder exists

        with open(docker_config_path, "w") as f:
            json.dump({"auths": {}}, f)

        yield f"data: 🔄 Docker config reset successfully.\n\n"

        # Step 2: Start the docker_build.py subprocess
        process = await asyncio.create_subprocess_exec(
            "python3", "docker_build.py", name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        while True:
            line = await process.stdout.readline()
            if not line:
                break
            # Stream each line
            yield f"data: {line.decode().strip()}\n\n"

        # Wait for process end
        await process.wait()

        # Final message
        yield f"data: --- ✅ Build Completed ---\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)