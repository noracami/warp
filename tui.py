from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, Label, Markdown, Static

from main import (
    APP_ACTION_STOP,
    APP_ACTION_TELEPORT,
    APP_PACKAGE,
    Coord,
    Location,
    load_locations,
    offset_coord,
    parse_location,
    save_locations,
)

STEP_SIZES: list[float] = [1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]


def _adb_broadcast_teleport(coord: Coord, serial: str) -> tuple[bool, str]:
    args = [
        "adb", "-s", serial, "shell", "am", "broadcast",
        "-a", APP_ACTION_TELEPORT,
        "-p", APP_PACKAGE,
        "--es", "lat", f"{coord.lat}",
        "--es", "lng", f"{coord.lng}",
    ]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode == 0 and "Broadcast completed" in r.stdout:
        return True, ""
    return False, (r.stderr or r.stdout).strip()[:80]


def _adb_broadcast_stop(serial: str) -> tuple[bool, str]:
    args = [
        "adb", "-s", serial, "shell", "am", "broadcast",
        "-a", APP_ACTION_STOP,
        "-p", APP_PACKAGE,
    ]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode == 0 and "Broadcast completed" in r.stdout:
        return True, ""
    return False, (r.stderr or r.stdout).strip()[:80]


def _closest_index(arr: list[float], value: float) -> int:
    best = 0
    best_diff = abs(arr[0] - value)
    for i, v in enumerate(arr):
        d = abs(v - value)
        if d < best_diff:
            best, best_diff = i, d
    return best


HELP_TEXT = """\
# Mock GPS · 儀表板使用說明

## 移動（模擬走路）
- **↑ ↓ ← →** — 往 N / S / W / E 走一步（依目前步長）
- **+ / -** — 調整步長（1 / 2 / 5 / 10 / 20 / 50 / 100 公尺）

每次按方向鍵都會送一次 teleport，手機 app 端會持續以該座標餵給系統。

## 位置清單
- **j / k** — 向下 / 向上選取（清單上下方有方向提示）
- **Enter** — 傳送到目前選取的位置
- **/** — 搜尋（子字串比對 name / tags / timezone / note）
- **c** — 清除搜尋過濾

位置資料儲存於 `locations.yaml`（人可讀、可版控、可手動編輯）。

## 貼上（Paste）
- **p** — 開啟貼上視窗，支援以下格式：
  - `25.0339, 121.5644` / `25.0339 121.5644` / `lat:25.03, lng:121.56`
  - `https://www.google.com/maps/@35.6895,139.6917,15z`
  - `https://www.google.com/maps?q=25.0339,121.5644`
  - `https://maps.app.goo.gl/xxxx` （短網址會自動 follow redirect）

## 管理位置
- **a** — 新增位置到 locations.yaml（預填目前座標，可貼 URL 自動填入）
- **r** — 重新讀取 locations.yaml

## 退出 Mock GPS
- **s** — **Exit mock**：停止推送、移除 test providers、關掉前景服務，系統完全回到真實 GPS。
  下次按方向鍵或 Enter 又會自動重新啟用，不用重開 app。

> 注意：`s` 不會取消「Mock GPS 被選為模擬位置 app」這個開發者選項設定。
> 若要完全解除，須手動到手機 設定 → 開發者選項 → 選擇模擬位置資訊應用程式。

## 其他
- **h / F1** — 這個說明視窗
- **q** — 離開儀表板（不影響手機端 app 狀態）

## 故障排除
- 若 walk 後手機定位沒變 → 檢查 Mock GPS app 是否在開發者選項被選為模擬位置 provider
- 若 Google Maps 位置跳動 → 關閉 設定 → 位置 → 位置服務 → Wi-Fi 掃描 / 藍牙掃描
- 若看到 `fail: ...` → ADB 連線或 app 服務異常，從終端機跑 `adb logcat | grep mockgps` 查看原因

按 Esc 或 ? 關閉此視窗。
"""


class HelpModal(ModalScreen[None]):
    DEFAULT_CSS = """
    HelpModal { align: center middle; }
    #help-box {
        background: $panel;
        border: tall $accent;
        padding: 1 2;
        width: 80%;
        height: 80%;
    }
    #help-hint { color: $text-muted; margin-top: 1; }
    """

    BINDINGS = [
        Binding("escape", "close", "close"),
        Binding("h", "close", "close"),
        Binding("f1", "close", "close"),
        Binding("q", "close", "close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-box"):
            yield Markdown(HELP_TEXT)
            yield Label("Esc / h / F1 / q 關閉", id="help-hint")

    def action_close(self) -> None:
        self.dismiss(None)


class SearchModal(ModalScreen[Optional[str]]):
    DEFAULT_CSS = """
    SearchModal { align: center middle; }
    #search-form {
        background: $panel;
        border: tall $accent;
        padding: 1 2;
        width: 60;
        height: auto;
    }
    #search-hint { color: $text-muted; margin-top: 1; }
    """

    BINDINGS = [
        Binding("escape", "cancel", "cancel"),
    ]

    def __init__(self, current: str = "") -> None:
        super().__init__()
        self.current = current

    def compose(self) -> ComposeResult:
        with Vertical(id="search-form"):
            yield Label("搜尋位置（名稱 / tags / timezone / note）")
            yield Input(id="q", value=self.current, placeholder="e.g. Taipei, outdoor, Asia/")
            yield Label("Enter 套用 · Esc 取消 · 清空後 Enter 可清除過濾", id="search-hint")

    def on_mount(self) -> None:
        inp = self.query_one("#q", Input)
        inp.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.input.value.strip())

    def action_cancel(self) -> None:
        self.dismiss(None)


class PasteTeleportModal(ModalScreen[Optional[Coord]]):
    """貼上座標或 Google Maps URL 立即傳送。"""

    DEFAULT_CSS = """
    PasteTeleportModal { align: center middle; }
    #paste-form {
        background: $panel;
        border: tall $accent;
        padding: 1 2;
        width: 70;
        height: auto;
    }
    #paste-form Label { margin-top: 1; }
    #paste-hint { color: $text-muted; margin-top: 1; }
    #paste-error { color: $error; margin-top: 1; }
    """

    BINDINGS = [
        Binding("escape", "cancel", "cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="paste-form"):
            yield Label("貼上座標 / Google Maps URL")
            yield Input(
                id="paste",
                placeholder='25.0339, 121.5644  或  https://maps.app.goo.gl/...',
            )
            yield Label(
                "Enter 解析並傳送 · Esc 取消",
                id="paste-hint",
            )
            yield Label("", id="paste-error")

    def on_mount(self) -> None:
        self.query_one("#paste", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "paste":
            return
        raw = event.input.value.strip()
        if not raw:
            self.dismiss(None)
            return

        coord = parse_location(raw)
        if coord is None:
            self.query_one("#paste-error", Label).update(
                "[red]無法解析。支援：lat,lng / Google Maps URL / 短網址[/red]"
            )
            self.app.bell()
            return

        self.dismiss(coord)

    def action_cancel(self) -> None:
        self.dismiss(None)


class AddLocationModal(ModalScreen[Optional[Location]]):
    DEFAULT_CSS = """
    AddLocationModal { align: center middle; }
    #form {
        background: $panel;
        border: tall $accent;
        padding: 1 2;
        width: 70;
        height: auto;
    }
    #form Label { margin-top: 1; }
    #form Input { margin-top: 0; }
    #hint { color: $text-muted; margin-top: 1; }
    #paste-status { color: $success; margin-top: 0; }
    """

    BINDINGS = [
        Binding("escape", "cancel", "cancel"),
        Binding("ctrl+s", "save", "save"),
    ]

    def __init__(self, default_lat: float, default_lng: float) -> None:
        super().__init__()
        self.default_lat = default_lat
        self.default_lng = default_lng

    def compose(self) -> ComposeResult:
        with Vertical(id="form"):
            yield Label("新增位置")
            yield Label("Paste URL / 座標（自動填入 Lat/Lng）:")
            yield Input(id="paste", placeholder="可留空")
            yield Label("", id="paste-status")
            yield Label("Name:")
            yield Input(id="name", placeholder="Home")
            yield Label("Lat:")
            yield Input(id="lat", value=f"{self.default_lat:.6f}")
            yield Label("Lng:")
            yield Input(id="lng", value=f"{self.default_lng:.6f}")
            yield Label("Tags (逗號分隔):")
            yield Input(id="tags", placeholder="Taipei,outdoor")
            yield Label("Timezone:")
            yield Input(id="tz", value="Asia/Taipei")
            yield Label("Note:")
            yield Input(id="note")
            yield Label("Enter 於最後欄位或 Ctrl+S 儲存 · Esc 取消", id="hint")

    def on_mount(self) -> None:
        self.query_one("#paste", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "paste":
            return
        raw = event.value.strip()
        status = self.query_one("#paste-status", Label)
        if not raw:
            status.update("")
            return
        coord = parse_location(raw)
        if coord is None:
            status.update("[dim]解析中或無法解析...[/dim]")
            return
        self.query_one("#lat", Input).value = f"{coord.lat:.6f}"
        self.query_one("#lng", Input).value = f"{coord.lng:.6f}"
        status.update(f"[green]✓ 已填入 {coord.lat:.6f}, {coord.lng:.6f}[/green]")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "note":
            self.action_save()
        elif event.input.id == "paste":
            self.query_one("#name", Input).focus()

    def action_save(self) -> None:
        name = self.query_one("#name", Input).value.strip()
        lat_s = self.query_one("#lat", Input).value.strip()
        lng_s = self.query_one("#lng", Input).value.strip()
        if not name or not lat_s or not lng_s:
            self.app.bell()
            return
        try:
            lat = float(lat_s)
            lng = float(lng_s)
        except ValueError:
            self.app.bell()
            return

        tags_s = self.query_one("#tags", Input).value.strip()
        tz_s = self.query_one("#tz", Input).value.strip() or None
        note_s = self.query_one("#note", Input).value.strip() or None
        tags = [t.strip() for t in tags_s.split(",") if t.strip()]

        self.dismiss(Location(name=name, lat=lat, lng=lng, tags=tags, timezone=tz_s, note=note_s))

    def action_cancel(self) -> None:
        self.dismiss(None)


class DashboardApp(App):
    CSS = """
    Screen { layout: vertical; }

    #top {
        height: auto;
        padding: 1 2;
        border: round $accent;
    }
    #coord {
        text-style: bold;
        color: $success;
    }
    #pad {
        padding: 0 2;
        color: $text-muted;
    }
    #locations {
        height: 1fr;
        padding: 0 2;
        border: round $accent;
    }
    #status { color: $warning; }
    """

    BINDINGS = [
        Binding("up", "walk('n')", "↑ N"),
        Binding("down", "walk('s')", "↓ S"),
        Binding("left", "walk('w')", "← W"),
        Binding("right", "walk('e')", "→ E"),
        Binding("k", "select_prev", "prev"),
        Binding("j", "select_next", "next"),
        Binding("enter", "teleport_selected", "teleport"),
        Binding("plus,equals_sign,equal", "step_up", "step+"),
        Binding("minus", "step_down", "step-"),
        Binding("a", "add_location", "add"),
        Binding("p", "paste_teleport", "paste"),
        Binding("slash", "search", "search"),
        Binding("c", "clear_filter", "clear"),
        Binding("s", "stop_mock", "exit mock"),
        Binding("r", "reload", "reload"),
        Binding("h", "help", "help"),
        Binding("f1", "help", "help"),
        Binding("q", "quit", "quit"),
    ]

    step_m: reactive[float] = reactive(5.0)
    last_action: reactive[str] = reactive("idle")

    def __init__(self, file: Path, serial: str) -> None:
        super().__init__()
        self.file = file
        self.serial = serial
        self.locations: dict[str, Location] = {}
        self._selected_idx: int = 0
        self._current_coord: Coord = Coord(0.0, 0.0)
        self._search_filter: str = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="top"):
            yield Static("", id="status")
            yield Static("", id="coord")
            yield Static("", id="pad")
        yield Static("", id="locations")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Mock GPS"
        self.sub_title = "Interactive TUI"
        self._load()
        if self.locations:
            first = next(iter(self.locations.values()))
            self._current_coord = first.coord
            self._selected_idx = 0
        self._render()

    def _load(self) -> None:
        self.locations = load_locations(self.file)
        if self._selected_idx >= len(self.locations):
            self._selected_idx = 0
        self._render_locations()

    def _render(self) -> None:
        self._render_top()
        self._render_locations()

    def _render_top(self) -> None:
        c = self._current_coord
        self.query_one("#coord", Static).update(
            f"Current: [bold green]{c.lat:.6f}, {c.lng:.6f}[/]"
        )
        self.query_one("#status", Static).update(
            f"Device: [cyan]{self.serial}[/]    "
            f"Step: [yellow]{self.step_m:g} m[/]    "
            f"Action: [magenta]{self.last_action}[/]"
        )
        self.query_one("#pad", Static).update(
            "        [bold]↑[/] (N)\n"
            "  [bold]←[/] (W) · [bold]→[/] (E)      arrows = walk  ·  j/k = select  ·  +/- = step\n"
            "        [bold]↓[/] (S)                Enter = teleport  ·  [bold]p[/] = paste URL/coord\n"
            "                                 [bold]/[/] = search  ·  c = clear  ·  a = add\n"
            "                                 [bold]s = exit mock[/] (回真實 GPS)  ·  r = reload\n"
            "                                 [bold]h / F1[/] = help  ·  q = quit"
        )

    def _filtered_items(self) -> list[tuple[str, Location]]:
        if not self._search_filter:
            return list(self.locations.items())
        q = self._search_filter.lower()
        result = []
        for name, loc in self.locations.items():
            haystack = " ".join([
                name.lower(),
                " ".join(loc.tags).lower(),
                (loc.note or "").lower(),
                (loc.timezone or "").lower(),
            ])
            if q in haystack:
                result.append((name, loc))
        return result

    def _clamp_selection(self, size: int) -> None:
        if size == 0:
            self._selected_idx = 0
        elif self._selected_idx >= size:
            self._selected_idx = size - 1
        elif self._selected_idx < 0:
            self._selected_idx = 0

    def _render_locations(self) -> None:
        items = self._filtered_items()
        self._clamp_selection(len(items))

        top_hint = "[dim]──── [bold]k ↑[/bold] (prev) ─────[/]"
        bot_hint = "[dim]──── [bold]j ↓[/bold] (next) ─────[/]"
        filter_line = (
            f"[magenta]filter: [/][bold]{self._search_filter}[/]  "
            f"[dim]({len(items)}/{len(self.locations)})  · c 清除 · / 修改[/]"
            if self._search_filter
            else ""
        )

        if not self.locations:
            body = "[dim](沒有位置，按 a 新增、按 p 貼上座標)[/]"
        elif not items:
            body = "[yellow](沒有符合的位置，按 c 清除過濾)[/]"
        else:
            rows: list[str] = []
            for i, (name, loc) in enumerate(items):
                marker = "[bold cyan]▶[/]" if i == self._selected_idx else " "
                tag_str = f" [dim][{', '.join(loc.tags)}][/]" if loc.tags else ""
                tz_str = f" [dim yellow]{loc.timezone}[/]" if loc.timezone else ""
                note_str = f" [dim]· {loc.note}[/]" if loc.note else ""
                rows.append(
                    f"{marker} [bold]{name}[/]  [dim]({loc.lat:.4f}, {loc.lng:.4f})[/]"
                    f"{tag_str}{tz_str}{note_str}"
                )
            body = "\n".join(rows)

        lines = [top_hint]
        if filter_line:
            lines.append(filter_line)
        lines.append(body)
        lines.append(bot_hint)
        self.query_one("#locations", Static).update("\n".join(lines))

    # Reactive watchers ------------------------------------------------------

    def watch_step_m(self) -> None:
        if self.is_mounted:
            self._render_top()

    def watch_last_action(self) -> None:
        if self.is_mounted:
            self._render_top()

    # Actions ----------------------------------------------------------------

    def action_walk(self, direction: str) -> None:
        if isinstance(self.focused, Input):
            return
        dx, dy = 0.0, 0.0
        if direction == "n": dy = self.step_m
        elif direction == "s": dy = -self.step_m
        elif direction == "e": dx = self.step_m
        elif direction == "w": dx = -self.step_m
        new_coord = offset_coord(self._current_coord, dx, dy)
        self._current_coord = new_coord
        ok, err = _adb_broadcast_teleport(new_coord, self.serial)
        self.last_action = (
            f"walk {direction.upper()} {self.step_m:g}m" if ok else f"fail: {err}"
        )
        self._render_top()

    def action_step_up(self) -> None:
        idx = _closest_index(STEP_SIZES, self.step_m)
        self.step_m = STEP_SIZES[min(idx + 1, len(STEP_SIZES) - 1)]

    def action_step_down(self) -> None:
        idx = _closest_index(STEP_SIZES, self.step_m)
        self.step_m = STEP_SIZES[max(idx - 1, 0)]

    def action_select_next(self) -> None:
        items = self._filtered_items()
        if not items:
            return
        self._selected_idx = (self._selected_idx + 1) % len(items)
        self._render_locations()

    def action_select_prev(self) -> None:
        items = self._filtered_items()
        if not items:
            return
        self._selected_idx = (self._selected_idx - 1) % len(items)
        self._render_locations()

    def action_teleport_selected(self) -> None:
        items = self._filtered_items()
        if not items:
            return
        name, loc = items[self._selected_idx]
        self._current_coord = loc.coord
        ok, err = _adb_broadcast_teleport(loc.coord, self.serial)
        self.last_action = f"teleport → {name}" if ok else f"fail: {err}"
        self._render_top()

    def action_search(self) -> None:
        modal = SearchModal(self._search_filter)

        def _applied(q: Optional[str]) -> None:
            if q is None:
                return
            self._search_filter = q
            self._selected_idx = 0
            self.last_action = f"filter: {q}" if q else "filter cleared"
            self._render_locations()
            self._render_top()

        self.push_screen(modal, _applied)

    def action_clear_filter(self) -> None:
        if not self._search_filter:
            return
        self._search_filter = ""
        self._selected_idx = 0
        self.last_action = "filter cleared"
        self._render_locations()
        self._render_top()

    def action_stop_mock(self) -> None:
        ok, err = _adb_broadcast_stop(self.serial)
        self.last_action = "exited mock (real GPS)" if ok else f"fail: {err}"
        self._render_top()

    def action_reload(self) -> None:
        self._load()
        self.last_action = "reloaded"
        self._render_top()

    def action_add_location(self) -> None:
        modal = AddLocationModal(self._current_coord.lat, self._current_coord.lng)

        def _saved(result: Optional[Location]) -> None:
            if result is None:
                return
            self.locations[result.name] = result
            save_locations(self.file, self.locations)
            self._load()
            self.last_action = f"added {result.name}"
            self._render_top()

        self.push_screen(modal, _saved)

    def action_help(self) -> None:
        self.push_screen(HelpModal())

    def action_paste_teleport(self) -> None:
        modal = PasteTeleportModal()

        def _pasted(coord: Optional[Coord]) -> None:
            if coord is None:
                return
            self._current_coord = coord
            ok, err = _adb_broadcast_teleport(coord, self.serial)
            self.last_action = (
                f"paste → {coord.lat:.5f}, {coord.lng:.5f}" if ok else f"fail: {err}"
            )
            self._render_top()

        self.push_screen(modal, _pasted)


def run_dashboard(file: Path, serial: str) -> None:
    DashboardApp(file=file, serial=serial).run()
