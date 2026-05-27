import sys
import time
import json
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

# Reconfigure stdout to use UTF-8
sys.stdout.reconfigure(encoding='utf-8')


from config import MQTT_BROKER, MQTT_PORT
from scanner import scan_known_devices

# High-resolution clock measurement helper
def measure_scan_performance():
    print("[Perf Test] Rozpoczynanie pomiaru wydajności skanowania sieci...")
    start_time = time.perf_counter()
    
    # Run the actual scanning function from scanner.py
    online_devices = scan_known_devices()
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    print(f"[Perf Test] Skanowanie ukończone w czasie: {duration:.4f} s")
    print(f"[Perf Test] Wykryte aktywne urządzenia znane: {list(online_devices)}")
    return duration


def measure_mqtt_latency():
    print("\n[Perf Test] Rozpoczynanie pomiaru opóźnienia MQTT (Mosquitto)...")
    
    received_timestamps = []
    latencies = []
    
    # Setup temporary test client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="perf-test-client")
    
    TEST_TOPIC = "office/presence/perf_test"
    
    def on_connect(client, userdata, flags, reason_code, properties):
        client.subscribe(TEST_TOPIC)
        
    def on_message(client, userdata, msg):
        recv_time = time.perf_counter()
        try:
            payload = json.loads(msg.payload.decode())
            sent_time = payload["ts"]
            latency_ms = (recv_time - sent_time) * 1000
            latencies.append(latency_ms)
            print(f"  [+] Otrzymano pakiet testowy. Opóźnienie: {latency_ms:.2f} ms")
        except Exception as e:
            print(f"  [-] Błąd parsowania pakietu: {e}")

    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()
        
        # Wait a bit for connection and subscription to stabilize
        time.sleep(1)
        
        # Publish 5 test packages
        for i in range(5):
            sent_time = time.perf_counter()
            payload = json.dumps({"test_id": i, "ts": sent_time})
            client.publish(TEST_TOPIC, payload)
            time.sleep(0.5) # Space out messages
            
        # Give a moment for the last message to arrive
        time.sleep(1)
        client.loop_stop()
        client.disconnect()
        
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            print(f"[Perf Test] Statystyki opóźnienia MQTT:")
            print(f"  - Średnie opóźnienie: {avg_latency:.2f} ms")
            print(f"  - Minimalne opóźnienie: {min_latency:.2f} ms")
            print(f"  - Maksymalne opóźnienie: {max_latency:.2f} ms")
        else:
            print("[-] Błąd: Nie odebrano żadnych pakietów testowych MQTT.")
            
    except Exception as e:
        print(f"[-] Błąd połączenia z brokerem MQTT {MQTT_BROKER}:{MQTT_PORT} - {e}")


def main():
    print("=== TESTY WYDAJNOŚCIOWE SYSTEMU ===")
    measure_scan_performance()
    measure_mqtt_latency()
    print("===================================")


if __name__ == "__main__":
    main()
