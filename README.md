# Smart Office Attendance Monitor

System pasywnego monitorowania obecności urządzeń pracowników w sieci biurowej.

Jak działa

Skaner co 15 sekund wykrywa znane urządzenia w sieci (ARP + ping), publikuje zdarzenia przez MQTT, listener zapisuje wszystko do SQLite.

## Status projektu

### Zrobione (Etap 1)
- [x] Repozytorium GitHub
- [x] Wybór protokołu komunikacyjnego — MQTT
- [x] Lokalny broker Mosquitto
- [x] scanner.py — skanowanie sieci ARP + ping, publikacja zdarzeń MQTT
- [x] listener.py — odbieranie zdarzeń MQTT, zapis do SQLite
- [x] config.py — rejestr urządzeń (whitelist MAC)
- [x] Działający przepływ end-to-end potwierdzony nagraniem

### Do zrobienia (Etap 2)
- [ ] Discord Bot — raport poranny (08:00) i wieczorny (17:00)
- [ ] Komendy bota: !status, !today, !history, !stats, !missing
- [ ] Testy wydajnościowe (czas skanowania, opóźnienia MQTT)
- [ ] Testy bezpieczeństwa (MAC spoofing, autoryzacja Mosquitto)
- [ ] Dokumentacja pisemna (30+ stron)
