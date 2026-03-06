#!/bin/bash

# =========================================
# VPN Aziendale con openfortivpn
# =========================================

CONFIG_BASEDIR="$HOME/.config/openfortivpn"
CONFIG="$CONFIG_BASEDIR/config"
PID_FILE="$CONFIG_BASEDIR/vpn.pid"
LOG_UP="$CONFIG_BASEDIR/vpn-up.log"

MAX_WAIT=15   # secondi massimi di attesa connessione

# ---------- Funzioni ----------

vpn_is_up() {
    ip link show ppp0 >/dev/null 2>&1
}

start_vpn() {

    if vpn_is_up; then
        echo "VPN già attiva."
        return
    fi

    if [ ! -f "$CONFIG" ]; then
        echo "Errore: file di configurazione $CONFIG non trovato!"
        echo "Usa lo script install.sh per crearlo"
        exit 1
    fi

    echo "Avvio VPN..."

    nohup sudo openfortivpn --config "$CONFIG" > "$LOG_UP" 2>&1 &
    VPN_PID=$!

    echo "Connessione in corso..."

    for ((i=1;i<=MAX_WAIT;i++)); do

        if vpn_is_up; then
            echo "$VPN_PID" > "$PID_FILE"

            notify-send "VPN" "Connessa"

            echo "VPN connessa (PID $VPN_PID)"
            echo "------ Contenuto vpn-up.log ------"
            cat "$LOG_UP"
            echo "---------------------------------"

            # imposto dns resolver e dafault domain aziendali
            sudo resolvectl dns ppp0 192.168.23.11 192.168.23.12
            sudo resolvectl domain ppp0 comune.spoleto.local

            return
        fi

        sleep 1
    done

    echo "Errore: la VPN non si è connessa entro $MAX_WAIT secondi."
    echo "------ Contenuto vpn-up.log ------"
    cat "$LOG_UP"
    echo "---------------------------------"

    sudo kill "$VPN_PID" 2>/dev/null
    rm -f "$PID_FILE"
}

stop_vpn() {

    if vpn_is_up; then

        echo "Arresto VPN..."

        VPN_PID=$(cat "$PID_FILE" 2>/dev/null)

        sudo kill "$VPN_PID" 2>/dev/null
        sleep 2

        rm -f "$PID_FILE"

        notify-send "VPN" "Disconnessa"
        echo "VPN disconnessa."

    else

        notify-send "VPN" "VPN non attiva"
        echo "VPN non attiva."

    fi
}

status_vpn() {

    if vpn_is_up; then
        echo "VPN attiva."
    else
        echo "VPN non attiva."
    fi
}

# ---------- Main ----------

# forza richiesta password sudo
sudo -v

case "$1" in
    start) start_vpn ;;
    stop) stop_vpn ;;
    status) status_vpn ;;
    *)
        echo "Uso: $0 {start|stop|status}"
        exit 1
        ;;
esac
