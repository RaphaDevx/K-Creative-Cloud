# 03 — Musik, Stems und Audio-Plugins

## Bestand und Ziel

LMMS-Projekt-/Renderadapter, eigene Notenoberfläche und `K-DAW/backend/stems_daemon.py`/`scripts/stems_batch.sh` sind vorhanden; deren Verfügbarkeit, Qualität und Geräteverhalten vor Wiederverwendung prüfen. Keine neue Doppelimplementierung ohne Bestandsvergleich.

Spuren zerlegen bedeutet zwei Funktionen: vorhandene Mehrspurdateien/Stems getrennt importieren und einen fertigen Mix per Source-Separation in angenäherte Stems zerlegen. Letzteres ist nicht verlustfrei; Original erhalten, Modell/Version, Lizenz, Einstellungen und Jobherkunft speichern. Ziel zunächst Vocals/Drums/Bass/Rest mit ausgerichteten Startpunkten und überprüfter Dauer.

## Engine und Plugin-Vertrag

- Eingebaute Grundausstattung: Instrument/Sampler, Gain/Pan, EQ, Kompressor, Delay, Reverb und Limiter; deterministische Presets und fehlende Plugins anzeigen.
- Echtzeit-Audio von KI/Dateizugriff/Logs trennen: keine Netzwerkaufrufe, unbeschränkten Allokationen oder blockierenden Sperren im Audio-Callback.
- Desktop: VST3 priorisieren; LV2/CLAP/AU nach Bedarf und Referenzplugins. Kauf allein garantiert keine Plattform-/CPU-Kompatibilität: macOS-Plugin läuft nicht automatisch unter Linux; Herstelleraktivierung und eigene Lizenz bleiben erforderlich.
- Plugin-Scanner und soweit praktikabel Worker isolieren; Abstürze und Hänger abfangen. Zustandsblöcke, Parameterautomation, Buslayouts, MIDI, Latenzausgleich und Offline-Rendering gehören zum Hostumfang.
- iPad: AUv3 und eingebaute Effekte. Keine Zusage, beliebige Desktop-VST-Binaries zu laden. Fehlendes Plugin als erhaltenen Zustand plus eingefrorenen Audiostem übertragen.

## Abnahmen

Neustart erhält Pluginzustand und Automation; Pluginabsturz zerstört Projekt nicht; Tempo-/Taktwechsel musikalisch korrekt; Stems samplegenau ausgerichtet; Musikrevision aktualisiert verknüpftes Video erst nach gewählter Update-Regel. CPU-/Latenzbudget auf Zielhardware messen. P0 implementiert keinen Pluginhost.
