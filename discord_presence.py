"""Minimal Discord Rich Presence client using Discord's local IPC pipe."""

import json
import os
import socket
import struct
import time


OP_HANDSHAKE = 0
OP_FRAME = 1
OP_CLOSE = 2
OP_PING = 3
OP_PONG = 4


class DiscordPresenceClient:
    def __init__(self):
        self.client_id = ""
        self.conn = None
        self.connected = False
        self.last_error = ""
        self.last_response = {}
        self.last_activity_key = None
        self.start_time = int(time.time())

    def configure(self, client_id):
        client_id = str(client_id or "").strip()
        if client_id != self.client_id:
            self.close()
            self.client_id = client_id
            self.last_activity_key = None

    def _pipe_names(self):
        if os.name == "nt":
            return [r"\\?\pipe\discord-ipc-{}".format(index) for index in range(10)]
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR") or os.environ.get("TMPDIR") or "/tmp"
        return [os.path.join(runtime_dir, "discord-ipc-{}".format(index)) for index in range(10)]

    def _send(self, opcode, payload):
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        packet = struct.pack("<II", opcode, len(data)) + data
        if hasattr(self.conn, "sendall"):
            self.conn.sendall(packet)
        else:
            self.conn.write(packet)
            self.conn.flush()

    def _read_exact(self, length):
        if hasattr(self.conn, "recv"):
            data = b""
            while len(data) < length:
                chunk = self.conn.recv(length - len(data))
                if not chunk:
                    raise OSError("Discord IPC closed")
                data += chunk
            return data
        return self.conn.read(length)

    def _recv(self):
        header = self._read_exact(8)
        if len(header) < 8:
            raise OSError("Discord IPC closed")
        opcode, length = struct.unpack("<II", header)
        data = self._read_exact(length)
        payload = json.loads(data.decode("utf-8")) if data else {}
        return opcode, payload

    def connect(self):
        if self.connected:
            return True
        if not self.client_id:
            self.last_error = "Discord client ID is not configured."
            return False

        last_error = ""
        for pipe_name in self._pipe_names():
            try:
                if os.name == "nt":
                    self.conn = open(pipe_name, "r+b", buffering=0)
                else:
                    sock = socket.socket(socket.AF_UNIX)
                    sock.settimeout(2)
                    sock.connect(pipe_name)
                    self.conn = sock
                self._send(OP_HANDSHAKE, {"v": 1, "client_id": self.client_id})
                opcode, payload = self._recv()
                if opcode in (OP_FRAME, OP_PONG) and payload.get("cmd") == "DISPATCH":
                    self.connected = True
                    self.last_error = ""
                    return True
                last_error = str(payload.get("message") or "Unexpected Discord IPC response.")
                self.close()
            except Exception as exc:
                last_error = str(exc)
                self.close()

        self.last_error = last_error or "Could not connect to Discord."
        return False

    def update(self, details, state="", large_image="", large_text="", small_image="", small_text="", buttons=None, name="UEM Tracker"):
        activity = {
            "application_id": self.client_id,
            "name": str(name or "UEM Tracker")[:128],
            "type": 0,
            "details": str(details or "")[:128],
            "state": str(state or "")[:128],
            "timestamps": {"start": self.start_time},
            "instance": False,
        }
        assets = {}
        if large_image:
            assets["large_image"] = str(large_image)
        if large_text:
            assets["large_text"] = str(large_text)[:128]
        if small_image:
            assets["small_image"] = str(small_image)
        if small_text:
            assets["small_text"] = str(small_text)[:128]
        if assets:
            activity["assets"] = assets
        if buttons:
            activity["buttons"] = buttons[:2]

        activity_key = json.dumps(activity, sort_keys=True)
        if activity_key == self.last_activity_key and self.connected:
            return True

        if not self.connect():
            return False

        try:
            nonce = str(time.time())
            self._send(OP_FRAME, {
                "cmd": "SET_ACTIVITY",
                "args": {"pid": os.getpid(), "activity": activity},
                "nonce": nonce,
            })
            _, payload = self._recv()
            self.last_response = payload
            if payload.get("evt") == "ERROR":
                data = payload.get("data") or {}
                self.last_error = str(data.get("message") or payload.get("message") or "Discord rejected the activity.")
                return False
            if payload.get("nonce") != nonce and payload.get("cmd") not in ("SET_ACTIVITY", "DISPATCH"):
                self.last_error = str(payload.get("message") or "Unexpected Discord activity response.")
                return False
            self.last_activity_key = activity_key
            self.last_error = ""
            return True
        except Exception as exc:
            self.last_error = str(exc)
            self.close()
            return False

    def get_last_response_summary(self):
        if not isinstance(self.last_response, dict) or not self.last_response:
            return ""
        cmd = str(self.last_response.get("cmd") or "")
        evt = str(self.last_response.get("evt") or "")
        data = self.last_response.get("data") or {}
        activity = data.get("activity") if isinstance(data, dict) else {}
        parts = []
        if cmd:
            parts.append(f"cmd={cmd}")
        if evt and evt != "None":
            parts.append(f"evt={evt}")
        if isinstance(activity, dict):
            activity_name = activity.get("name")
            if activity_name:
                parts.append(f"name={activity_name}")
        return ", ".join(parts)

    def clear(self):
        if not self.connected and not self.connect():
            return False
        try:
            nonce = str(time.time())
            self._send(OP_FRAME, {
                "cmd": "SET_ACTIVITY",
                "args": {"pid": os.getpid()},
                "nonce": nonce,
            })
            _, payload = self._recv()
            self.last_response = payload
            self.last_activity_key = None
            return True
        except Exception as exc:
            self.last_error = str(exc)
            self.close()
            return False

    def close(self):
        if self.conn:
            try:
                if self.connected:
                    if hasattr(self.conn, "sendall"):
                        self.conn.sendall(struct.pack("<II", OP_CLOSE, 0))
                    else:
                        self.conn.write(struct.pack("<II", OP_CLOSE, 0))
                        self.conn.flush()
            except Exception:
                pass
            try:
                self.conn.close()
            except Exception:
                pass
        self.conn = None
        self.connected = False


discord_presence = DiscordPresenceClient()
