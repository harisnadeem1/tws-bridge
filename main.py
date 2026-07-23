import os
import sys
import time
import queue
import asyncio
import threading
from pathlib import Path

from dotenv import load_dotenv, set_key
from services.vps_client import VpsClient
from services.tws_client import TwsClient

import tkinter as tk
from tkinter import ttk, messagebox


APP_NAME = "GianKom Tools TWS Bridge"
ENV_FILE = Path(".env")
LOG_FILE = Path("bridge.log")

FIXED_VPS_BASE_URL = "https://giankom.com/api"
FIXED_TWS_HOST = "127.0.0.1"
FIXED_TWS_CLIENT_ID = "0"


def log(message: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line, flush=True)


def ensure_env_file():
    if not ENV_FILE.exists():
        ENV_FILE.write_text(
            f"VPS_BASE_URL={FIXED_VPS_BASE_URL}\n"
            "BRIDGE_TOKEN=\n"
            f"TWS_HOST={FIXED_TWS_HOST}\n"
            "TWS_PORT=7496\n"
            f"TWS_CLIENT_ID={FIXED_TWS_CLIENT_ID}\n",
            encoding="utf-8"
        )


def get_env_value(key, default=""):
    load_dotenv(override=True)
    return os.getenv(key, default)


def save_env_value(key, value):
    ensure_env_file()
    set_key(str(ENV_FILE), key, str(value))
    os.environ[key] = str(value)


class BridgeApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("560x360")
        self.root.minsize(560, 360)
        self.root.configure(bg="#0f172a")

        self.queue = queue.Queue()
        self.connection_thread = None
        self.connected = False

        self.status_var = tk.StringVar(value="Ready")
        self.detail_var = tk.StringVar(value="Enter your bridge token and connect.")
        self.token_var = tk.StringVar(value=get_env_value("BRIDGE_TOKEN", ""))
        self.port_var = tk.StringVar(value=get_env_value("TWS_PORT", "7496"))

        self.vps = None
        self.tws = None

        self._build_styles()
        self._build_ui()
        self._poll_queue()

    def _build_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("Card.TFrame", background="#111827")
        style.configure("App.TFrame", background="#0f172a")
        style.configure("Title.TLabel", background="#0f172a", foreground="#f8fafc", font=("Segoe UI", 18, "bold"))
        style.configure("Sub.TLabel", background="#0f172a", foreground="#94a3b8", font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background="#111827", foreground="#f8fafc", font=("Segoe UI", 11, "bold"))
        style.configure("Field.TLabel", background="#111827", foreground="#cbd5e1", font=("Segoe UI", 10))
        style.configure("Hint.TLabel", background="#111827", foreground="#94a3b8", font=("Segoe UI", 9))
        style.configure("Status.TLabel", background="#111827", foreground="#e2e8f0", font=("Segoe UI", 10, "bold"))
        style.configure("TEntry", padding=8)
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=10)
        style.configure("Secondary.TButton", font=("Segoe UI", 10), padding=10)

    def _build_ui(self):
        outer = ttk.Frame(self.root, style="App.TFrame", padding=20)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="App.TFrame")
        header.pack(fill="x", pady=(0, 16))

        ttk.Label(header, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Secure bridge connection for TWS and VPS sync.",
            style="Sub.TLabel"
        ).pack(anchor="w", pady=(4, 0))

        card = ttk.Frame(outer, style="Card.TFrame", padding=18)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="Connection Settings", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 14)
        )

        ttk.Label(card, text="Bridge Token", style="Field.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 12), pady=8
        )
        self.token_entry = ttk.Entry(card, textvariable=self.token_var, show="*")
        self.token_entry.grid(row=1, column=1, sticky="ew", pady=8)

        ttk.Label(card, text="TWS Port", style="Field.TLabel").grid(
            row=2, column=0, sticky="w", padx=(0, 12), pady=8
        )
        self.port_entry = ttk.Entry(card, textvariable=self.port_var)
        self.port_entry.grid(row=2, column=1, sticky="ew", pady=8)

        ttk.Label(
            card,
            text=f"TWS Host is fixed to {FIXED_TWS_HOST} | Client ID is fixed to {FIXED_TWS_CLIENT_ID}",
            style="Hint.TLabel"
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 2))

        ttk.Label(
            card,
            text=f"Server URL is fixed to {FIXED_VPS_BASE_URL}",
            style="Hint.TLabel"
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 10))

        card.columnconfigure(1, weight=1)

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(16, 8))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)

        self.connect_btn = ttk.Button(
            actions, text="Connect", style="Primary.TButton", command=self.start_connect
        )
        self.connect_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.save_btn = ttk.Button(
            actions, text="Save", style="Secondary.TButton", command=self.save_settings
        )
        self.save_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        status_box = ttk.Frame(card, style="Card.TFrame")
        status_box.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(14, 0))

        ttk.Label(status_box, text="Status", style="Status.TLabel").pack(anchor="w")

        self.status_label = tk.Label(
            status_box,
            textvariable=self.status_var,
            bg="#111827",
            fg="#f59e0b",
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        )
        self.status_label.pack(fill="x", pady=(6, 2))

        self.detail_label = tk.Label(
            status_box,
            textvariable=self.detail_var,
            bg="#111827",
            fg="#cbd5e1",
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=480
        )
        self.detail_label.pack(fill="x")

    def set_status(self, title, detail="", color="#f59e0b"):
        self.status_var.set(title)
        self.detail_var.set(detail)
        self.status_label.config(fg=color)
        log(f"{title} - {detail}")

    def save_settings(self):
        try:
            token = self.token_var.get().strip()
            port = self.port_var.get().strip()

            if not token:
                raise ValueError("Bridge token is required.")
            if not port.isdigit():
                raise ValueError("TWS Port must be a number.")

            save_env_value("VPS_BASE_URL", FIXED_VPS_BASE_URL)
            save_env_value("TWS_HOST", FIXED_TWS_HOST)
            save_env_value("TWS_CLIENT_ID", FIXED_TWS_CLIENT_ID)
            save_env_value("BRIDGE_TOKEN", token)
            save_env_value("TWS_PORT", port)

            self.set_status("Saved", "Bridge token and TWS port saved successfully.", "#22c55e")
        except Exception as e:
            self.set_status("Save Failed", str(e), "#ef4444")
            messagebox.showerror(APP_NAME, str(e))

    def start_connect(self):
        if self.connection_thread and self.connection_thread.is_alive():
            return

        self.connect_btn.config(state="disabled")
        self.save_btn.config(state="disabled")
        self.set_status("Connecting...", "Starting secure bridge connection.", "#60a5fa")

        self.connection_thread = threading.Thread(target=self._connect_worker, daemon=True)
        self.connection_thread.start()

    def _connect_worker(self):
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            token = self.token_var.get().strip()
            port_text = self.port_var.get().strip()

            if not token:
                raise ValueError("Bridge token is required.")
            if not port_text.isdigit():
                raise ValueError("TWS Port must be a valid number.")

            port = int(port_text)
            base_url = FIXED_VPS_BASE_URL
            host = FIXED_TWS_HOST
            client_id = int(FIXED_TWS_CLIENT_ID)

            save_env_value("VPS_BASE_URL", base_url)
            save_env_value("TWS_HOST", host)
            save_env_value("TWS_CLIENT_ID", FIXED_TWS_CLIENT_ID)
            save_env_value("BRIDGE_TOKEN", token)
            save_env_value("TWS_PORT", port)

            load_dotenv(override=True)

            self.queue.put(("status", "Validating Key...", "Checking bridge credentials with server.", "#60a5fa"))

            self.vps = VpsClient()
            try:
                heartbeat_result = self.vps.heartbeat()
            except Exception as e:
                msg = str(e).lower()
                if "401" in msg or "403" in msg or "unauthorized" in msg or "forbidden" in msg or "invalid" in msg:
                    raise ValueError("Key is not correct.")
                raise ValueError(f"Could not validate key: {e}")

            self.queue.put(("status", "Key Accepted", "Credentials verified successfully.", "#22c55e"))
            self.queue.put(("status", "Connecting to TWS...", f"Host {host}:{port}, Client ID {client_id}", "#60a5fa"))

            self.tws = TwsClient(self.vps)

            try:
                self.tws.connect(host, port, client_id)
            except Exception as e:
                raise ValueError(f"TWS not running or connection failed: {e}")

            self.connected = True
            self.queue.put(("status", "Connected", "Bridge is connected and running.", "#22c55e"))

            threading.Thread(target=self._heartbeat_loop, daemon=True).start()
            self.tws.run()

        except Exception as e:
            self.connected = False
            self.queue.put(("error", str(e)))
        finally:
            try:
                if loop and not loop.is_closed():
                    loop.close()
            except Exception:
                pass

    def _heartbeat_loop(self):
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            while self.connected and self.vps:
                try:
                    result = self.vps.heartbeat()
                    self.queue.put(("status", "Connected", f"Heartbeat OK", "#22c55e"))
                except Exception as e:
                    self.connected = False
                    msg = str(e).lower()
                    if "401" in msg or "403" in msg or "unauthorized" in msg or "forbidden" in msg or "invalid" in msg:
                        self.queue.put(("error", "Key is not correct."))
                    else:
                        self.queue.put(("error", f"Heartbeat failed: {e}"))
                    break
                time.sleep(15)
        finally:
            try:
                if loop and not loop.is_closed():
                    loop.close()
            except Exception:
                pass

    def _poll_queue(self):
        try:
            while True:
                item = self.queue.get_nowait()
                kind = item[0]

                if kind == "status":
                    _, title, detail, color = item
                    self.set_status(title, detail, color)

                    if title == "Connected":
                        self.connect_btn.config(state="disabled")
                        self.save_btn.config(state="normal")

                elif kind == "error":
                    _, error_message = item
                    self.connect_btn.config(state="normal")
                    self.save_btn.config(state="normal")
                    self.set_status("Connection Failed", error_message, "#ef4444")
                    messagebox.showerror(APP_NAME, error_message)

        except queue.Empty:
            pass

        self.root.after(200, self._poll_queue)


def main():
    ensure_env_file()
    load_dotenv(override=True)

    root = tk.Tk()
    BridgeApp(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"Fatal error: {e}")
        try:
            messagebox.showerror(APP_NAME, str(e))
        except Exception:
            pass
        sys.exit(1)