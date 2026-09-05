#!/usr/bin/env python3
"""
NetShare Pro - Modern WiFi Hotspot Manager (v2 - Redesigned UI)
Backend: create_ap systemd service & CLI

What changed in this redesign:
- Sidebar-based navigation (Panel / Cihazlar / Ağ Ayarları / Gelişmiş / QR Kod)
  instead of a top tab switcher, for a more "app-like" advanced feel.
- New "Panel" (Dashboard) page: one glance shows status, quick stats
  (device count / band / channel), a mini device preview and the single
  start/stop action - no need to hunt through tabs for the basics.
- Live-searchable device list (Gtk.ListBox + filter function).
- Floating toast notifications (bottom-center, auto-dismiss) replace the
  old headerbar-subtitle notification trick - clearer and less noisy.
- Softer, more spacious visual language: bigger radii, subtle shadows,
  a calmer accent color, consistent spacing scale.
- All backend logic (create_ap control, config I/O, client parsing, tray
  icons, QR generation) is unchanged from the original implementation.
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')

from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf
from gi.repository import AyatanaAppIndicator3 as AppIndicator3

import subprocess
import threading
import time
import os
import signal
import sys

# ─── Constants ────────────────────────────────────────────────────────
APP_ID = "com.netshare.hotspot"
APP_NAME = "NetShare Pro"
CONFIG_FILE = "/etc/create_ap.conf"
ICON_DIR = os.path.dirname(os.path.abspath(__file__))

NAV_PAGES = [
    ("dashboard", "Panel"),
    ("devices", "Cihazlar"),
    ("network", "Ağ Ayarları"),
    ("advanced", "Gelişmiş"),
    ("qrcode", "QR Kod"),
]

# ─── Stylesheet ─────────────────────────────────────────────────────────
CSS = """
@define-color bg_primary #0B0C10;
@define-color bg_sidebar #101117;
@define-color bg_card #15161D;
@define-color bg_card_alt #1B1D26;
@define-color bg_input #0F1016;
@define-color accent #3B82F6;
@define-color accent_soft rgba(59,130,246,0.16);
@define-color border_subtle rgba(255,255,255,0.07);
@define-color text_dim #8B90A0;

* {
    outline: none;
}

window.background {
    background-color: @bg_primary;
}

headerbar {
    background-color: @bg_primary;
    border-bottom: 1px solid @border_subtle;
    box-shadow: none;
    min-height: 46px;
    padding: 0 6px 0 0;
}
headerbar .title {
    color: #FFFFFF;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.2px;
}

/* ── Status pill in headerbar ─────────────────────────── */
.hdr-pill {
    border-radius: 20px;
    padding: 4px 12px 4px 10px;
    font-size: 11px;
    font-weight: 700;
}
.hdr-pill-active {
    background-color: rgba(16,185,129,0.16);
    color: #34D399;
}
.hdr-pill-inactive {
    background-color: rgba(255,255,255,0.06);
    color: @text_dim;
}

/* ── Sidebar ───────────────────────────────────────────── */
.sidebar {
    background-color: @bg_sidebar;
    border-right: 1px solid @border_subtle;
}
.brand-title {
    color: #FFFFFF;
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0.2px;
}
.brand-subtitle {
    color: @text_dim;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.4px;
}

.nav-list {
    background-color: transparent;
}
.nav-list row {
    padding: 0;
    margin: 1px 10px;
    border-radius: 9px;
    background-color: transparent;
}
.nav-list row:hover {
    background-color: rgba(255,255,255,0.045);
}
.nav-list row:selected {
    background-color: @accent_soft;
}
.nav-row-label {
    color: @text_dim;
    font-size: 13px;
    font-weight: 600;
    padding: 10px 14px;
}
.nav-list row:selected .nav-row-label {
    color: #DCEBFF;
}
.nav-list row:hover .nav-row-label {
    color: #E5E7EB;
}

.sidebar-footer-btn {
    background-color: transparent;
    color: @text_dim;
    border: 1px solid @border_subtle;
    border-radius: 9px;
    padding: 8px 10px;
    font-size: 11px;
    font-weight: 700;
}
.sidebar-footer-btn:hover {
    background-color: rgba(255,255,255,0.05);
    color: #F3F4F6;
}

/* ── Cards ─────────────────────────────────────────────── */
.card {
    background-color: @bg_card;
    border-radius: 14px;
    border: 1px solid @border_subtle;
    padding: 16px 18px;
}
.card-title {
    color: @text_dim;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.1px;
}
.card-hint {
    color: @text_dim;
    font-size: 12px;
}
.page-title {
    color: #FFFFFF;
    font-size: 19px;
    font-weight: 800;
}
.page-subtitle {
    color: @text_dim;
    font-size: 12.5px;
}

/* ── Dashboard hero ────────────────────────────────────── */
.status-hero {
    padding: 22px 22px;
    border-radius: 16px;
    border: 1px solid @border_subtle;
    transition: all 200ms ease;
}
.status-active {
    background-image: linear-gradient(135deg, #064E3B, #0B3B2E);
    border-color: rgba(16,185,129,0.5);
}
.status-inactive {
    background-color: @bg_card_alt;
    border-color: @border_subtle;
}
.status-loading {
    background-color: #3A2E0A;
    border-color: rgba(245,158,11,0.5);
}

.status-title-active, .status-title-inactive {
    color: #FFFFFF;
    font-size: 21px;
    font-weight: 800;
}
.status-sub-active {
    color: #A7F3D0;
    font-size: 13px;
    font-weight: 600;
}
.status-sub-inactive {
    color: @text_dim;
    font-size: 13px;
}
.status-sub-loading {
    color: #FDE68A;
    font-size: 13px;
    font-weight: 600;
}

/* Pulsing state dot */
.dot {
    border-radius: 50%;
    min-width: 9px;
    min-height: 9px;
}
.dot-active {
    background-color: #10B981;
    box-shadow: 0 0 8px #10B981;
}
.dot-inactive {
    background-color: #4B5563;
}
.dot-loading {
    background-color: #F59E0B;
    box-shadow: 0 0 8px #F59E0B;
}

/* ── Stat chips (quick glance numbers) ───────────────────── */
.stat-chip {
    background-color: @bg_card;
    border: 1px solid @border_subtle;
    border-radius: 12px;
    padding: 12px 14px;
}
.stat-value {
    color: #FFFFFF;
    font-size: 18px;
    font-weight: 800;
}
.stat-label {
    color: @text_dim;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.6px;
}

/* ── Buttons ───────────────────────────────────────────── */
.btn-primary {
    background-color: @accent;
    color: #FFFFFF;
    border: none;
    border-radius: 11px;
    padding: 13px 24px;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 0.3px;
    box-shadow: none;
    transition: all 150ms ease;
}
.btn-primary:hover { background-color: #5B9BFA; }
.btn-primary:disabled { opacity: 0.5; }

.btn-danger {
    background-color: #DC2626;
    color: #FFFFFF;
    border: none;
    border-radius: 11px;
    padding: 13px 24px;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 0.3px;
    transition: all 150ms ease;
}
.btn-danger:hover { background-color: #EF4444; }
.btn-danger:disabled { opacity: 0.5; }

.btn-secondary {
    background-color: rgba(255,255,255,0.06);
    color: #F3F4F6;
    border: 1px solid @border_subtle;
    border-radius: 9px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 700;
    transition: all 150ms ease;
}
.btn-secondary:hover {
    background-color: rgba(255,255,255,0.12);
    border-color: rgba(255,255,255,0.2);
}

/* ── Form inputs ───────────────────────────────────────── */
.modern-entry {
    background-color: @bg_input;
    color: #F3F4F6;
    border: 1px solid @border_subtle;
    border-radius: 9px;
    padding: 9px 12px;
    font-size: 13px;
    caret-color: @accent;
    min-height: 20px;
}
.modern-entry:focus {
    border-color: @accent;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.22);
}
.modern-entry:disabled { opacity: 0.4; }

.search-entry {
    background-color: @bg_input;
    color: #F3F4F6;
    border: 1px solid @border_subtle;
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 13px;
}
.search-entry:focus {
    border-color: @accent;
}

.field-label {
    color: @text_dim;
    font-size: 12px;
    font-weight: 600;
}

.modern-combo {
    background-color: @bg_input;
    color: #F3F4F6;
    border: 1px solid @border_subtle;
    border-radius: 9px;
    padding: 5px 10px;
    font-size: 13px;
    min-height: 20px;
}
.modern-combo * { color: #F3F4F6; }

.switch-row {
    background-color: @bg_input;
    border-radius: 10px;
    padding: 10px 12px;
}

/* ── Devices list ──────────────────────────────────────── */
.device-row {
    background-color: @bg_card_alt;
    border: 1px solid @border_subtle;
    border-radius: 11px;
    padding: 11px 14px;
}
.device-row:hover {
    border-color: rgba(59,130,246,0.35);
}
.device-hostname-btn {
    background: transparent;
    border: none;
    color: #F3F4F6;
    font-size: 13.5px;
    font-weight: 700;
    padding: 0;
}
.device-hostname-btn:hover { color: #7DB2FF; }

.copy-pill {
    background-color: @bg_input;
    color: @text_dim;
    border: 1px solid @border_subtle;
    border-radius: 6px;
    padding: 3px 9px;
    font-size: 10.5px;
    font-family: monospace;
    transition: all 150ms ease;
}
.copy-pill:hover {
    background-color: rgba(59,130,246,0.15);
    color: #7DB2FF;
    border-color: rgba(59,130,246,0.4);
}

.badge {
    background-color: @accent_soft;
    color: #7DB2FF;
    border-radius: 20px;
    padding: 3px 11px;
    font-size: 11px;
    font-weight: 700;
}

.loading-bar {
    min-height: 4px;
    border-radius: 2px;
    background-color: rgba(255,255,255,0.06);
}
.loading-bar progress {
    border-radius: 2px;
    background-color: @accent;
    min-height: 4px;
}

/* ── Toast notification ───────────────────────────────── */
.toast {
    background-color: #1F2230;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 12px;
    padding: 10px 18px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.45);
}
.toast-label {
    color: #F3F4F6;
    font-size: 12.5px;
    font-weight: 700;
}
.toast-error {
    background-color: #3A1518;
    border-color: rgba(239,68,68,0.4);
}
.toast-error .toast-label { color: #FCA5A5; }

scrollbar slider {
    background-color: rgba(255,255,255,0.14);
    border-radius: 8px;
    min-width: 6px;
    min-height: 6px;
}
scrollbar slider:hover { background-color: rgba(255,255,255,0.25); }
"""


# ─── Helper Functions (backend - unchanged from original) ─────────────

def run_cmd(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout.strip()
    except Exception as e:
        return False, str(e)


def copy_to_clipboard(text):
    try:
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()
        return True
    except Exception as e:
        print("Clipboard error:", e)
        return False


def read_config():
    cfg = {}
    try:
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    cfg[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return cfg


def save_config(cfg_dict):
    lines = [f"{k}={v}" for k, v in cfg_dict.items()]
    content = "\n".join(lines) + "\n"
    try:
        p = subprocess.Popen(["sudo", "-n", "tee", CONFIG_FILE],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        p.communicate(input=content, timeout=5)
        return p.returncode == 0
    except Exception as e:
        print("save_config error:", e)
        return False


def get_wifi_interfaces():
    ok, out = run_cmd("iw dev | awk '$1==\"Interface\"{if ($2 !~ /^ap/ && $2 !~ /^p2p/) print $2}'")
    if ok and out:
        return [i.strip() for i in out.split('\n') if i.strip()]
    return []


def get_all_interfaces():
    ok, out = run_cmd("ls /sys/class/net")
    if ok and out:
        return [i.strip() for i in out.split() if i.strip()]
    return []


def is_hotspot_running():
    ok, out = run_cmd("sudo -n /usr/bin/create_ap --list-running")
    if ok and out:
        parts = out.split()
        if len(parts) >= 2:
            return True, parts[0], parts[1]
    return False, None, None


def get_connected_clients():
    running, pid, _ = is_hotspot_running()
    if not running or not pid:
        return []
    ok, out = run_cmd(f"sudo -n /usr/bin/create_ap --list-clients {pid}")
    clients = []
    if ok and out:
        lines = out.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith("MAC") or "No clients" in line:
                continue
            parts = line.split()
            if len(parts) >= 1 and ':' in parts[0]:
                mac = parts[0]
                ip = parts[1] if len(parts) > 1 and parts[1] != "*" else "—"
                hostname = parts[2] if len(parts) > 2 and parts[2] != "*" else "Bilinmeyen Cihaz"
                clients.append({'mac': mac, 'ip': ip, 'hostname': hostname})
    return clients


# ─── Tray Icons ─────────────────────────────────────────────────────────

TRAY_ICON_ACTIVE_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="22" height="22" viewBox="0 0 22 22" xmlns="http://www.w3.org/2000/svg">
  <rect width="22" height="22" rx="5" fill="#101117"/>
  <circle cx="11" cy="14.5" r="1.5" fill="#10B981"/>
  <path d="M7.5 11.5a5 5 0 0 1 7 0" stroke="#10B981" stroke-width="1.6" stroke-linecap="round" fill="none"/>
  <path d="M5 9a8.5 8.5 0 0 1 12 0" stroke="#10B981" stroke-width="1.6" stroke-linecap="round" fill="none" opacity="0.65"/>
</svg>"""

TRAY_ICON_INACTIVE_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="22" height="22" viewBox="0 0 22 22" xmlns="http://www.w3.org/2000/svg">
  <rect width="22" height="22" rx="5" fill="#101117"/>
  <circle cx="11" cy="14.5" r="1.5" fill="#EF4444"/>
  <path d="M7.5 11.5a5 5 0 0 1 7 0" stroke="#EF4444" stroke-width="1.6" stroke-linecap="round" fill="none" opacity="0.6"/>
  <line x1="5" y1="5" x2="17" y2="17" stroke="#EF4444" stroke-width="1.6" stroke-linecap="round"/>
</svg>"""


def write_tray_icons():
    icon_path = os.path.join(ICON_DIR, "netshare-tray-red.svg")
    icon_active_path = os.path.join(ICON_DIR, "netshare-tray-green.svg")
    with open(icon_path, 'w') as f:
        f.write(TRAY_ICON_INACTIVE_SVG)
    with open(icon_active_path, 'w') as f:
        f.write(TRAY_ICON_ACTIVE_SVG)
    return icon_path, icon_active_path


def make_dot(size=9):
    """Small colored status dot widget."""
    dot = Gtk.DrawingArea()
    dot.set_size_request(size, size)
    dot.get_style_context().add_class("dot")
    dot.get_style_context().add_class("dot-inactive")
    return dot


# ─── Main Application ────────────────────────────────────────────────

class NetShareApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None
        self.indicator = None
        self.is_running = False
        self.hotspot_pid = None
        self.poll_timer_id = None
        self._pulse_active = False
        self._toast_timer_id = None
        self.all_clients = []

    def do_activate(self):
        if self.window:
            self.window.present()
            return

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self._build_window()
        self._build_tray()
        self._load_initial_config()
        self._check_status()

        self.hold()

    # ──────────────────────────────────────────────────────────────────
    # Window shell: headerbar + overlay(sidebar + stack, toast)
    # ──────────────────────────────────────────────────────────────────

    def _build_window(self):
        self.window = Gtk.ApplicationWindow(application=self, title=APP_NAME)
        self.window.set_default_size(860, 640)
        self.window.set_size_request(760, 560)
        self.window.connect("delete-event", self._on_close)
        self.window.connect("window-state-event", self._on_window_state)

        # HeaderBar: title + live status pill
        self.hb = Gtk.HeaderBar()
        self.hb.set_show_close_button(True)
        self.hb.set_title(APP_NAME)
        self.window.set_titlebar(self.hb)

        self.hdr_pill = Gtk.Label(label="● Kapalı")
        self.hdr_pill.get_style_context().add_class("hdr-pill")
        self.hdr_pill.get_style_context().add_class("hdr-pill-inactive")
        self.hb.pack_end(self.hdr_pill)

        # Overlay lets us float a toast over the whole window
        self.overlay = Gtk.Overlay()

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        sidebar = self._build_sidebar()
        stack_wrapper = self._build_stack()
        root.pack_start(sidebar, False, False, 0)
        root.pack_start(stack_wrapper, True, True, 0)

        self.overlay.add(root)
        self.overlay.add_overlay(self._build_toast())

        self.window.add(self.overlay)
        self.window.show_all()
        self.toast_revealer.set_reveal_child(False)

        # Select first nav row after stack is initialized
        self.nav_list.select_row(self.nav_list.get_row_at_index(0))

    def _build_sidebar(self):
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar.get_style_context().add_class("sidebar")
        sidebar.set_size_request(200, -1)

        brand = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        brand.set_margin_start(20)
        brand.set_margin_end(16)
        brand.set_margin_top(22)
        brand.set_margin_bottom(18)
        title = Gtk.Label(label=APP_NAME, xalign=0)
        title.get_style_context().add_class("brand-title")
        subtitle = Gtk.Label(label="WIFI HOTSPOT", xalign=0)
        subtitle.get_style_context().add_class("brand-subtitle")
        brand.pack_start(title, False, False, 0)
        brand.pack_start(subtitle, False, False, 0)
        sidebar.pack_start(brand, False, False, 0)

        self.nav_list = Gtk.ListBox()
        self.nav_list.get_style_context().add_class("nav-list")
        self.nav_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        for key, label_text in NAV_PAGES:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=label_text, xalign=0)
            lbl.get_style_context().add_class("nav-row-label")
            row.add(lbl)
            row.nav_key = key
            self.nav_list.add(row)
        self.nav_list.connect("row-selected", self._on_nav_selected)
        sidebar.pack_start(self.nav_list, False, False, 6)

        spacer = Gtk.Box()
        sidebar.pack_start(spacer, True, True, 0)

        footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        footer.set_margin_start(14)
        footer.set_margin_end(14)
        footer.set_margin_bottom(16)

        self.sidebar_dot = make_dot(8)
        dot_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        dot_row.set_halign(Gtk.Align.START)
        dot_wrap = Gtk.Box()
        dot_wrap.set_valign(Gtk.Align.CENTER)
        dot_wrap.pack_start(self.sidebar_dot, False, False, 0)
        dot_row.pack_start(dot_wrap, False, False, 0)
        self.sidebar_status_lbl = Gtk.Label(label="Hotspot kapalı", xalign=0)
        self.sidebar_status_lbl.get_style_context().add_class("card-hint")
        dot_row.pack_start(self.sidebar_status_lbl, False, False, 0)
        footer.pack_start(dot_row, False, False, 0)

        btn_tray = Gtk.Button(label="Simge Durumuna Küçült")
        btn_tray.get_style_context().add_class("sidebar-footer-btn")
        btn_tray.connect("clicked", lambda b: self._hide_to_tray())
        footer.pack_start(btn_tray, False, False, 0)

        sidebar.pack_start(footer, False, False, 0)
        return sidebar

    def _build_toast(self):
        self.toast_label = Gtk.Label(label="")
        self.toast_label.get_style_context().add_class("toast-label")

        toast_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        toast_box.get_style_context().add_class("toast")
        self.toast_box_ctx = toast_box.get_style_context()
        toast_box.pack_start(self.toast_label, False, False, 0)

        self.toast_revealer = Gtk.Revealer()
        self.toast_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.toast_revealer.set_transition_duration(180)
        self.toast_revealer.set_halign(Gtk.Align.CENTER)
        self.toast_revealer.set_valign(Gtk.Align.END)
        self.toast_revealer.set_margin_bottom(22)
        self.toast_revealer.add(toast_box)
        return self.toast_revealer

    def _show_toast(self, msg, is_error=False, duration_ms=2600):
        self.toast_label.set_text(msg)
        self.toast_box_ctx.remove_class("toast-error")
        if is_error:
            self.toast_box_ctx.add_class("toast-error")

        if self._toast_timer_id:
            GLib.source_remove(self._toast_timer_id)
            self._toast_timer_id = None

        self.toast_revealer.set_reveal_child(True)

        def _hide():
            self.toast_revealer.set_reveal_child(False)
            self._toast_timer_id = None
            return False
        self._toast_timer_id = GLib.timeout_add(duration_ms, _hide)

    def _on_nav_selected(self, listbox, row):
        if row is None or not hasattr(self, 'content_stack'):
            return
            return
        self.content_stack.set_visible_child_name(row.nav_key)
        self.page_title_lbl.set_text(dict(NAV_PAGES)[row.nav_key])
        subtitles = {
            "dashboard": "Hotspot durumunu tek bakışta görün ve yönetin",
            "devices": "Ağınıza bağlı tüm cihazları görüntüleyin",
            "network": "Ağ adı, şifre ve arayüz tercihlerinizi düzenleyin",
            "advanced": "Frekans, kanal ve gelişmiş kablosuz seçenekleri",
            "qrcode": "Şifre yazmadan tek taramayla bağlanın",
        }
        self.page_subtitle_lbl.set_text(subtitles.get(row.nav_key, ""))

    def go_to_page(self, key):
        for row in self.nav_list.get_children():
            if row.nav_key == key:
                self.nav_list.select_row(row)
                break

    # ──────────────────────────────────────────────────────────────────
    # Content stack (right-hand side pages)
    # ──────────────────────────────────────────────────────────────────

    def _build_stack(self):
        wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        page_header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        page_header.set_margin_start(24)
        page_header.set_margin_end(24)
        page_header.set_margin_top(20)
        page_header.set_margin_bottom(10)
        self.page_title_lbl = Gtk.Label(label="Panel", xalign=0)
        self.page_title_lbl.get_style_context().add_class("page-title")
        self.page_subtitle_lbl = Gtk.Label(label="Hotspot durumunu tek bakışta görün ve yönetin", xalign=0)
        self.page_subtitle_lbl.get_style_context().add_class("page-subtitle")
        page_header.pack_start(self.page_title_lbl, False, False, 0)
        page_header.pack_start(self.page_subtitle_lbl, False, False, 0)
        wrapper.pack_start(page_header, False, False, 0)

        self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.content_stack.set_transition_duration(140)
        self.content_stack.set_hexpand(True)
        self.content_stack.set_vexpand(True)

        self.content_stack.add_named(self._build_dashboard_page(), "dashboard")
        self.content_stack.add_named(self._build_devices_page(), "devices")
        self.content_stack.add_named(self._build_network_page(), "network")
        self.content_stack.add_named(self._build_advanced_page(), "advanced")
        self.content_stack.add_named(self._build_qr_page(), "qrcode")

        wrapper.pack_start(self.content_stack, True, True, 0)
        return wrapper

    # ── Dashboard ──────────────────────────────────────────────────────

    def _build_dashboard_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_bottom(24)

        # Hero status card
        self.status_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.status_card.get_style_context().add_class("status-hero")
        self.status_card.get_style_context().add_class("status-inactive")

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        dot_wrap = Gtk.Box()
        dot_wrap.set_valign(Gtk.Align.CENTER)
        self.hero_dot = make_dot(10)
        dot_wrap.pack_start(self.hero_dot, False, False, 0)
        top_row.pack_start(dot_wrap, False, False, 0)

        self.status_title = Gtk.Label(label="Hotspot Kapalı", xalign=0)
        self.status_title.get_style_context().add_class("status-title-inactive")
        top_row.pack_start(self.status_title, False, False, 0)
        self.status_card.pack_start(top_row, False, False, 0)

        self.status_sub = Gtk.Label(label="Başlatmak için aşağıdaki butona tıklayın", xalign=0)
        self.status_sub.get_style_context().add_class("status-sub-inactive")
        self.status_card.pack_start(self.status_sub, False, False, 0)

        self.progress = Gtk.ProgressBar()
        self.progress.get_style_context().add_class("loading-bar")
        self.progress.set_no_show_all(True)
        self.progress.set_visible(False)
        self.status_card.pack_start(self.progress, False, False, 4)

        self.btn_action = Gtk.Button(label="Hotspot Başlat")
        self.btn_action.get_style_context().add_class("btn-primary")
        self.btn_action.connect("clicked", self._on_toggle_hotspot)
        self.btn_action.set_margin_top(6)
        self.status_card.pack_start(self.btn_action, False, False, 0)

        page.pack_start(self.status_card, False, False, 0)

        # Quick stat chips
        stats_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        stats_row.set_homogeneous(True)

        self.stat_devices_val = Gtk.Label(label="0", xalign=0)
        stats_row.pack_start(self._make_stat_chip(self.stat_devices_val, "BAĞLI CİHAZ"), True, True, 0)

        self.stat_band_val = Gtk.Label(label="Otomatik", xalign=0)
        stats_row.pack_start(self._make_stat_chip(self.stat_band_val, "FREKANS BANDI"), True, True, 0)

        self.stat_ssid_val = Gtk.Label(label="—", xalign=0)
        stats_row.pack_start(self._make_stat_chip(self.stat_ssid_val, "AĞ ADI"), True, True, 0)

        page.pack_start(stats_row, False, False, 0)

        # Mini device preview
        preview_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        preview_card.get_style_context().add_class("card")
        preview_card.set_vexpand(True)

        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        head_title = Gtk.Label(label="SON BAĞLANANLAR", xalign=0)
        head_title.get_style_context().add_class("card-title")
        head.pack_start(head_title, True, True, 0)
        btn_see_all = Gtk.Button(label="Tümünü Gör")
        btn_see_all.get_style_context().add_class("btn-secondary")
        btn_see_all.connect("clicked", lambda b: self.go_to_page("devices"))
        head.pack_start(btn_see_all, False, False, 0)
        preview_card.pack_start(head, False, False, 0)

        self.preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.preview_empty_lbl = Gtk.Label(
            label="Henüz bağlı cihaz bulunmuyor.\nHotspot aktifleştiğinde bağlanan cihazlar burada gösterilecektir.")
        self.preview_empty_lbl.get_style_context().add_class("status-sub-inactive")
        self.preview_empty_lbl.set_justify(Gtk.Justification.CENTER)
        self.preview_box.pack_start(self.preview_empty_lbl, True, True, 24)
        preview_card.pack_start(self.preview_box, True, True, 0)

        page.pack_start(preview_card, True, True, 0)
        return page

    def _make_stat_chip(self, value_label, caption_text):
        chip = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        chip.get_style_context().add_class("stat-chip")
        value_label.get_style_context().add_class("stat-value")
        chip.pack_start(value_label, False, False, 0)
        caption = Gtk.Label(label=caption_text, xalign=0)
        caption.get_style_context().add_class("stat-label")
        chip.pack_start(caption, False, False, 0)
        return chip

    # ── Devices ────────────────────────────────────────────────────────

    def _build_devices_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_bottom(24)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self.device_search = Gtk.SearchEntry()
        self.device_search.get_style_context().add_class("search-entry")
        self.device_search.set_placeholder_text("Cihaz adı, IP veya MAC ile ara…")
        self.device_search.set_hexpand(True)
        self.device_search.connect("search-changed", lambda e: self.devices_listbox.invalidate_filter())
        toolbar.pack_start(self.device_search, True, True, 0)

        self.dev_badge = Gtk.Label(label="0 Cihaz")
        self.dev_badge.get_style_context().add_class("badge")
        toolbar.pack_start(self.dev_badge, False, False, 0)

        btn_refresh = Gtk.Button(label="Yenile")
        btn_refresh.get_style_context().add_class("btn-secondary")
        btn_refresh.connect("clicked", lambda b: self._refresh_clients())
        toolbar.pack_start(btn_refresh, False, False, 0)

        page.pack_start(toolbar, False, False, 0)

        dev_scroll = Gtk.ScrolledWindow()
        dev_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        dev_scroll.set_vexpand(True)

        self.devices_listbox = Gtk.ListBox()
        self.devices_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.devices_listbox.set_filter_func(self._device_filter_func)

        self.no_devices_lbl = Gtk.Label(
            label="Henüz bağlı cihaz bulunmuyor.\nHotspot aktifleştiğinde bağlanan cihazlar burada gösterilecektir.")
        self.no_devices_lbl.get_style_context().add_class("status-sub-inactive")
        self.no_devices_lbl.set_justify(Gtk.Justification.CENTER)
        self.no_devices_lbl.set_margin_top(40)

        dev_scroll.add(self.devices_listbox)

        self.devices_page_stack = Gtk.Stack()
        self.devices_page_stack.add_named(self.no_devices_lbl, "empty")
        self.devices_page_stack.add_named(dev_scroll, "list")
        self.devices_page_stack.set_visible_child_name("empty")
        page.pack_start(self.devices_page_stack, True, True, 0)

        return page

    def _device_filter_func(self, row):
        query = self.device_search.get_text().strip().lower()
        if not query:
            return True
        return query in row.search_key

    def _make_device_row_widget(self, item, compact=False):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.get_style_context().add_class("device-row")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        btn_host = Gtk.Button(label=item['hostname'])
        btn_host.get_style_context().add_class("device-hostname-btn")
        btn_host.set_tooltip_text("Cihaz adını kopyalamak için tıklayın")
        btn_host.connect("clicked", lambda b, val=item['hostname']: self._copy_field("Cihaz Adı", val))
        vbox.pack_start(btn_host, False, False, 0)

        if not compact:
            pills_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

            btn_ip = Gtk.Button(label=f"IP: {item['ip']}")
            btn_ip.get_style_context().add_class("copy-pill")
            btn_ip.set_tooltip_text("IP adresini kopyala")
            btn_ip.connect("clicked", lambda b, val=item['ip']: self._copy_field("IP Adresi", val))
            pills_box.pack_start(btn_ip, False, False, 0)

            btn_mac = Gtk.Button(label=f"MAC: {item['mac']}")
            btn_mac.get_style_context().add_class("copy-pill")
            btn_mac.set_tooltip_text("MAC adresini kopyala")
            btn_mac.connect("clicked", lambda b, val=item['mac']: self._copy_field("MAC Adresi", val))
            pills_box.pack_start(btn_mac, False, False, 0)

            vbox.pack_start(pills_box, False, False, 0)

        row.pack_start(vbox, True, True, 0)

        dot = make_dot(8)
        dot.get_style_context().remove_class("dot-inactive")
        dot.get_style_context().add_class("dot-active")
        dot_box = Gtk.Box()
        dot_box.set_valign(Gtk.Align.CENTER)
        dot_box.pack_start(dot, False, False, 0)
        row.pack_start(dot_box, False, False, 0)

        return row

    # ── Network settings ────────────────────────────────────────────────

    def _build_network_page(self):
        outer_scroll = Gtk.ScrolledWindow()
        outer_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_bottom(24)

        # Credentials card
        cred_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        cred_card.get_style_context().add_class("card")

        ctitle = Gtk.Label(label="AĞ KİMLİK BİLGİLERİ", xalign=0)
        ctitle.get_style_context().add_class("card-title")
        cred_card.pack_start(ctitle, False, False, 0)

        lbl_ssid = Gtk.Label(label="Ağ Adı (SSID)", xalign=0)
        lbl_ssid.get_style_context().add_class("field-label")
        cred_card.pack_start(lbl_ssid, False, False, 0)
        self.entry_ssid = Gtk.Entry()
        self.entry_ssid.get_style_context().add_class("modern-entry")
        self.entry_ssid.connect("changed", lambda e: self._update_qr_code())
        cred_card.pack_start(self.entry_ssid, False, False, 0)

        open_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        open_box.get_style_context().add_class("switch-row")
        lbl_open = Gtk.Label(label="Açık Ağ (Şifresiz Hotspot)", xalign=0)
        lbl_open.get_style_context().add_class("field-label")
        open_box.pack_start(lbl_open, True, True, 0)
        self.sw_open = Gtk.Switch()
        self.sw_open.connect("notify::active", self._on_toggle_open_network)
        open_box.pack_start(self.sw_open, False, False, 0)
        cred_card.pack_start(open_box, False, False, 0)

        lbl_pass = Gtk.Label(label="Şifre (WPA2 Passphrase)", xalign=0)
        lbl_pass.get_style_context().add_class("field-label")
        cred_card.pack_start(lbl_pass, False, False, 0)

        self.entry_pass = Gtk.Entry()
        self.entry_pass.get_style_context().add_class("modern-entry")
        self.entry_pass.set_visibility(False)
        self.entry_pass.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "view-reveal-symbolic")
        self.entry_pass.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, "Şifreyi Göster / Gizle")
        self.entry_pass.connect("icon-press", self._on_pass_icon_press)
        self.entry_pass.connect("changed", lambda e: self._update_qr_code())
        cred_card.pack_start(self.entry_pass, False, False, 0)

        btn_qr_jump = Gtk.Button(label="QR Kod ile Paylaş")
        btn_qr_jump.get_style_context().add_class("btn-secondary")
        btn_qr_jump.set_halign(Gtk.Align.START)
        btn_qr_jump.connect("clicked", lambda b: self.go_to_page("qrcode"))
        cred_card.pack_start(btn_qr_jump, False, False, 2)

        page.pack_start(cred_card, False, False, 0)

        # Interfaces card
        iface_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        iface_card.get_style_context().add_class("card")

        ititle = Gtk.Label(label="ARAYÜZ SEÇİMİ", xalign=0)
        ititle.get_style_context().add_class("card-title")
        iface_card.pack_start(ititle, False, False, 0)

        lbl_wifi = Gtk.Label(label="WiFi Arayüzü (Hotspot Yayını Yapacak)", xalign=0)
        lbl_wifi.get_style_context().add_class("field-label")
        iface_card.pack_start(lbl_wifi, False, False, 0)
        self.combo_wifi = Gtk.ComboBoxText()
        self.combo_wifi.get_style_context().add_class("modern-combo")
        iface_card.pack_start(self.combo_wifi, False, False, 0)

        lbl_inet = Gtk.Label(label="İnternet Kaynağı (Paylaşılacak Bağlantı)", xalign=0)
        lbl_inet.get_style_context().add_class("field-label")
        iface_card.pack_start(lbl_inet, False, False, 0)
        self.combo_inet = Gtk.ComboBoxText()
        self.combo_inet.get_style_context().add_class("modern-combo")
        iface_card.pack_start(self.combo_inet, False, False, 0)

        page.pack_start(iface_card, False, False, 0)

        outer_scroll.add(page)
        return outer_scroll

    # ── Advanced settings ───────────────────────────────────────────────

    def _build_advanced_page(self):
        outer_scroll = Gtk.ScrolledWindow()
        outer_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_bottom(24)

        # Frequency & channel
        freq_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        freq_card.get_style_context().add_class("card")

        ftitle = Gtk.Label(label="FREKANS VE KANAL", xalign=0)
        ftitle.get_style_context().add_class("card-title")
        freq_card.pack_start(ftitle, False, False, 0)

        freq_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        fcol = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl_freq = Gtk.Label(label="Frekans Bandı", xalign=0)
        lbl_freq.get_style_context().add_class("field-label")
        fcol.pack_start(lbl_freq, False, False, 0)
        self.combo_freq = Gtk.ComboBoxText()
        self.combo_freq.get_style_context().add_class("modern-combo")
        self.combo_freq.append_text("Otomatik (Auto)")
        self.combo_freq.append_text("2.4 GHz")
        self.combo_freq.append_text("5 GHz")
        self.combo_freq.set_active(0)
        self.combo_freq.connect("changed", lambda c: self._update_band_stat())
        fcol.pack_start(self.combo_freq, False, True, 0)
        freq_row.pack_start(fcol, True, True, 0)

        ccol = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl_chan = Gtk.Label(label="Kanal", xalign=0)
        lbl_chan.get_style_context().add_class("field-label")
        ccol.pack_start(lbl_chan, False, False, 0)
        self.entry_channel = Gtk.Entry()
        self.entry_channel.get_style_context().add_class("modern-entry")
        self.entry_channel.set_placeholder_text("Otomatik")
        ccol.pack_start(self.entry_channel, False, True, 0)
        freq_row.pack_start(ccol, True, True, 0)

        freq_card.pack_start(freq_row, False, False, 0)
        page.pack_start(freq_card, False, False, 0)

        # Feature switches
        opt_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        opt_card.get_style_context().add_class("card")

        otitle = Gtk.Label(label="KABLOSUZ AĞ ÖZELLİKLERİ", xalign=0)
        otitle.get_style_context().add_class("card-title")
        opt_card.pack_start(otitle, False, False, 0)

        self.sw_hidden = self._make_switch_row(opt_card, "Gizli SSID", "Ağ adını kablosuz taramalarda gizler (--hidden)")
        self.sw_isolate = self._make_switch_row(opt_card, "Cihaz İzolasyonu", "Bağlı cihazların birbiriyle iletişimini engeller (--isolate-clients)")
        self.sw_novirt = self._make_switch_row(opt_card, "Sanal Arayüz Devre Dışı", "Doğrudan fiziksel arayüzü kullanır (--no-virt)")
        self.sw_n = self._make_switch_row(opt_card, "IEEE 802.11n Desteği", "Yüksek hızlı Wi-Fi 4 standardını etkinleştirir")
        self.sw_ac = self._make_switch_row(opt_card, "IEEE 802.11ac Desteği", "Wi-Fi 5 standardını etkinleştirir (5GHz gerektirir)")
        self.sw_ax = self._make_switch_row(opt_card, "IEEE 802.11ax Desteği", "Wi-Fi 6 standardını etkinleştirir")

        page.pack_start(opt_card, False, False, 0)

        # Network / MAC
        net_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        net_card.get_style_context().add_class("card")

        ntitle = Gtk.Label(label="AĞ VE MAC ADRESİ", xalign=0)
        ntitle.get_style_context().add_class("card-title")
        net_card.pack_start(ntitle, False, False, 0)

        lbl_gw = Gtk.Label(label="Gateway (Ağ Geçidi) IP", xalign=0)
        lbl_gw.get_style_context().add_class("field-label")
        net_card.pack_start(lbl_gw, False, False, 0)
        self.entry_gateway = Gtk.Entry()
        self.entry_gateway.get_style_context().add_class("modern-entry")
        self.entry_gateway.set_placeholder_text("192.168.12.1")
        net_card.pack_start(self.entry_gateway, False, False, 0)

        lbl_mac = Gtk.Label(label="Özel AP MAC Adresi", xalign=0)
        lbl_mac.get_style_context().add_class("field-label")
        net_card.pack_start(lbl_mac, False, False, 0)
        self.entry_mac = Gtk.Entry()
        self.entry_mac.get_style_context().add_class("modern-entry")
        self.entry_mac.set_placeholder_text("Rastgele / Varsayılan")
        net_card.pack_start(self.entry_mac, False, False, 0)

        page.pack_start(net_card, False, False, 0)

        outer_scroll.add(page)
        return outer_scroll

    def _make_switch_row(self, parent, label_text, subtext):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.get_style_context().add_class("switch-row")
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl = Gtk.Label(label=label_text, xalign=0)
        lbl.get_style_context().add_class("field-label")
        vbox.pack_start(lbl, False, False, 0)
        sub = Gtk.Label(label=subtext, xalign=0)
        sub.get_style_context().add_class("status-sub-inactive")
        sub.set_line_wrap(True)
        vbox.pack_start(sub, False, False, 0)
        row.pack_start(vbox, True, True, 0)

        sw = Gtk.Switch()
        sw.set_valign(Gtk.Align.CENTER)
        row.pack_start(sw, False, False, 0)
        parent.pack_start(row, False, False, 0)
        return sw

    # ── QR page ──────────────────────────────────────────────────────────

    def _build_qr_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_bottom(24)

        qr_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        qr_card.get_style_context().add_class("card")
        qr_card.set_vexpand(True)
        qr_card.set_halign(Gtk.Align.CENTER)
        qr_card.set_valign(Gtk.Align.CENTER)

        qrtitle = Gtk.Label(label="HIZLI BAĞLANTI QR KODU", xalign=0.5)
        qrtitle.get_style_context().add_class("card-title")
        qr_card.pack_start(qrtitle, False, False, 0)

        self.qr_image = Gtk.Image()
        qr_card.pack_start(self.qr_image, True, True, 8)

        self.qr_info_lbl = Gtk.Label(
            label="Mobil cihazınızın kamerası ile taratarak şifre yazmadan anında bağlanabilirsiniz.")
        self.qr_info_lbl.get_style_context().add_class("status-sub-inactive")
        self.qr_info_lbl.set_line_wrap(True)
        self.qr_info_lbl.set_justify(Gtk.Justification.CENTER)
        self.qr_info_lbl.set_max_width_chars(40)
        qr_card.pack_start(self.qr_info_lbl, False, False, 0)

        btn_save_qr = Gtk.Button(label="QR Kodu Kaydet / İndir")
        btn_save_qr.get_style_context().add_class("btn-secondary")
        btn_save_qr.set_halign(Gtk.Align.CENTER)
        btn_save_qr.connect("clicked", self._on_save_qr_code)
        qr_card.pack_start(btn_save_qr, False, False, 4)

        page.pack_start(qr_card, True, True, 0)
        return page

    # ──────────────────────────────────────────────────────────────────
    # Tray
    # ──────────────────────────────────────────────────────────────────

    def _build_tray(self):
        icon_path, icon_active_path = write_tray_icons()
        self.tray_icon_path = icon_path
        self.tray_icon_active_path = icon_active_path

        self.indicator = AppIndicator3.Indicator.new(
            APP_ID,
            os.path.abspath(icon_path),
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_title(APP_NAME)

        menu = Gtk.Menu()

        self.tray_status_item = Gtk.MenuItem(label="Hotspot Kapalı")
        self.tray_status_item.set_sensitive(False)
        menu.append(self.tray_status_item)

        menu.append(Gtk.SeparatorMenuItem())

        self.tray_toggle_item = Gtk.MenuItem(label="Hotspot Başlat")
        self.tray_toggle_item.connect("activate", lambda i: self._on_toggle_hotspot(self.btn_action))
        menu.append(self.tray_toggle_item)

        show_item = Gtk.MenuItem(label="Pencereyi Göster")
        show_item.connect("activate", self._on_tray_show)
        menu.append(show_item)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Çıkış Yap (Hotspot'u Kapat)")
        quit_item.connect("activate", self._on_tray_quit)
        menu.append(quit_item)

        menu.show_all()
        self.indicator.set_menu(menu)

    # ──────────────────────────────────────────────────────────────────
    # Config & QR logic
    # ──────────────────────────────────────────────────────────────────

    def _load_initial_config(self):
        wifi_ifaces = get_wifi_interfaces()
        all_ifaces = get_all_interfaces()

        self.combo_wifi.remove_all()
        for iface in wifi_ifaces:
            self.combo_wifi.append_text(iface)

        self.combo_inet.remove_all()
        self.combo_inet.append_text("İnternet Paylaşımı Yok (Sadece Yerel Ağ)")
        for iface in all_ifaces:
            self.combo_inet.append_text(iface)

        cfg = read_config()

        self.entry_ssid.set_text(cfg.get('SSID', 'NetShare-WiFi'))
        self.entry_pass.set_text(cfg.get('PASSPHRASE', '12345678'))
        self.entry_channel.set_text(cfg.get('CHANNEL', ''))
        self.entry_gateway.set_text(cfg.get('GATEWAY', '192.168.12.1'))
        self.entry_mac.set_text(cfg.get('NEW_MACADDR', ''))

        self.sw_open.set_active(cfg.get('PASSPHRASE', '') == '')
        self.sw_hidden.set_active(cfg.get('HIDDEN', '0') == '1')
        self.sw_isolate.set_active(cfg.get('ISOLATE_CLIENTS', '0') == '1')
        self.sw_novirt.set_active(cfg.get('NO_VIRT', '0') == '1')
        self.sw_n.set_active(cfg.get('IEEE80211N', '0') == '1')
        self.sw_ac.set_active(cfg.get('IEEE80211AC', '0') == '1')
        self.sw_ax.set_active(cfg.get('IEEE80211AX', '0') == '1')

        freq = cfg.get('FREQ_BAND', 'auto').lower()
        if freq == '2.4':
            self.combo_freq.set_active(1)
        elif freq == '5':
            self.combo_freq.set_active(2)
        else:
            self.combo_freq.set_active(0)

        wifi_iface = cfg.get('WIFI_IFACE', 'wlan0')
        if wifi_iface in wifi_ifaces:
            self.combo_wifi.set_active(wifi_ifaces.index(wifi_iface))
        elif wifi_ifaces:
            self.combo_wifi.set_active(0)

        inet_iface = cfg.get('INTERNET_IFACE', 'none')
        if inet_iface == 'none':
            self.combo_inet.set_active(0)
        else:
            for i, ifc in enumerate(all_ifaces):
                if ifc == inet_iface:
                    self.combo_inet.set_active(i + 1)
                    break
            else:
                self.combo_inet.set_active(0)

        self._update_band_stat()
        self._update_qr_code()

    def _update_band_stat(self):
        idx = self.combo_freq.get_active()
        label = {0: "Otomatik", 1: "2.4 GHz", 2: "5 GHz"}.get(idx, "Otomatik")
        self.stat_band_val.set_text(label)

    def _on_toggle_open_network(self, switch, gparam):
        is_open = switch.get_active()
        self.entry_pass.set_sensitive(not is_open)
        self._update_qr_code()

    def _on_pass_icon_press(self, entry, icon_pos, event):
        if icon_pos == Gtk.EntryIconPosition.SECONDARY:
            visible = entry.get_visibility()
            entry.set_visibility(not visible)
            new_icon = "view-conceal-symbolic" if not visible else "view-reveal-symbolic"
            entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, new_icon)

    def _get_qr_string(self):
        ssid = self.entry_ssid.get_text().strip() or "NetShare-WiFi"
        is_open = self.sw_open.get_active()
        password = self.entry_pass.get_text().strip()
        if is_open:
            return f"WIFI:S:{ssid};T:nopass;;"
        return f"WIFI:S:{ssid};T:WPA;P:{password};;"

    def _update_qr_code(self):
        if hasattr(self, "stat_ssid_val"):
            ssid = self.entry_ssid.get_text().strip() or "—"
            self.stat_ssid_val.set_text(ssid)

        qr_text = self._get_qr_string()

        def _gen():
            try:
                cmd = ["qrencode", "-t", "SVG", "-o", "-", qr_text]
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    GLib.idle_add(self._set_qr_pixbuf, r.stdout)
            except Exception as e:
                print("QR error:", e)
        threading.Thread(target=_gen, daemon=True).start()

    def _set_qr_pixbuf(self, svg_data):
        try:
            loader = GdkPixbuf.PixbufLoader.new_with_type('svg')
            loader.set_size(200, 200)
            loader.write(svg_data.encode())
            loader.close()
            self.qr_image.set_from_pixbuf(loader.get_pixbuf())
        except Exception:
            pass

    def _on_save_qr_code(self, button):
        dialog = Gtk.FileChooserDialog(
            title="QR Kodu Kaydet",
            parent=self.window,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            "İptal", Gtk.ResponseType.CANCEL,
            "Kaydet", Gtk.ResponseType.ACCEPT
        )
        dialog.set_current_name("netshare-qr.png")
        dialog.set_do_overwrite_confirmation(True)

        filter_png = Gtk.FileFilter()
        filter_png.set_name("PNG Görsel (*.png)")
        filter_png.add_pattern("*.png")
        dialog.add_filter(filter_png)

        filter_svg = Gtk.FileFilter()
        filter_svg.set_name("SVG Vektör (*.svg)")
        filter_svg.add_pattern("*.svg")
        dialog.add_filter(filter_svg)

        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            target_path = dialog.get_filename()
            dialog.destroy()
            self._export_qr_file(target_path)
        else:
            dialog.destroy()

    def _export_qr_file(self, file_path):
        qr_text = self._get_qr_string()
        fmt = "SVG" if file_path.endswith(".svg") else "PNG"
        cmd = ["qrencode", "-t", fmt, "-o", file_path, qr_text]

        def _do_export():
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    GLib.idle_add(self._show_toast, f"QR kodu kaydedildi: {os.path.basename(file_path)}", False, 2600)
                else:
                    GLib.idle_add(self._show_toast, "QR kodu kaydedilemedi!", True, 2600)
            except Exception as e:
                GLib.idle_add(self._show_toast, f"Hata: {e}", True, 3200)

        threading.Thread(target=_do_export, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────
    # Hotspot control
    # ──────────────────────────────────────────────────────────────────

    def _check_status(self):
        def _check():
            running, pid, iface = is_hotspot_running()
            GLib.idle_add(self._update_ui_status, running, pid, iface)
        threading.Thread(target=_check, daemon=True).start()

    def _set_dot_state(self, dot_widget, state):
        ctx = dot_widget.get_style_context()
        ctx.remove_class("dot-active")
        ctx.remove_class("dot-inactive")
        ctx.remove_class("dot-loading")
        ctx.add_class(f"dot-{state}")

    def _update_ui_status(self, running, pid, iface):
        self.is_running = running
        self.hotspot_pid = pid

        sc = self.status_card.get_style_context()
        sc.remove_class("status-active")
        sc.remove_class("status-inactive")
        sc.remove_class("status-loading")

        tc = self.status_title.get_style_context()
        tc.remove_class("status-title-active")
        tc.remove_class("status-title-inactive")

        subc = self.status_sub.get_style_context()
        subc.remove_class("status-sub-active")
        subc.remove_class("status-sub-inactive")
        subc.remove_class("status-sub-loading")

        if running:
            sc.add_class("status-active")
            tc.add_class("status-title-active")
            subc.add_class("status-sub-active")

            self.status_title.set_text("Hotspot Aktif")
            ssid = self.entry_ssid.get_text() or "NetShare"
            self.status_sub.set_text(f"Yayında: {ssid}  •  PID {pid}")

            self.btn_action.set_label("Hotspot Durdur")
            ctx = self.btn_action.get_style_context()
            ctx.remove_class("btn-primary")
            ctx.add_class("btn-danger")

            self._set_inputs_sensitive(False)
            self._set_dot_state(self.hero_dot, "active")
            self._set_dot_state(self.sidebar_dot, "active")
            self.sidebar_status_lbl.set_text("Hotspot aktif")

            self.hdr_pill.set_text(f"● {ssid}")
            self.hdr_pill.get_style_context().remove_class("hdr-pill-inactive")
            self.hdr_pill.get_style_context().add_class("hdr-pill-active")

            if self.indicator:
                self.indicator.set_icon_full(os.path.abspath(self.tray_icon_active_path), "Active")
                self.tray_status_item.set_label(f"Aktif: {ssid}")
                self.tray_toggle_item.set_label("Hotspot Durdur")

            self._refresh_clients()
            if self.poll_timer_id:
                GLib.source_remove(self.poll_timer_id)
            self.poll_timer_id = GLib.timeout_add_seconds(5, self._poll_clients)

        else:
            sc.add_class("status-inactive")
            tc.add_class("status-title-inactive")
            subc.add_class("status-sub-inactive")

            self.status_title.set_text("Hotspot Kapalı")
            self.status_sub.set_text("Başlatmak için aşağıdaki butona tıklayın")

            self.btn_action.set_label("Hotspot Başlat")
            ctx = self.btn_action.get_style_context()
            ctx.remove_class("btn-danger")
            ctx.add_class("btn-primary")

            self._set_inputs_sensitive(True)
            self._set_dot_state(self.hero_dot, "inactive")
            self._set_dot_state(self.sidebar_dot, "inactive")
            self.sidebar_status_lbl.set_text("Hotspot kapalı")

            self.hdr_pill.set_text("● Kapalı")
            self.hdr_pill.get_style_context().remove_class("hdr-pill-active")
            self.hdr_pill.get_style_context().add_class("hdr-pill-inactive")

            if self.indicator:
                self.indicator.set_icon_full(os.path.abspath(self.tray_icon_path), "Inactive")
                self.tray_status_item.set_label("Hotspot Kapalı")
                self.tray_toggle_item.set_label("Hotspot Başlat")

            if self.poll_timer_id:
                GLib.source_remove(self.poll_timer_id)
                self.poll_timer_id = None

            self.dev_badge.set_text("0 Cihaz")
            self.stat_devices_val.set_text("0")
            self._clear_devices_ui()

        self.btn_action.set_sensitive(True)
        self.progress.set_visible(False)
        self._stop_pulse()

    def _set_inputs_sensitive(self, sensitive):
        self.entry_ssid.set_sensitive(sensitive)
        self.combo_wifi.set_sensitive(sensitive)
        self.combo_inet.set_sensitive(sensitive)
        self.combo_freq.set_sensitive(sensitive)
        self.entry_channel.set_sensitive(sensitive)
        self.sw_hidden.set_sensitive(sensitive)
        self.sw_isolate.set_sensitive(sensitive)
        self.sw_novirt.set_sensitive(sensitive)
        self.sw_n.set_sensitive(sensitive)
        self.sw_ac.set_sensitive(sensitive)
        self.sw_ax.set_sensitive(sensitive)
        self.entry_gateway.set_sensitive(sensitive)
        self.entry_mac.set_sensitive(sensitive)
        self.sw_open.set_sensitive(sensitive)
        self.entry_pass.set_sensitive(sensitive and not self.sw_open.get_active())

    def _on_toggle_hotspot(self, button):
        self.btn_action.set_sensitive(False)
        self._show_loading()

        if self.is_running:
            self._stop_hotspot()
        else:
            self._start_hotspot()

    def _show_loading(self):
        sc = self.status_card.get_style_context()
        sc.remove_class("status-active")
        sc.remove_class("status-inactive")
        sc.add_class("status-loading")

        subc = self.status_sub.get_style_context()
        subc.remove_class("status-sub-active")
        subc.remove_class("status-sub-inactive")
        subc.add_class("status-sub-loading")

        self._set_dot_state(self.hero_dot, "loading")

        self.progress.set_visible(True)
        self._start_pulse()

    def _start_pulse(self):
        self._pulse_active = True

        def pulse():
            if self._pulse_active:
                self.progress.pulse()
                return True
            return False
        GLib.timeout_add(100, pulse)

    def _stop_pulse(self):
        self._pulse_active = False

    def _start_hotspot(self):
        ssid = self.entry_ssid.get_text().strip()
        is_open = self.sw_open.get_active()
        password = self.entry_pass.get_text().strip()
        wifi = self.combo_wifi.get_active_text()
        inet_idx = self.combo_inet.get_active()
        inet = "none" if inet_idx == 0 else self.combo_inet.get_active_text()

        if not ssid:
            self._show_error("Ağ adı (SSID) boş olamaz!")
            return
        if not is_open and len(password) < 8:
            self._show_error("Şifre en az 8 karakter olmalıdır!")
            return
        if not wifi:
            self._show_error("Lütfen bir WiFi arayüzü seçin!")
            return

        self.status_title.set_text("Başlatılıyor...")
        self.status_sub.set_text("Ayarlar kaydediliyor ve hotspot yayını başlatılıyor")

        freq_idx = self.combo_freq.get_active()
        freq = "2.4" if freq_idx in [0, 1] else "5"
        channel = self.entry_channel.get_text().strip() or "8"
        gateway = self.entry_gateway.get_text().strip() or "192.168.12.1"
        mac = self.entry_mac.get_text().strip()

        cfg = {
            'SSID': ssid,
            'PASSPHRASE': '' if is_open else password,
            'WIFI_IFACE': wifi,
            'INTERNET_IFACE': inet,
            'FREQ_BAND': freq,
            'CHANNEL': channel,
            'GATEWAY': gateway,
            'HIDDEN': '1' if self.sw_hidden.get_active() else '0',
            'ISOLATE_CLIENTS': '1' if self.sw_isolate.get_active() else '0',
            'NO_VIRT': '1' if self.sw_novirt.get_active() else '0',
            'IEEE80211N': '1' if self.sw_n.get_active() else '0',
            'IEEE80211AC': '1' if self.sw_ac.get_active() else '0',
            'IEEE80211AX': '1' if self.sw_ax.get_active() else '0',
            'USE_PSK': '0',
            'SHARE_METHOD': 'none' if inet == 'none' else 'nat',
            'NEW_MACADDR': mac,
            'DAEMONIZE': '0',
            'DAEMON_LOGFILE': '/dev/null',
            'NO_HAVEGED': '0'
        }

        def _do_start():
            save_config(cfg)
            run_cmd("sudo -n systemctl restart create_ap", timeout=10)

            for _ in range(12):
                time.sleep(0.5)
                running, pid, iface = is_hotspot_running()
                if running:
                    GLib.idle_add(self._update_ui_status, True, pid, iface)
                    return

            running, pid, iface = is_hotspot_running()
            GLib.idle_add(self._update_ui_status, running, pid, iface)
            if not running:
                GLib.idle_add(self._show_error, "Hotspot başlatılamadı! Ayarları kontrol edin.")

        threading.Thread(target=_do_start, daemon=True).start()

    def _stop_hotspot(self):
        self.status_title.set_text("Durduruluyor...")
        self.status_sub.set_text("Servis sonlandırılıyor")

        def _do_stop():
            run_cmd("sudo -n systemctl stop create_ap", timeout=10)

            for _ in range(10):
                time.sleep(0.3)
                running, _, _ = is_hotspot_running()
                if not running:
                    break

            GLib.idle_add(self._update_ui_status, False, None, None)

        threading.Thread(target=_do_stop, daemon=True).start()

    def _show_error(self, msg):
        self.btn_action.set_sensitive(True)
        self._stop_pulse()
        self.progress.set_visible(False)

        sc = self.status_card.get_style_context()
        sc.remove_class("status-loading")
        sc.add_class("status-inactive")

        self.status_title.set_text("Hata")
        self.status_sub.set_text(msg)
        self._set_dot_state(self.hero_dot, "inactive")
        self._show_toast(msg, is_error=True, duration_ms=3400)

    # ──────────────────────────────────────────────────────────────────
    # Connected clients
    # ──────────────────────────────────────────────────────────────────

    def _refresh_clients(self):
        def _fetch():
            clients = get_connected_clients()
            GLib.idle_add(self._update_clients_ui, clients)
        threading.Thread(target=_fetch, daemon=True).start()

    def _poll_clients(self):
        if not self.is_running:
            return False
        self._refresh_clients()
        return True

    def _clear_devices_ui(self):
        for child in self.devices_listbox.get_children():
            self.devices_listbox.remove(child)
        for child in self.preview_box.get_children():
            self.preview_box.remove(child)
        self.preview_box.pack_start(self.preview_empty_lbl, True, True, 24)
        self.devices_page_stack.set_visible_child_name("empty")
        self.preview_box.show_all()

    def _copy_field(self, label_name, value_text):
        if copy_to_clipboard(value_text):
            self._show_toast(f"{label_name} kopyalandı: {value_text}")

    def _update_clients_ui(self, clients):
        self.all_clients = clients

        for child in self.devices_listbox.get_children():
            self.devices_listbox.remove(child)
        for child in self.preview_box.get_children():
            self.preview_box.remove(child)

        self.dev_badge.set_text(f"{len(clients)} Cihaz")
        self.stat_devices_val.set_text(str(len(clients)))

        if not clients:
            self.devices_page_stack.set_visible_child_name("empty")
            self.preview_box.pack_start(self.preview_empty_lbl, True, True, 24)
        else:
            self.devices_page_stack.set_visible_child_name("list")
            for item in clients:
                full_row = self._make_device_row_widget(item)
                lb_row = Gtk.ListBoxRow()
                lb_row.search_key = f"{item['hostname']} {item['ip']} {item['mac']}".lower()
                lb_row.add(full_row)
                self.devices_listbox.add(lb_row)

            for item in clients[:3]:
                self.preview_box.pack_start(self._make_device_row_widget(item, compact=True), False, False, 0)

        self.devices_listbox.invalidate_filter()
        self.devices_listbox.show_all()
        self.preview_box.show_all()

    # ──────────────────────────────────────────────────────────────────
    # Window / tray lifecycle
    # ──────────────────────────────────────────────────────────────────

    def _on_window_state(self, window, event):
        if event.new_window_state & Gdk.WindowState.ICONIFIED:
            GLib.idle_add(self._hide_to_tray)
            return True
        return False

    def _hide_to_tray(self):
        self.window.deiconify()
        self.window.hide()

    def _on_tray_show(self, item):
        self.window.show_all()
        self.toast_revealer.set_reveal_child(False)
        self.window.present()
        self.window.deiconify()
        self._check_status()

    def _on_tray_quit(self, item):
        if self.poll_timer_id:
            GLib.source_remove(self.poll_timer_id)

        if self.is_running:
            run_cmd("sudo -n systemctl stop create_ap", timeout=5)

        self.release()
        self.quit()

    def _on_close(self, window, event):
        window.hide()
        return True


# ─── Entry Point ──────────────────────────────────────────────────────

def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = NetShareApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
