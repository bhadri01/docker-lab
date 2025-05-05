from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio
import json
import uvicorn

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Safe load wg0.json
data = {}
wg_file = Path("wg0.json")
if wg_file.is_file():
    with wg_file.open() as file:
        data = json.load(file)
else:
    print("Warning: wg0.json file not found.")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, tag: str = None):
    names = list(data.keys())

    # Even if data is empty, still create user_ips
    user_ips = {}
    if data:
        for name, details in data.items():
            interface = details.get("Interface", {})
            address = interface.get("Address", "")
            ip = address.split("/")[0] if address else ""
            user_ips[name] = ip

    selected_name = tag if tag in names else None

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "names": names,
            "selected_name": selected_name,
            "user_ips": user_ips,  # even if empty, safe
        }
    )


@app.get("/stream/{name}")
async def stream(name: str):
    async def event_generator():
        docker_config_path = Path.home() / ".docker" / "config.json"
        docker_config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(docker_config_path, "w") as f:
            json.dump({"auths": {}}, f)

        yield f"data: 🔄 Docker config reset successfully.\n\n"

        process = await asyncio.create_subprocess_exec(
            "python3", "docker_build.py", name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        while True:
            line = await process.stdout.readline()
            if not line:
                break
            yield f"data: {line.decode().strip()}\n\n"

        await process.wait()
        yield f"data: --- ✅ Build Completed ---\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/code-server-stream/{name}")
async def code_server_stream(name: str):
    async def event_generator():
        try:
            cmd = [
                "docker", "exec", "-td",
                "-u", name,
                name,
                "code-server",
                "--config", f"/home/{name}/.config/code-server/docker.yaml"
            ]

            yield f"data: 🚀 Starting code-server for {name}...\n\n"

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                yield f"data: {line.decode().strip()}\n\n"

            await process.wait()

            if process.returncode == 0:
                yield f"data: --- ✅ Code-Server Started Successfully ---\n\n"
            else:
                yield f"data: --- ❌ Failed to start Code-Server (Exit Code {process.returncode}) ---\n\n"

        except Exception as e:
            yield f"data: ❌ Error: {str(e)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
