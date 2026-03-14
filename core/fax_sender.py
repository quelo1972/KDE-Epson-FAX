import subprocess
import threading
import time
from core.app_logging import get_logger
from core.database import add_history, update_status

active_jobs = 0
lock = threading.Lock()
logger = get_logger()


def get_active_jobs():
    with lock:
        return active_jobs


def monitor_job(job_id, printer, notify_callback=None, status_callback=None):
    global active_jobs

    logger.info("Monitor job started: %s on %s", job_id, printer)

    with lock:
        active_jobs += 1

    while True:
        # Polling dinamico
        with lock:
            current_jobs = active_jobs
        interval = 2 if current_jobs > 0 else 5
        time.sleep(interval)

        result = subprocess.run(
            ["lpstat", "-l", "-o", printer],
            capture_output=True,
            text=True
        )

        output = result.stdout
        if result.stderr:
            logger.warning("lpstat stderr for %s: %s", job_id, result.stderr.strip())

        # Job non più attivo
        if job_id not in output:

            completed = subprocess.run(
                ["lpstat", "-W", "completed"],
                capture_output=True,
                text=True
            ).stdout

            if job_id in completed:
                update_status(job_id, "COMPLETED")
                logger.info("Job completed: %s", job_id)
                if notify_callback:
                    notify_callback("Fax completato", f"{job_id} inviato correttamente")
            else:
                update_status(job_id, "FAILED")
                logger.warning("Job failed or missing in completed list: %s", job_id)
                if notify_callback:
                    notify_callback("Fax fallito", f"{job_id} non riuscito")

            break

        if "processing" in output:
            update_status(job_id, "PROCESSING")

        if any(err in output for err in [
            "Filter failed",
            "cups-filter-crashed",
            "stopped",
            "aborted"
        ]):
            update_status(job_id, "FAILED")
            logger.warning("Job error detected in output: %s", job_id)
            if notify_callback:
                notify_callback("Fax fallito", f"{job_id} errore di stampa")

            cancel_result = subprocess.run(["cancel", job_id], capture_output=True, text=True)
            if cancel_result.returncode != 0:
                logger.warning(
                    "Cancel failed for %s: %s",
                    job_id,
                    (cancel_result.stderr or cancel_result.stdout).strip()
                )
            break

    with lock:
        active_jobs -= 1

    if status_callback:
        status_callback()

    logger.info("Monitor job finished: %s", job_id)


def send_fax(printer, recipient, file_path,
             notify_callback=None,
             status_callback=None):
    try:
        command = [
            "lp",
            "-d", printer,
            "-o", f"phone={recipient}",
            file_path
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            output = result.stdout.strip()
            job_id = output.split()[3]
            logger.info("Fax queued: %s -> %s (%s)", printer, recipient, job_id)

            add_history(printer, recipient, file_path, job_id, "QUEUED")

            thread = threading.Thread(
                target=monitor_job,
                args=(job_id, printer, notify_callback, status_callback),
                daemon=True
            )
            thread.start()

        else:
            add_history(printer, recipient, file_path, None, "FAILED")
            logger.warning(
                "Fax send failed: %s -> %s (%s)",
                printer,
                recipient,
                (result.stderr or result.stdout).strip()
            )
            if notify_callback:
                notify_callback("Fax fallito", "Errore comando lp")

    except Exception as e:
        add_history(printer, recipient, file_path, None, "FAILED")
        logger.exception("Fax send exception: %s -> %s", printer, recipient)
        if notify_callback:
            notify_callback("Errore", str(e))


def send_fax_async(printer, recipient, file_path,
                   notify_callback=None,
                   status_callback=None):
    thread = threading.Thread(
        target=send_fax,
        args=(printer, recipient, file_path,
              notify_callback, status_callback),
        daemon=True
    )
    thread.start()


def cancel_fax(job_id):
    if not job_id:
        return False

    result = subprocess.run(["cancel", job_id], capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(
            "Cancel failed for %s: %s",
            job_id,
            (result.stderr or result.stdout).strip()
        )
        return False

    logger.info("Cancel requested: %s", job_id)
    return True
