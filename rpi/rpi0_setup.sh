#!/usr/bin/env bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root. Please run with sudo." 
   exit 1
fi

# CONFIG_FILE="/boot/config.txt" # newer version may have /boot/firmware/config.txt
CONFIG_FILE="/boot/firmware/config.txt"
# CMDLINE_FILE="/boot/cmdline.txt" # see comment above
CMDLINE_FILE="/boot/firmware/cmdline.txt"
DTOVERLAY="dtoverlay=dwc2"
MODULES="modules-load=dwc2,g_ether"
DHCPCD="/etc/dhcpcd.conf"
# DHCPCD="dhcpcd.conf"
ETHERNET_INTERFACE="usb0"
STATIC_IP="10.0.20.193"

sudo apt install -y i2c-tools python3-picamera2 python3-libcamera python3-opencv

usage() {
  echo "'''Configures $CONFIG_FILE and $CMDLINE_FILE for ethernet over usb"
  echo "and sets static ip address in $DHCPCD'''"
  echo ""
  echo "Usage: $0 -s <static_ip>"
  echo "Options:"
  echo "  -s <static_ip>             Static IP address to assign (e.g., 192.168.1.100)"
  echo "  -h, --help                 Display this help message"
}

while getopts ":i:s:h" opt; do
  case $opt in
    s)
      STATIC_IP=$OPTARG
      ;;
    h|\?)
      usage
      exit 0
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z $STATIC_IP ]]; then
  usage
  exit 1
fi

if grep -q "$DTOVERLAY" "$CONFIG_FILE"; then
  echo "'$DTOVERLAY' is already in $CONFIG_FILE."
else
  cp "$CONFIG_FILE" "$CONFIG_FILE.bak"
  echo "$DTOVERLAY" >> "$CONFIG_FILE"
  echo "'$DTOVERLAY' appended in $CONFIG_FILE."
fi

if grep -q "$MODULES" "$CMDLINE_FILE"; then
  echo "'$MODULES' is already in $CMDLINE_FILE."
else
  cp "$CMDLINE_FILE" "$CMDLINE_FILE.bak"
  sed -i "s/rootwait/& $MODULES/" "$CMDLINE_FILE"
  echo "'$MODULES' appended to $CMDLINE_FILE."
fi

if grep -q "interface $ETHERNET_INTERFACE" "$DHCPCD"; then
  echo "'interface $ETHERNET_INTERFACE' is already in $DHCPCD"
else
  cp "$DHCPCD" "$DHCPCD.bak"
  echo -e "interface $ETHERNET_INTERFACE\nstatic ip_address=$STATIC_IP/24" >> "$DHCPCD"
  echo "'interface $ETHERNET_INTERFACE' config appended to $DHCPCD"
fi

# TODO: is it possible to have more occurences of rootwait - yes
