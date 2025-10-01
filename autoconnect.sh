#!/bin/bash

# by @jasalt (https://github.com/schorschii/ImagingEdge4Linux/issues/4)

SSID="DIRECT-3XXX:DSC-RX100M7"
PASSWORD="z1zXXXXX"


# Backup current network connection details
CURRENT_SSID=$(nmcli -t c show --active |grep "wlan0"| head -n 1 | cut -d ':' -f 1)

# Connect to the specified SSID with the given password
nmcli dev wifi connect "$SSID" password "$PASSWORD"

# Wait for a few seconds to ensure the connection is established
sleep 6

if command -v uv >/dev/null 2>&1; then
	uv run imaging-edge.py
else
	python3 imaging-edge.py
fi

if [ -n "$CURRENT_SSID" ]; then
	echo "Reconnecting to the previously connected network..."
	nmcli con up "$CURRENT_SSID"
else
	echo "No previously connected network found."
	exit 1
fi

echo "Done."
