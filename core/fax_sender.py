import subprocess
import threading
import time
from core.database import add_history, update_status

active_jobs = 0
lock = threading.Lock()


def monitor_job(job_id, printer, notify_callback=None, status_callback=None):
    global active_jobs

    with lock:
        active_jobs += 1

    while True:
        # Polling dinamico
        interval = 2 if active_jobs > 0 else 5
        time.sleep(interval)

        result = subprocess.run(
            ["lpstat", "-l", "-o", printer],
            capture_output=True,
            text=True
        )

        output = result.stdout

        # Job non più attivo
        if job_id not in output:

            completed = subprocess.run(
                ["lpstat", "-W", "completed"],
                capture_output=True,
                text=True
            ).stdout

            if job_id in completed:
                update_status(job_id, "COMPLETED")
                if notify_callback:
                    notify_callback("Fax completato", f"{job_id} inviato correttamente")
            else:
                update_status(job_id, "FAILED")
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
            if notify_callback:
                notify_callback("Fax fallito", f"{job_id} errore di stampa")

            subprocess.run(["cancel", job_id])
            break

    with lock:
        active_jobs -= 1

    if status_callback:
        status_callback()


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

            add_history(printer, recipient, file_path, job_id, "QUEUED")

            thread = threading.Thread(
                target=monitor_job,
                args=(job_id, printer, notify_callback, status_callback),
                daemon=True
            )
            thread.start()

        else:
            add_history(printer, recipient, file_path, None, "FAILED")
            if notify_callback:
                notify_callback("Fax fallito", "Errore comando lp")

    except Exception as e:
        add_history(printer, recipient, file_path, None, "FAILED")
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
