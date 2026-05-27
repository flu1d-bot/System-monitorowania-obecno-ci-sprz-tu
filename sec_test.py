import sys
import time
import json
import paho.mqtt.client as mqtt

# Reconfigure stdout to use UTF-8
sys.stdout.reconfigure(encoding='utf-8')


from config import MQTT_BROKER, MQTT_PORT, KNOWN_DEVICES

def test_mqtt_open_access():
    print("[Sec Test] Sprawdzanie poziomu zabezpieczeń brokera MQTT...")
    
    # Try to connect without password
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="attacker-client")
    
    connected_successfully = False
    
    def on_connect(client, userdata, flags, reason_code, properties):
        nonlocal connected_successfully
        if reason_code == 0:
            connected_successfully = True
            print("  [!] Ostrzeżenie: Połączono z brokerem BEZ credentials. Kanał jest podatny.")
        else:
            print(f"  [+] Broker odrzucił anonimowe połączenie (kod błędu: {reason_code}). Poprawne zabezpieczenie.")

    client.on_connect = on_connect
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=10)
        client.loop_start()
        time.sleep(1.5)
        client.loop_stop()
        client.disconnect()
    except Exception as e:
        print(f"  [+] Brak dostępu do brokera bez uwierzytelnienia (wyjątek: {e}). Zabezpieczenie działa.")
        connected_successfully = False
        
    return connected_successfully


def test_mac_spoofing_vectors():
    print("\n[Sec Test] Analiza podatności na MAC Spoofing:")
    print("  Opis zagrożenia:")
    print("    System opiera się na skanowaniu ARP w sieci lokalnej i weryfikuje adresy MAC.")
    print("    Dowolny użytkownik sieci LAN może zmienić swój adres fizyczny (MAC) na jeden")
    print("    z whitelisty w config.py, aby zasymulować obecność innego pracownika.")
    
    print("\n  Whitelista znanych urządzeń podatnych na podszycie:")
    for mac, name in KNOWN_DEVICES.items():
        print(f"    - Urządzenie: {name} (MAC: {mac})")
        
    print("\n  Rekomendowane metody mitygacji:")
    print("    1. Implementacja standardu IEEE 802.1X (uwierzytelnianie portów).")
    print("    2. Statyczna tabela ARP na przełącznikach sieciowych.")
    print("    3. Wdrożenie technologii DHCP Snooping i Dynamic ARP Inspection (DAI).")
    print("    4. Dodatkowe sprawdzanie tożsamości poprzez puszczenie żądania ping do urządzenia i analizę czasu TTL lub nazw hosta NetBIOS/mDNS.")


def main():
    print("=== TESTY BEZPIECZEŃSTWA SYSTEMU ===")
    test_mqtt_open_access()
    test_mac_spoofing_vectors()
    print("====================================")


if __name__ == "__main__":
    main()
