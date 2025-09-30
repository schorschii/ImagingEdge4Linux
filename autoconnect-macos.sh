#!/bin/bash

# macOS version of autoconnect.sh
# Automatically connects to Sony camera WiFi, runs imaging-edge.py, then reconnects to previous network

SSID="DIRECT-3XXX:DSC-RX100M7"
PASSWORD="z1zXXXXX"

echo "=== Sony Camera Auto-Connect Script for macOS ==="

# Get current WiFi network
CURRENT_SSID=$(networksetup -getairportnetwork en0 | cut -d ':' -f 2 | sed 's/^ *//')

if [ "$CURRENT_SSID" = "You are not associated with an AirPort network" ]; then
    CURRENT_SSID=""
    echo "No current WiFi connection detected."
else
    echo "Current network: $CURRENT_SSID"
fi

# Connect to camera WiFi
echo "Connecting to camera WiFi: $SSID"
networksetup -setairportnetwork en0 "$SSID" "$PASSWORD"

if [ $? -eq 0 ]; then
    echo "Successfully connected to camera WiFi"
else
    echo "Failed to connect to camera WiFi"
    exit 1
fi

# Wait for connection to stabilize
echo "Waiting for connection to stabilize..."
sleep 6

# Run the imaging edge script
echo "Running imaging-edge.py..."
uv run imaging-edge.py

# Reconnect to previous network if there was one
if [ -n "$CURRENT_SSID" ]; then
    echo "Reconnecting to previous network: $CURRENT_SSID"
    networksetup -setairportnetwork en0 "$CURRENT_SSID"
    
    if [ $? -eq 0 ]; then
        echo "Successfully reconnected to $CURRENT_SSID"
    else
        echo "Failed to reconnect to $CURRENT_SSID"
        echo "You may need to manually reconnect to your network"
    fi
else
    echo "No previous network to reconnect to."
fi

echo "Done."