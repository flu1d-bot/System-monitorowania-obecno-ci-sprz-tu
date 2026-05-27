import json
import re
import subprocess
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from config import KNOWN_DEVICES, MQTT_BROKER, MQTT_PORT, NETWORK_PREFIX, SCAN_INTERVAL

TOPIC_ONLINE  = "office/presence/online"
TOPIC_OFFLINE = "office/presence/offline"


def _ping(ip: str) -> None:
    subprocess.run(
        ["ping", "-n", "1", "-w", "200", ip],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def ping_sweep() -> None:
    threads = [
        threading.Thread(target=_ping, args=(f"{NETWORK_PREFIX}.{i}",), daemon=True)
        for i in range(1, 255)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=0.5)


def get_arp_map() -> dict[str, str]:
    result = subprocess.run(["arp", "-a"], capture_output=True)
    text = result.stdout.decode("cp1251", errors="replace")
    mac_to_ip: dict[str, str] = {}
    for line in text.splitlines():
        ip_m  = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
        mac_m = re.search(r"([\da-fA-F]{2}[-:]){5}[\da-fA-F]{2}", line)
        if ip_m and mac_m:
            ip  = ip_m.group(1)
            mac = mac_m.group(0).replace("-", ":").lower()
            if mac != "ff:ff:ff:ff:ff:ff" and not ip.startswith("224.") and ip != "255.255.255.255":
                mac_to_ip[mac] = ip
    return mac_to_ip


def ping_check(ip: str) -> bool:
    result = subprocess.run(
        ["ping", "-n", "1", "-w", "500", ip],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def scan_known_devices() -> set[str]:
    ping_sweep()
    time.sleep(1)
    arp_map = get_arp_map()

    online: set[str] = set()
    for mac in KNOWN_DEVICES:
        ip = arp_map.get(mac)
        if ip and ping_check(ip):
            online.add(mac)
    return online


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="office-scanner")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()
    print(f"[Scanner] broker={MQTT_BROKER}  interval={SCAN_INTERVAL}s")

    online: set[str] = set()

    while True:
        current  = scan_known_devices()
        now      = datetime.now(timezone.utc).isoformat()
        appeared = current - online
        vanished = online  - current

        for mac in appeared:
            payload = json.dumps({"mac": mac, "name": KNOWN_DEVICES[mac], "timestamp": now})
            client.publish(TOPIC_ONLINE, payload)
            print(f"  [+] ONLINE  {KNOWN_DEVICES[mac]:15} {mac}  {now}")

        for mac in vanished:
            payload = json.dumps({"mac": mac, "name": KNOWN_DEVICES[mac], "timestamp": now})
            client.publish(TOPIC_OFFLINE, payload)
            print(f"  [-] OFFLINE {KNOWN_DEVICES[mac]:15} {mac}  {now}")

        online = current
        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()
