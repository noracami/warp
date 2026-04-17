from __future__ import annotations

import math
import re
import subprocess
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import typer
import yaml
from geopy.distance import distance as geopy_distance
from rich.console import Console
from rich.table import Table

APP_PACKAGE = "dev.warp.mockgps"
APP_ACTION_TELEPORT = "dev.warp.mockgps.TELEPORT"
APP_ACTION_STOP = "dev.warp.mockgps.STOP"
DEFAULT_LOCATIONS_FILE = Path("locations.yaml")

console = Console()
app = typer.Typer(help="Mock GPS remote control via ADB.", no_args_is_help=True)


@dataclass(frozen=True)
class Coord:
    lat: float
    lng: float

    def __str__(self) -> str:
        return f"({self.lat:.6f}, {self.lng:.6f})"


@dataclass
class Location:
    name: str
    lat: float
    lng: float
    tags: list[str] = field(default_factory=list)
    timezone: Optional[str] = None
    note: Optional[str] = None

    @property
    def coord(self) -> Coord:
        return Coord(self.lat, self.lng)


_COORD_RE = re.compile(
    r"""^\s*
        (?:lat[:=]?\s*)?
        (-?\d+(?:\.\d+)?)
        \s*[,\s/]\s*
        (?:lng[:=]?\s*|lon[:=]?\s*)?
        (-?\d+(?:\.\d+)?)
        \s*$""",
    re.VERBOSE,
)
_AT_RE = re.compile(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")
_PARAM_RE = re.compile(
    r"[?&](?:q|ll|query|center|daddr|saddr|destination|sll)="
    r"(-?\d+(?:\.\d+)?)(?:%2C|,)(-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_SHORT_HOSTS = ("maps.app.goo.gl", "goo.gl", "g.page", "maps.google.com")


def parse_location(raw: str) -> Optional[Coord]:
    """解析座標字串、Google/Apple Maps URL、逗號分隔 lat,lng。"""
    s = (raw or "").strip()
    if not s:
        return None

    m = _COORD_RE.match(s)
    if m:
        return _safe_coord(m.group(1), m.group(2))

    coord = _parse_url(s)
    if coord:
        return coord

    if any(h in s for h in _SHORT_HOSTS):
        resolved = _resolve_redirect(s)
        if resolved and resolved != s:
            return _parse_url(resolved)
    return None


def _parse_url(url: str) -> Optional[Coord]:
    decoded = urllib.parse.unquote(url)
    m = _AT_RE.search(decoded)
    if m:
        return _safe_coord(m.group(1), m.group(2))
    m = _PARAM_RE.search(decoded)
    if m:
        return _safe_coord(m.group(1), m.group(2))
    return None


def _resolve_redirect(url: str, timeout: float = 5.0) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.url
    except Exception:
        return None


def _safe_coord(lat: str, lng: str) -> Optional[Coord]:
    try:
        la = float(lat)
        ln = float(lng)
    except ValueError:
        return None
    if not (-90.0 <= la <= 90.0) or not (-180.0 <= ln <= 180.0):
        return None
    return Coord(la, ln)


def offset_coord(coord: Coord, dx_m: float, dy_m: float) -> Coord:
    """以目前座標為原點，向東 dx_m、向北 dy_m 公尺計算新座標。"""
    dlat = dy_m / 111111.0
    cos_lat = math.cos(math.radians(coord.lat))
    if abs(cos_lat) < 1e-9:
        cos_lat = 1e-9
    dlng = dx_m / (111111.0 * cos_lat)
    return Coord(coord.lat + dlat, coord.lng + dlng)


def run_adb(args: list[str], serial: Optional[str] = None) -> subprocess.CompletedProcess[str]:
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += args
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        console.print("[red]找不到 adb 指令。請先安裝 Android Platform Tools 並加入 PATH。[/red]")
        raise typer.Exit(code=2)


def ensure_device(serial: Optional[str] = None) -> str:
    result = run_adb(["devices"])
    if result.returncode != 0:
        console.print(f"[red]adb devices 執行失敗：{result.stderr.strip()}[/red]")
        raise typer.Exit(code=2)

    lines = [ln.strip() for ln in result.stdout.splitlines()[1:] if ln.strip()]
    devices = [ln.split("\t")[0] for ln in lines if ln.endswith("device")]

    if not devices:
        console.print("[yellow]尚未連接任何已授權的 ADB 裝置。[/yellow]")
        console.print("請確認：1) USB 已連接 或 已執行 `adb connect <ip>` 2) 手機已允許 USB 偵錯")
        raise typer.Exit(code=1)

    if serial:
        if serial not in devices:
            console.print(f"[red]指定的序號 {serial} 未連接。可用裝置：{', '.join(devices)}[/red]")
            raise typer.Exit(code=1)
        return serial

    if len(devices) > 1:
        console.print(f"[yellow]偵測到多台裝置 {devices}，請透過 --serial 指定。[/yellow]")
        raise typer.Exit(code=1)

    return devices[0]


def send_teleport(coord: Coord, serial: str) -> None:
    args = [
        "shell", "am", "broadcast",
        "-a", APP_ACTION_TELEPORT,
        "-p", APP_PACKAGE,
        "--es", "lat", f"{coord.lat}",
        "--es", "lng", f"{coord.lng}",
    ]
    result = run_adb(args, serial=serial)
    if result.returncode != 0 or "Broadcast completed" not in result.stdout:
        console.print(f"[red]Broadcast 失敗：[/red]\nstdout: {result.stdout}\nstderr: {result.stderr}")
        raise typer.Exit(code=3)


def send_stop(serial: str) -> None:
    args = [
        "shell", "am", "broadcast",
        "-a", APP_ACTION_STOP,
        "-p", APP_PACKAGE,
    ]
    result = run_adb(args, serial=serial)
    if result.returncode != 0 or "Broadcast completed" not in result.stdout:
        console.print(f"[red]Broadcast 失敗：[/red]\nstdout: {result.stdout}\nstderr: {result.stderr}")
        raise typer.Exit(code=3)


def load_locations(path: Path) -> dict[str, Location]:
    if not path.exists():
        example = path.with_name(path.stem + ".example" + path.suffix)
        console.print(f"[red]找不到位置檔：{path}[/red]")
        if example.exists():
            console.print(f"[yellow]提示：複製範本即可開始使用：[/yellow]")
            console.print(f"  [dim]cp {example} {path}[/dim]")
        raise typer.Exit(code=1)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = data.get("locations", {}) or {}
    result: dict[str, Location] = {}
    for name, item in raw.items():
        try:
            tags_raw = item.get("tags") or []
            if isinstance(tags_raw, str):
                tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            else:
                tags = [str(t) for t in tags_raw]
            result[name] = Location(
                name=name,
                lat=float(item["lat"]),
                lng=float(item["lng"]),
                tags=tags,
                timezone=item.get("timezone"),
                note=item.get("note"),
            )
        except (KeyError, TypeError, ValueError) as e:
            console.print(f"[red]位置 {name} 格式錯誤：{e}[/red]")
            raise typer.Exit(code=1)
    return result


def save_locations(path: Path, locations: dict[str, Location]) -> None:
    data: dict[str, dict] = {"locations": {}}
    for name, loc in locations.items():
        entry: dict = {"lat": loc.lat, "lng": loc.lng}
        if loc.tags:
            entry["tags"] = loc.tags
        if loc.timezone:
            entry["timezone"] = loc.timezone
        if loc.note:
            entry["note"] = loc.note
        data["locations"][name] = entry
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def interpolate(start: Coord, end: Coord, step_meters: float) -> list[Coord]:
    total_m = geopy_distance((start.lat, start.lng), (end.lat, end.lng)).meters
    if total_m <= step_meters:
        return [end]
    steps = max(1, int(total_m // step_meters))
    points: list[Coord] = []
    for i in range(1, steps + 1):
        ratio = i / steps
        lat = start.lat + (end.lat - start.lat) * ratio
        lng = start.lng + (end.lng - start.lng) * ratio
        points.append(Coord(lat=lat, lng=lng))
    return points


@app.command()
def teleport(
    query: Optional[str] = typer.Argument(
        None,
        help='位置名稱 / "lat,lng" / Google Maps URL。',
    ),
    lat: Optional[float] = typer.Option(None, "--lat", help="緯度"),
    lng: Optional[float] = typer.Option(None, "--lng", help="經度"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="locations.yaml 內的名稱"),
    file: Path = typer.Option(DEFAULT_LOCATIONS_FILE, "--file", "-f", help="位置檔案路徑"),
    serial: Optional[str] = typer.Option(None, "--serial", "-s", help="ADB 裝置序號"),
):
    """傳送到指定座標、URL 或命名位置。"""
    device = ensure_device(serial)

    coord: Optional[Coord] = None
    label: str = ""

    if name:
        loc = load_locations(file).get(name)
        if not loc:
            console.print(f"[red]找不到位置：{name}[/red]")
            raise typer.Exit(code=1)
        coord, label = loc.coord, f"{name} {loc.coord}"
    elif lat is not None and lng is not None:
        coord = Coord(lat=lat, lng=lng)
        label = str(coord)
    elif query:
        if file.exists():
            loc = load_locations(file).get(query)
            if loc:
                coord, label = loc.coord, f"{query} {loc.coord}"
        if coord is None:
            parsed = parse_location(query)
            if parsed:
                coord, label = parsed, str(parsed)

    if coord is None:
        console.print("[red]無法解析位置。支援格式：[/red]")
        console.print("  [dim]• 名稱（例：Home）[/dim]")
        console.print("  [dim]• 座標字串（例：'25.0339, 121.5644'）[/dim]")
        console.print("  [dim]• Google Maps URL（含 @lat,lng 或 ?q=lat,lng）[/dim]")
        console.print("  [dim]• --lat 與 --lng[/dim]")
        raise typer.Exit(code=1)

    console.print(f"[cyan]{device}[/cyan] → Teleport {label}")
    send_teleport(coord, device)
    console.print("[green]✓ 完成[/green]")


@app.command("list")
def list_locations(
    file: Path = typer.Option(DEFAULT_LOCATIONS_FILE, "--file", "-f"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="以 tag 過濾"),
):
    """列出 locations.yaml 中所有位置。"""
    locs = load_locations(file)
    table = Table(title=str(file))
    table.add_column("Name", style="cyan")
    table.add_column("Lat", justify="right")
    table.add_column("Lng", justify="right")
    table.add_column("Tags", style="magenta")
    table.add_column("TZ", style="yellow")
    table.add_column("Note", style="dim")
    for loc in locs.values():
        if tag and tag not in loc.tags:
            continue
        table.add_row(
            loc.name,
            f"{loc.lat:.6f}",
            f"{loc.lng:.6f}",
            ", ".join(loc.tags),
            loc.timezone or "",
            loc.note or "",
        )
    console.print(table)


@app.command()
def add(
    name: str = typer.Argument(..., help="位置名稱"),
    lat: float = typer.Option(..., "--lat", help="緯度"),
    lng: float = typer.Option(..., "--lng", help="經度"),
    tags: Optional[str] = typer.Option(None, "--tags", help="逗號分隔標籤，例如 Taipei,outdoor"),
    timezone: Optional[str] = typer.Option(None, "--tz", help="時區，例如 Asia/Taipei"),
    note: Optional[str] = typer.Option(None, "--note", help="備註"),
    file: Path = typer.Option(DEFAULT_LOCATIONS_FILE, "--file", "-f"),
    force: bool = typer.Option(False, "--force", help="覆蓋同名位置"),
):
    """新增一個位置到 locations.yaml。"""
    locs = load_locations(file) if file.exists() else {}
    if name in locs and not force:
        console.print(f"[red]{name} 已存在。加 --force 可覆蓋。[/red]")
        raise typer.Exit(code=1)

    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    tag_list = [t for t in tag_list if t]

    locs[name] = Location(
        name=name,
        lat=lat,
        lng=lng,
        tags=tag_list,
        timezone=timezone,
        note=note,
    )
    save_locations(file, locs)
    console.print(f"[green]✓ 已新增 {name} ({lat}, {lng}) → {file}[/green]")


@app.command()
def move(
    from_name: Optional[str] = typer.Option(None, "--from", help="起點名稱"),
    to_name: Optional[str] = typer.Option(None, "--to", help="終點名稱"),
    from_lat: Optional[float] = typer.Option(None, "--from-lat"),
    from_lng: Optional[float] = typer.Option(None, "--from-lng"),
    to_lat: Optional[float] = typer.Option(None, "--to-lat"),
    to_lng: Optional[float] = typer.Option(None, "--to-lng"),
    speed: float = typer.Option(1.4, "--speed", help="走路速度 m/s，預設 1.4"),
    interval: float = typer.Option(1.0, "--interval", help="每次發送間隔秒數"),
    file: Path = typer.Option(DEFAULT_LOCATIONS_FILE, "--file", "-f"),
    serial: Optional[str] = typer.Option(None, "--serial", "-s"),
):
    """模擬從起點走到終點。"""
    device = ensure_device(serial)

    start: Optional[Coord] = None
    end: Optional[Coord] = None

    if from_name or to_name:
        locs = load_locations(file)
        if from_name:
            loc = locs.get(from_name)
            start = loc.coord if loc else None
        if to_name:
            loc = locs.get(to_name)
            end = loc.coord if loc else None

    if start is None and from_lat is not None and from_lng is not None:
        start = Coord(from_lat, from_lng)
    if end is None and to_lat is not None and to_lng is not None:
        end = Coord(to_lat, to_lng)

    if start is None or end is None:
        console.print("[red]請提供完整的起點與終點（名稱或經緯度）。[/red]")
        raise typer.Exit(code=1)

    step_m = speed * interval
    points = interpolate(start, end, step_m)
    total_m = geopy_distance((start.lat, start.lng), (end.lat, end.lng)).meters

    console.print(
        f"[cyan]{device}[/cyan] Move {start} → {end} "
        f"(距離 {total_m:.1f} m, 步長 {step_m:.1f} m, 共 {len(points)} 步)"
    )

    send_teleport(start, device)
    for i, p in enumerate(points, 1):
        time.sleep(interval)
        send_teleport(p, device)
        console.print(f"  [{i}/{len(points)}] {p}")

    console.print("[green]✓ 抵達終點[/green]")


@app.command()
def stop(serial: Optional[str] = typer.Option(None, "--serial", "-s")):
    """停止 Mock GPS 服務。"""
    device = ensure_device(serial)
    console.print(f"[cyan]{device}[/cyan] → Stop mock GPS")
    send_stop(device)
    console.print("[green]✓ 已停止[/green]")


@app.command()
def dashboard(
    file: Path = typer.Option(DEFAULT_LOCATIONS_FILE, "--file", "-f"),
    serial: Optional[str] = typer.Option(None, "--serial", "-s"),
):
    """啟動互動式 TUI 儀表板（方向鍵走位、選單傳送、新增點位）。"""
    device = ensure_device(serial)
    from tui import run_dashboard
    run_dashboard(file=file, serial=device)


@app.command()
def devices():
    """列出目前連接的 ADB 裝置。"""
    result = run_adb(["devices"])
    console.print(result.stdout.strip() or "[dim](無輸出)[/dim]")


if __name__ == "__main__":
    app()
