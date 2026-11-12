# 01 — Dokumente, Abhängigkeiten und Löschen

## Begriffe

Eine Abhängigkeit zeigt vom **Nutzer** zur **Quelle**: Video → Musik; Extrusion → Sketch. Ein Versionszweig ist davon verschieden. „Alle Zweige löschen“ wird in der Oberfläche deshalb als „Dokument und abhängige Inhalte archivieren“ mit konkreter Vorschau formuliert. Gemeinsame vorgelagerte Quellen werden dabei nicht mitgelöscht.

## Verhalten

- **Nur dieses Dokument entfernen, Verwendungen erhalten:** Für jede direkt verwendende Stelle wird ein lokales Quelldokument mit neuer Identität angelegt, die Verwendung umgehängt und die Herkunft festgehalten. Dessen eigene Quellenverknüpfungen bleiben erhalten. Original danach archivieren, alles atomar und rückgängig machbar.
- **Dokument und abhängige Inhalte archivieren:** Transitive Nutzer vorab auflisten und gemeinsam archivieren. Unabhängige Inhalte und gemeinsam genutzte Eingangsquellen erhalten.
- Niemals zuerst physisch löschen und danach versuchen, Referenzen zu reparieren. Eine geänderte Revision seit der Vorschau erzwingt eine neue Vorschau.
- Später: pro Verwendung zwischen letzter freigegebener Version und aktueller Quelle wählen; Projektgrenzen/ACL berücksichtigen. P0 ist projektlokal und verwendet den aktuellen Manifeststand.

## Speicherung ohne unnötige Kopien

Ziel ist ein content-adressierter Blob-Store: Dokumentkopien verweisen zunächst auf dieselben unveränderlichen Datenblöcke. Eine Änderung erzeugt neue Blöcke; alte Versionen halten ihre Referenzen. „Am Verwendungsort“ beschreibt logische Zugehörigkeit, keine duplizierte 4-GB-Datei.

P0 kopiert nur JSON-Manifeste und lässt enthaltene Datenreferenzen unverändert; es gibt **noch keinen** content-adressierten Medienstore, Hashprüfung oder Garbage Collector. Ein externer mutierbarer Dateipfad garantiert keine dauerhafte Erhaltung seines Inhalts. Vor UI-Freigabe von „einfrieren“ müssen solche Quellen aufgenommen und verifiziert werden.

## Schritte und Abnahmen

1. P0: gerichteter azyklischer Graph, persistierte Manifestkopien, zwei Archivmodi, Vorschau, Revisionsguard, Undo/Redo; Tests mit Kette, gemeinsamem Input, Diamant und altem Projektformat.
2. P1: Blob-Store, Pins, atomare Publikation, Crash-/Wiederanlauftests und Größenlimits; gleiche Quelle benötigt beim ersten Abtrennen keine zweite Medienkopie.
3. P1: Löschdialog zeigt Dokumentnamen, betroffene Nutzer und Speicherwirkung. Abbrechen ändert nichts.
4. P2/P7: Offline-Clients und laufende KI-Jobs; archivierte Ziele werden als Konflikt behandelt. Bereinigung erst nach erreichbaren Referenzen aus Historie, Pins und autorisierten Clients.

Nachweis: Sketch → Extrusion → Render. Sketch alleine archivieren erhält bearbeitbare lokale Sketch-Kopie in Extrusion; Render bleibt verknüpft. Undo stellt exakt die ursprünglichen IDs und Verknüpfungen wieder her.
