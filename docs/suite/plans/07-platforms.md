# 07 — Desktop, iPad, Konto und Distribution

## Produktform

Ein Workspace mit Fachmodulen, getrennten App-Einstiegen und optionalem Suite-Fenster. Gemeinsame Dokumentverträge, Gestaltungsgrundlagen und SDKs; Fachoberflächen bleiben individuell. Bestehenden Electron/Web-Desktop zunächst erhalten. Tauri/Rust-Shell erst nach Host-/Plugin-/Accessibility-Spike entscheiden, keine sofortige Neuentwicklung aller Oberflächen.

iPad zuerst klar begrenzter Touch-/Pencil-Client für Sketch, Foto, Notes und ausgewählte Musik-/Timeline-Aktionen. Gemeinsame Rust-Logik über geeignete Bindings/WASM evaluieren. Desktop-Blender, FreeCAD und native VSTs lassen sich nicht einfach als iPad-Binaries übernehmen. Schwere Jobs können optional auf eigenem Desktop/Server laufen; Offline-Modus muss verbleibende Fähigkeiten sichtbar machen. Mobile-native Audio/AUv3 braucht eigene Plattformintegration.

## Konto und Zugriff

- Google Sign-In und Sign in with Apple münden in interne stabile Account-ID; E-Mail ist kein primärer Identifikator. Pro App separate Client-Konfiguration und eng begrenzte Tokens, gemeinsamer serverseitiger Nutzer.
- Account-Verknüpfung nur über nachgewiesenen Besitz beider Identitäten; private Apple-Relay-Adresse nicht blind mit gleicher/ähnlicher E-Mail zusammenlegen.
- OAuth/OIDC mit Systembrowser, State/Nonce, PKCE wo passend, registrierten Redirects/Universal Links und Prüfung von Issuer/Audience/Signatur. Credentials in Keychain/OS-Keystore, keine eingebetteten Client-Secrets.
- Login allein ist keine Synchronisation und keine Autorisierung. Dokument-/Projektrollen, Besitzer, Einladungen und Gerätewiderruf serverseitig prüfen; Actor-ID im Journal aus authentifizierter Sitzung ableiten.
- Lokale Projekte ohne Login; Cloud optional. Kontolöschung, Datenexport und Aufbewahrung geteilter Inhalte als getrennte Produktfälle planen.

## Freigaben und Abnahmen

Google-/Apple-Provider brauchen registrierte App-IDs, Domains und Umgebung; diese Sitzung konfiguriert keine fremden Konten. Jede Plattform bekommt getestete Capability-Matrix. Desktop-Keychain, echtes iPad/Pencil, Audio, Dateiauswahl und Hintergrundverhalten auf Hardware prüfen; Responsive-Web allein belegt keine iPad-App.

Login in zwei Fachapps verbindet denselben Nutzer; widerrufenes Gerät kann nicht weiter synchronisieren; Offline-Änderungen werden mit Konfliktanzeige zusammengeführt. Suite und Einzelpakete öffnen dieselbe Dokumentversion. Builds/Signatur über K-Dev; keine Store-Veröffentlichung in diesem Planungs-/Foundation-Schritt.
