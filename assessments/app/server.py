#!/usr/bin/env python3
"""
selfcare-api — a tiny, dependency-free telecom self-care service.

Used across the Module 1–3 assignments. It is deliberately built on the Python
standard library only (no Flask, no pip install) so the *container image* is the
only moving part: you build it once in Module 1, then run the very same image as
a Pod / Deployment in Modules 2–3.

Endpoints
---------
  GET /healthz            -> liveness/readiness probe target ({"status":"ok"})
  GET /version            -> build + runtime info (image tag, pod name, region)
  GET /subscribers        -> list all subscribers (MSISDN + plan)
  GET /subscribers/<msisdn> -> one subscriber's profile + plan + balance
  GET /tariffs            -> tariff catalog
  GET /                   -> service banner

Configuration (12-factor: everything via environment)
-----------------------------------------------------
  SELFCARE_PORT      TCP port to listen on            (default 8080)
  SELFCARE_DATA_DIR  directory holding the datasets    (default ./data)
  SELFCARE_REGION    region label shown in /version    (default "unknown")
  SELFCARE_BANNER    banner text shown on /            (default "Mobily Self-Care")
  SELFCARE_API_KEY   if set, all /subscribers* calls   (default unset = open)
                     require header  X-API-Key: <value>
  HOSTNAME           reported as "pod" in /version      (set by the container)

Datasets live in $SELFCARE_DATA_DIR:  subscribers.json, tariffs.json
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = os.environ.get("SELFCARE_VERSION", "1.0.0")
PORT = int(os.environ.get("SELFCARE_PORT", "8080"))
DATA_DIR = os.environ.get("SELFCARE_DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
REGION = os.environ.get("SELFCARE_REGION", "unknown")
BANNER = os.environ.get("SELFCARE_BANNER", "Mobily Self-Care")
API_KEY = os.environ.get("SELFCARE_API_KEY")  # None => auth disabled


def _load(name):
    path = os.path.join(DATA_DIR, name)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_data():
    subs = {s["msisdn"]: s for s in _load("subscribers.json")}
    tariffs = {t["code"]: t for t in _load("tariffs.json")}
    return subs, tariffs


try:
    SUBSCRIBERS, TARIFFS = load_data()
except FileNotFoundError as exc:
    sys.stderr.write(f"FATAL: dataset not found: {exc}\n")
    sys.stderr.write(f"       Looked in SELFCARE_DATA_DIR={DATA_DIR}\n")
    raise


class Handler(BaseHTTPRequestHandler):
    server_version = "selfcare-api/" + VERSION

    def _send(self, code, payload):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        if not API_KEY:
            return True
        return self.headers.get("X-API-Key") == API_KEY

    def log_message(self, format, *args):
        # one-line access log to stdout so `kubectl logs` / `podman logs` show it
        sys.stdout.write("%s - %s\n" % (self.address_string(), format % args))
        sys.stdout.flush()

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")

        if path == "" or path == "/":
            return self._send(200, {"service": BANNER, "version": VERSION,
                                     "endpoints": ["/healthz", "/version",
                                                   "/subscribers", "/subscribers/<msisdn>",
                                                   "/tariffs"]})

        if path == "/healthz":
            return self._send(200, {"status": "ok"})

        if path == "/version":
            return self._send(200, {
                "version": VERSION,
                "region": REGION,
                "pod": os.environ.get("HOSTNAME", "n/a"),
                "subscribers_loaded": len(SUBSCRIBERS),
                "tariffs_loaded": len(TARIFFS),
            })

        if path == "/tariffs":
            return self._send(200, list(TARIFFS.values()))

        if path == "/subscribers":
            if not self._authorized():
                return self._send(401, {"error": "missing or invalid X-API-Key"})
            return self._send(200, [{"msisdn": s["msisdn"], "plan": s["plan"]}
                                    for s in SUBSCRIBERS.values()])

        if path.startswith("/subscribers/"):
            if not self._authorized():
                return self._send(401, {"error": "missing or invalid X-API-Key"})
            msisdn = path.rsplit("/", 1)[1]
            sub = SUBSCRIBERS.get(msisdn)
            if not sub:
                return self._send(404, {"error": "subscriber not found", "msisdn": msisdn})
            tariff = TARIFFS.get(sub["plan"], {})
            return self._send(200, {**sub, "tariff": tariff})

        return self._send(404, {"error": "no such endpoint", "path": path})


def main():
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    sys.stdout.write(
        f"selfcare-api {VERSION} listening on :{PORT} "
        f"(region={REGION}, data={DATA_DIR}, auth={'on' if API_KEY else 'off'})\n")
    sys.stdout.flush()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
