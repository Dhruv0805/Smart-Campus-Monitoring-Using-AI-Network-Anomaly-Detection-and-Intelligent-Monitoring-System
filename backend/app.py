"""Flask entry point.   python -m backend.app   ->  http://localhost:5000"""
from __future__ import annotations

import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from engine import ROOT

from .routes.api import bp
from .services.monitor_service import MonitorService

DIST = ROOT / "frontend" / "dist"


def create_app(monitor: MonitorService | None = None, autostart: bool = True) -> Flask:
    app = Flask(__name__, static_folder=None)
    CORS(app)
    app.config["MONITOR"] = monitor or MonitorService(autostart=autostart)
    app.register_blueprint(bp)

    @app.errorhandler(404)
    def nf(_):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(500)
    def ise(e):
        return jsonify({"error": "internal error"}), 500

    if DIST.exists():  # serve the built React app so one process is enough for the demo
        @app.get("/", defaults={"path": ""})
        @app.get("/<path:path>")
        def spa(path):
            if path.startswith("api/"):
                return jsonify({"error": "not found"}), 404
            f = DIST / path
            if path and f.is_file():
                return send_from_directory(DIST, path)
            return send_from_directory(DIST, "index.html")
    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True)
