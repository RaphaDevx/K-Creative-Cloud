# Primärquellen und Entscheidungsgrenzen

Geprüft am 12. November 2026. Versionen vor konkreter Integration pinnen; diese Quellen belegen Technologien, nicht die Runtime-Verfügbarkeit im aktuellen Projekt.

- Blender Lizenz: https://www.blender.org/about/license/ und https://developer.blender.org/docs/license/ — GPL; Distribution, Addons und eingebetteter Code erfordern Prüfung der konkreten Komponenten. Engine separat erhalten, keinen pauschalen Lizenzschluss aus IPC ziehen.
- Blender Headless: https://docs.blender.org/manual/id/dev/advanced/command_line/arguments.html — Background-Aufrufe; lokale Render-/Addonfähigkeiten gesondert prüfen.
- FreeCAD Import/Export: https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Import_Export_Preferences.md — CAD-/Mesh-Formate und Einstellungen; kein Beleg verlustfreien Featurebaum-Roundtrips.
- VST3 SDK: https://www.steinberg.net/developers/vstsdk/ — aktuelle MIT-Lizenz des SDK; Pluginherstellerlizenzen, Aktivierung und Binärplattform bleiben separat.
- Apple Audio-Host: https://developer.apple.com/documentation/audiotoolbox/incorporating-audio-effects-and-instruments — iOS AUv3-Extensions und Prozessgrenzen.
- Echtzeit-Audio: https://developer.apple.com/documentation/avfaudio/creating-custom-audio-effects — keine Allokationen, Datei-I/O oder Locks im Renderpfad.
- OpenFX: https://openeffects.org/ — Host-/Pluginstandard für visuelle Effekte; jeweilige Hostfähigkeiten testen.
- OpenColorIO: https://opencolorio.org/ — Farbverwaltung für Motion-Picture/VFX/Animation; ersetzt keinen vollständigen ICC-Druckworkflow.
- Unreal Cloth: https://dev.epicgames.com/documentation/fortnite/create-your-clothing-asset-in-unreal-engine-in-unreal-editor-for-fortnite — dokumentierter USD-/Cloth-Dataflow; kein universeller CLO-/Blender-Roundtrip.
- Unreal Versionsänderungen: https://dev.epicgames.com/community/learning/tutorials/Wb2V/unreal-engine-chaos-cloth-updates-5-8 — versionsabhängige Cloth-Importer/Plugins.
- Google Desktop OAuth: https://developers.google.com/identity/protocols/oauth2/native-app — PKCE/registrierte Clients; Google-Konto bedeutet keinen Gmail-Zugriff.
- Native OAuth: https://www.rfc-editor.org/rfc/rfc8252 — Systembrowser und Native-App-Flows.
- Apple Review: https://developer.apple.com/app-store/review/guidelines/ — Login-/Plugin-/Kontolöschungsanforderungen vor Einreichung erneut prüfen.
- Collaboration-Kandidaten: https://github.com/loro-dev/loro und https://automerge.org/docs/reference/documents/conflicts/ — strukturierte Konvergenz; fachliche Konfliktregeln bleiben eigene Aufgabe.
