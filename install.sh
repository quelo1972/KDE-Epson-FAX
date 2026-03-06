#!/bin/bash

CONFIG_DIR="$HOME/.config/openfortivpn"
CONFIG_FILE="$CONFIG_DIR/config"

echo "=== Installazione configurazione openfortivpn ==="
echo

if ! command -v openfortivpn >/dev/null 2>&1; then
    echo "Errore: openfortivpn non è installato."
    exit 1
fi

# Crea directory
if [ ! -d "$CONFIG_DIR" ]; then
    mkdir -p "$CONFIG_DIR"
    chmod 700 "$CONFIG_DIR"
    echo "Creata directory $CONFIG_DIR"
fi

# Sovrascrittura
if [ -f "$CONFIG_FILE" ]; then
    read -p "Il file config esiste già. Sovrascriverlo? (s/N): " OVERWRITE
    if [[ "$OVERWRITE" != "s" && "$OVERWRITE" != "S" ]]; then
        echo "Operazione annullata."
        exit 0
    fi
fi

# Input utente
read -p "Host VPN: " VPN_HOST
read -p "Porta VPN [443]: " VPN_PORT
VPN_PORT=${VPN_PORT:-443}
read -p "Username VPN: " VPN_USER
read -s -p "Password VPN: " VPN_PASS
echo
echo

echo "Recupero fingerprint reale dal gateway..."
echo "Potrebbe chiedere la password sudo."
echo

# LANCIO COME ROOT SENZA PASSWORD VPN
TMP_OUTPUT=$(echo "" | sudo timeout 8 openfortivpn ${VPN_HOST}:${VPN_PORT} \
    --username=${VPN_USER} 2>&1)

# Estrazione robusta del fingerprint (prima stringa hex di 64 caratteri)
VPN_CERT=$(echo "$TMP_OUTPUT" | grep -oE '[a-f0-9]{64}' | head -n1)

echo
echo "Fingerprint rilevato dal client:"
echo "$VPN_CERT"
echo

read -p "Confermi di volerlo usare? (S/n): " CONFIRM
if [[ "$CONFIRM" == "n" || "$CONFIRM" == "N" ]]; then
    echo "Operazione annullata."
    exit 0
fi

# Scrittura config
cat > "$CONFIG_FILE" <<EOF
host = $VPN_HOST
port = $VPN_PORT
username = $VPN_USER
password = $VPN_PASS
trusted-cert = $VPN_CERT
set-dns = 0
EOF

chmod 600 "$CONFIG_FILE"

echo
echo "Configurazione salvata in $CONFIG_FILE"
echo "Installazione completata con successo."
