import json
import typer
import docker
from pathlib import Path

app = typer.Typer()



def remove_containers(client, status):
    containers = client.containers.list(all=True, filters={"status": status})
    for c in containers:
        try:
            print(f"Removing {status} container: {c.name} ({c.id[:12]})")
            c.remove(force=True)
        except docker.errors.APIError as e:
            print(f"  ⚠️  Could not remove {c.name}: {e}")
    print(f"{'No' if not containers else 'All'} '{status}' containers processed.")

def write_wg_conf(username: str, json_path: Path, conf_path: Path):
    """
    Load wg0.json, extract the user block, and write wg0.conf.
    """
    if not json_path.is_file():
        typer.secho(f"wg0.json not found at {json_path}", fg="red")
        raise typer.Exit(code=1)

    data = json.loads(json_path.read_text())
    user_cfg = data.get(username)
    if not user_cfg:
        typer.secho(f"No WireGuard entry for user '{username}' in {json_path}", fg="red")
        raise typer.Exit(code=1)

    lines = ["[Interface]"]
    for key, val in user_cfg["Interface"].items():
        lines.append(f"{key} = {val}")

    lines += ["", "[Peer]"]
    for key, val in user_cfg["Peer"].items():
        lines.append(f"{key} = {val}")

    conf = "\n".join(lines) + "\n"
    conf_path.write_text(conf)
    typer.secho(f"✔️  Written WireGuard config to {conf_path}", fg="green")

@app.command()
def build(
    username: str,
    wg_json: Path = Path("wg0.json"),
    wg_conf: Path = Path("wg0.conf"),
):
    """
    Build an image, prune old containers, write wg0.conf based on username, and run with a named Docker volume.
    """
    image_name     = f"{username}_docker"
    container_name = username
    volume_name    = f"{username}_data"
    hostname       = "youngstorageultra"
    network_name   = "dind"

    # Ensure the network exists (use a temporary client so the main client can still be created later)
    tmp_client = docker.from_env()
    try:
        existing = tmp_client.networks.list(names=[network_name])
        if not existing:
            typer.secho(f"➕ Creating network '{network_name}'", fg="yellow")
            tmp_client.networks.create(name=network_name)
        else:
            typer.secho(f"🔎 Network '{network_name}' already exists", fg="blue")
    except docker.errors.APIError as e:
        typer.secho(f"⚠️  Could not ensure network '{network_name}': {e}", fg="red")
    finally:
        try:
            tmp_client.close()
        except Exception:
            pass

    client = docker.from_env()

    # 0) generate wg0.conf
    write_wg_conf(username, wg_json, wg_conf)

    # 1) Build
    typer.secho(f"🔨 Building image {image_name}…", fg="cyan")
    client.images.build(
        path=".",
        tag=image_name,
        buildargs={"USERNAME": username},
        nocache=True
    )
    typer.secho("✅ Build complete", fg="green")

    # 2) Cleanup exited/created
    remove_containers(client, "exited")
    remove_containers(client, "created")

    # 3) Ensure named volume exists
    existing = [v.name for v in client.volumes.list()]
    if volume_name not in existing:
        typer.secho(f"➕ Creating volume '{volume_name}'", fg="yellow")
        client.volumes.create(name=volume_name)
    else:
        typer.secho(f"🔎 Volume '{volume_name}' already exists", fg="blue")

    # 4) Remove old container
    try:
        old = client.containers.get(container_name)
        typer.secho(f"🗑  Removing old container '{container_name}'", fg="yellow")
        old.stop()
        old.remove()
    except docker.errors.NotFound:
        pass

    # 5) Run container
    typer.secho(f"▶️  Starting '{container_name}' with named volume '{volume_name}'", fg="cyan")
    client.containers.run(
        image_name,
        name=container_name,
        hostname=hostname,
        network=network_name,
        volumes=[f"{volume_name}:/home/{username}:rw"],
        detach=True,
        cap_add=["NET_ADMIN"],
        restart_policy={"Name": "always"},
        runtime="sysbox-runc"
    )
    typer.secho("🚀 Container is up and running!", fg="green")

if __name__ == "__main__":
    app()
