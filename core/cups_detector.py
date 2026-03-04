import subprocess


def detect_fax_printers():
    printers = []

    try:
        result = subprocess.run(
            ["lpstat", "-v"],
            capture_output=True,
            text=True
        )

        for line in result.stdout.splitlines():
            if "epsonfax://" in line:
                parts = line.split()
                name = parts[2].replace(":", "")
                printers.append(name)

    except Exception:
        pass

    return printers
