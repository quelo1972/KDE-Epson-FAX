import subprocess


def notify(title, message):
    try:
        subprocess.run(["notify-send", title, message])
    except Exception:
        pass
