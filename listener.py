import json
import os
import sqlite3
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from config import KNOWN_DEVICES, MQTT_BROKER, MQTT_PORT

TOPIC_ONLINE  = "office/presence/online"
TOPIC_OFFLINE = "office/presence/offline"
DB_PATH       = os.path.join(os.path.dirname(__file__), "data", "office.db")


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS presence_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            mac       TEXT NOT NULL,
            name      TEXT NOT NULL,
            event     TEXT NOT NULL CHECK(event IN ('online','offline')),
            timestamp TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_mac_ts ON presence_log (mac, timestamp);
    """)
    conn.commit()


def on_connect(client, userdata, flags, reason_code, properties) -> None:
    print(f"[Listener] connected (rc={reason_code})")
    client.subscribe(TOPIC_ONLINE)
    client.subscribe(TOPIC_OFFLINE)


def on_message(client, userdata, msg) -> None:
    conn: sqlite3.Connection = userdata["conn"]
    try:
        data      = json.loads(msg.payload.decode())
        event     = "online" if msg.topic == TOPIC_ONLINE else "offline"
        mac       = data["mac"]
        name      = data.get("name", KNOWN_DEVICES.get(mac, "unknown"))
        timestamp = data.get("timestamp", datetime.now(timezone.utc).isoformat())

        conn.execute(
            "INSERT INTO presence_log (mac, name, event, timestamp) VALUES (?,?,?,?)",
            (mac, name, event, timestamp),
        )
        conn.commit()

        icon = "+" if event == "online" else "-"
        print(f"  [{icon}] {event.upper():7}  {name:15}  {timestamp}")

    except Exception as exc:
        print(f"[Listener] error: {exc}")


def main() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    init_db(conn)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="office-listener")
    client.user_data_set({"conn": conn})
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[Listener] connecting to {MQTT_BROKER}...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()
