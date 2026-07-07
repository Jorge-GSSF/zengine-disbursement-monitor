from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from monitor import DisbursementMonitor
from settings import Settings


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

app = FastAPI(title="Zengine Disbursement Monitor")
scheduler = BackgroundScheduler(timezone="America/New_York")
settings = Settings.from_env()
monitor = DisbursementMonitor(settings)
last_result: dict[str, object] = {"status": "starting"}


def run_monitor_job() -> None:
    global last_result
    try:
        result = monitor.run_once()
        last_result = {
            "status": "ok",
            "scanned": result.scanned,
            "approved": result.approved,
            "sent": result.sent,
            "skipped_existing": result.skipped_existing,
        }
    except Exception as exc:
        logging.exception("Monitor job failed")
        last_result = {"status": "error", "error": str(exc)}


@app.on_event("startup")
def startup() -> None:
    scheduler.add_job(
        run_monitor_job,
        trigger="interval",
        minutes=max(1, settings.check_interval_minutes),
        id="zengine-disbursement-monitor",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    if settings.run_on_startup:
        run_monitor_job()


@app.on_event("shutdown")
def shutdown() -> None:
    scheduler.shutdown(wait=False)


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    missing = settings.missing_required_values()
    missing_html = "".join(f"<li>{key}</li>" for key in missing) or "<li>None</li>"
    result_html = "".join(
        f"<li><strong>{key}</strong>: {value}</li>" for key, value in last_result.items()
    )
    return f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Zengine Disbursement Monitor</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 40px; color: #111827; }}
          main {{ max-width: 760px; }}
          h1 {{ font-size: 28px; margin-bottom: 8px; }}
          section {{ border-top: 1px solid #d1d5db; margin-top: 24px; padding-top: 18px; }}
          li {{ margin: 6px 0; }}
          code {{ background: #f3f4f6; padding: 2px 5px; border-radius: 4px; }}
        </style>
      </head>
      <body>
        <main>
          <h1>Zengine Disbursement Monitor</h1>
          <p>Checking form <code>{settings.zengine_form_id}</code> every <code>{settings.check_interval_minutes}</code> minutes for status <code>{settings.zengine_approved_value}</code>.</p>
          <section>
            <h2>Missing Environment</h2>
            <ul>{missing_html}</ul>
          </section>
          <section>
            <h2>Last Result</h2>
            <ul>{result_html}</ul>
          </section>
        </main>
      </body>
    </html>
    """


@app.post("/run-once")
def run_once(secret: str = "") -> dict[str, object]:
    if not settings.run_once_secret or secret != settings.run_once_secret:
        raise HTTPException(status_code=403, detail="Manual runs are disabled or the secret is invalid.")
    run_monitor_job()
    if last_result.get("status") == "error":
        raise HTTPException(status_code=500, detail=last_result)
    return last_result
