# Smart Office Attendance Monitor

Passive presence detection system for office networks.  
Tracks which employees are in the office based on device connectivity to the local Wi-Fi/LAN — no software installation required on employee devices.

---

## How it works

`scanner.py` scans the subnet every 15 seconds (ICMP + ARP), detects active devices from a whitelist and publishes events via MQTT.  
`listener.py` subscribes to the broker and writes each event to a SQLite database.  
`discord_bot.py` provides a command interface over Discord and sends automatic morning/evening reports.

---

## Project structure

```
├── scanner.py          # Network scanning, MQTT publishing
├── listener.py         # MQTT subscriber, SQLite logging
├── discord_bot.py      # Discord bot — commands and scheduled reports
├── config.py           # Device whitelist (MAC -> name)
├── perf_test.py        # Performance tests (scan time, MQTT latency)
├── sec_test.py         # Security tests (MAC spoofing, broker auth)
├── requirements.txt    # Python dependencies
└── .env.example        # Environment variable template
```

---

## Requirements

- Python 3.10+
- Local MQTT broker (Mosquitto)

```bash
# Ubuntu/Debian
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable --now mosquitto
```

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

`.env` must contain a valid Discord bot token and channel ID.

---

## Device configuration

`config.py` holds the device whitelist:

```python
KNOWN_DEVICES = {
    "aa:bb:cc:dd:ee:01": "Ivan",
    "aa:bb:cc:dd:ee:02": "Danylo",
}
```

MAC addresses can be retrieved with `arp -a` after a device connects to the network.

---

## Running

Three separate processes:

```bash
python scanner.py
python listener.py
python discord_bot.py
```

For persistent deployment, each script can be registered as a `systemd` service.

---

## Bot commands

| Command | Description |
|---|---|
| `!status` | Who is currently in the office |
| `!today` | Who was present today |
| `!history <name>` | Last 10 events for a specific person |
| `!stats` | Entry count and last-seen time per device |
| `!missing` | Who is currently absent |

Automatic reports are sent at **08:00** and **17:00** to the configured Discord channel.

---

## Authors

- Ivan — album no. 50251  
- Danylo — album no. 53513
