from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import load_settings
from data.store import Store

STATIC = Path(__file__).resolve().parent / "static"


def get_store() -> Store:
    settings = load_settings()
    return Store(settings["database"]["url"])


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _json(self, payload, code: int = 200) -> None:
        raw = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def _file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            self._file(STATIC / "index.html", "text/html; charset=utf-8")
            return
        if path == "/api/overview":
            store = get_store()
            drawings = store.query("SELECT * FROM live_drawings ORDER BY created_ts DESC LIMIT 80")
            reviews = store.query("SELECT label, COUNT(*) AS n FROM drawing_reviews GROUP BY label")
            reports = store.query("SELECT * FROM reports ORDER BY created_ts DESC LIMIT 20")
            genomes = store.query("SELECT * FROM genomes ORDER BY fitness DESC LIMIT 5")
            corr = store.query("SELECT * FROM correlations ORDER BY ABS(weight) DESC LIMIT 12")
            fills = store.query("SELECT * FROM paper_fills ORDER BY created_ts DESC LIMIT 20")
            from dashboard.series import fills_by_venue
            from execution.kill_switch import is_killed
            from learning.forward import forward_stats
            fill_rows = fills.to_dict(orient="records") if not fills.empty else []
            self._json(
                {
                    "drawings": drawings.to_dict(orient="records") if not drawings.empty else [],
                    "reviews": reviews.to_dict(orient="records") if not reviews.empty else [],
                    "reports": reports.to_dict(orient="records") if not reports.empty else [],
                    "genomes": genomes.to_dict(orient="records") if not genomes.empty else [],
                    "correlations": corr.to_dict(orient="records") if not corr.empty else [],
                    "paper_fills": fill_rows,
                    "fills_by_venue": fills_by_venue(fill_rows),
                    "forward": forward_stats(store),
                    "killed": is_killed(store),
                }
            )
            return
        if path == "/api/health":
            self._json({"ok": True})
            return
        if path == "/api/ohlcv":
            q = parse_qs(parsed.query)
            settings = load_settings()
            store = get_store()
            exchange = (q.get("exchange") or [settings["exchanges"]["primary"]])[0]
            symbol = (q.get("symbol") or [settings["symbols"]["perps"][0]])[0]
            tf = (q.get("tf") or ["4h"])[0]
            from dashboard.series import candles_payload

            df = store.load_ohlcv(exchange, symbol, tf)
            self._json({"symbol": symbol, "tf": tf, "candles": candles_payload(df)})
            return
        if path == "/api/cvd":
            q = parse_qs(parsed.query)
            settings = load_settings()
            store = get_store()
            exchange = (q.get("exchange") or [settings["exchanges"]["primary"]])[0]
            symbol = (q.get("symbol") or [settings["symbols"]["perps"][0]])[0]
            from dashboard.series import spark_payload

            df = store.load_cvd(exchange, symbol, "swap", "4h")
            self._json({"symbol": symbol, "spark": spark_payload(df)})
            return
        self._json({"error": "not_found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            body = {}
        if parsed.path == "/api/review":
            store = get_store()
            store.execute(
                """
                INSERT INTO drawing_reviews (drawing_id, label, note, created_ts)
                VALUES (:drawing_id, :label, :note, CAST(strftime('%s','now') AS INTEGER)*1000)
                """,
                {
                    "drawing_id": int(body.get("drawing_id") or 0),
                    "label": str(body.get("label") or "skip"),
                    "note": str(body.get("note") or ""),
                },
            )
            if body.get("drawing_id"):
                store.execute(
                    "UPDATE live_drawings SET status=:s WHERE id=:id",
                    {"s": str(body.get("label") or "skip"), "id": int(body["drawing_id"])},
                )
            self._json({"ok": True})
            return
        if parsed.path == "/api/kill":
            from execution.kill_switch import set_enabled
            store = get_store()
            enabled = bool(body.get("enabled", False))
            set_enabled(store, enabled)
            self._json({"ok": True, "enabled": enabled})
            return
        self._json({"error": "not_found"}, 404)


def main() -> None:
    host = "0.0.0.0"
    port = int((parse_qs(urlparse("//x").query).get("port") or [8765])[0]) if False else 8765
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"dashboard http://127.0.0.1:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
