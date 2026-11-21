#!/usr/bin/env python3
"""claude-manager: server locale (solo 127.0.0.1) per vedere E gestire la config di Claude Code.

Scrive soltanto in ~/.claude/settings.json, chiavi `skillOverrides` ed `enabledPlugins`,
e fa sempre prima un backup in ./backups. Valori ammessi per una skill: on | off | user-invocable-only.
"""
import json, shutil, time, importlib, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
SETTINGS = Path.home() / ".claude/settings.json"
STATES = {"on", "off", "user-invocable-only"}
sys.path.insert(0, str(HERE))
import scan


def collect():
    importlib.reload(scan)
    return scan.data


def backup():
    (HERE / "backups").mkdir(exist_ok=True)
    shutil.copy2(SETTINGS, HERE / "backups" / f"settings.{int(time.time())}.json")


def save(mutate):
    s = json.loads(SETTINGS.read_text())
    mutate(s)
    backup()
    tmp = SETTINGS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(SETTINGS)


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if self.path == "/api/data":
            return self._send(200, json.dumps(collect(), ensure_ascii=False))
        if self.path in ("/", "/index.html"):
            return self._send(200, (HERE / "template.html").read_text(), "text/html; charset=utf-8")
        self._send(404, "{}")

    def do_POST(self):
        # difesa CSRF/DNS-rebinding: solo richieste dalla stessa origine locale
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin", "")
        if not host.startswith(("127.0.0.1:", "localhost:")) or (origin and origin.split("//")[-1] != host):
            return self._send(403, '{"error":"forbidden"}')
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if self.path == "/api/skill":
                name, state = str(body["name"]), body["state"]
                if state not in STATES:
                    return self._send(400, '{"error":"stato non valido"}')
                def m(s):
                    o = s.setdefault("skillOverrides", {})
                    if state == "on": o.pop(name, None)
                    else: o[name] = state
                save(m)
            elif self.path == "/api/plugin":
                pid, en = str(body["id"]), bool(body["enabled"])
                save(lambda s: s.setdefault("enabledPlugins", {}).__setitem__(pid, en))
            else:
                return self._send(404, "{}")
        except Exception as e:
            return self._send(400, json.dumps({"error": str(e)}))
        self._send(200, '{"ok":true}')

    def log_message(self, *a): pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"Claude Manager: http://127.0.0.1:{port}  (Ctrl+C per fermare)")
    HTTPServer(("127.0.0.1", port), H).serve_forever()
