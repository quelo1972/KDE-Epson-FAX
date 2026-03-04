import subprocess


def get_all_printers():
    """
    Restituisce tutte le stampanti configurate in CUPS
    usando lpstat -a (indipendente dalla lingua)
    """
    try:
        result = subprocess.run(
            ["lpstat", "-a"],
            capture_output=True,
            text=True
        )

        printers = []

        for line in result.stdout.splitlines():
            if line.strip():
                # Il nome stampante è sempre il primo token
                printer_name = line.split()[0]
                printers.append(printer_name)

        return printers

    except Exception:
        return []


def get_fax_printers():
    """
    Restituisce solo stampanti con backend epsonfax://
    """
    try:
        result = subprocess.run(
            ["lpstat", "-v"],
            capture_output=True,
            text=True
        )

        fax_printers = []

        for line in result.stdout.splitlines():
            if "epsonfax://" in line:
                # formato tipico:
                # dispositivo per EPSON_FAX: epsonfax://192.168.1.16
                parts = line.split()
                # Il nome stampante è sempre prima dei :
                for part in parts:
                    if part.endswith(":"):
                        printer_name = part.replace(":", "")
                        fax_printers.append(printer_name)
                        break

        return fax_printers

    except Exception:
        return []
