# Vy Tåg – Entwicklung, keine Veröffentlichung (10. November 2026)

## Gesichert
- `stable/09`: ursprüngliche 13-Systeme-Quelle, Commit `2554bc57c977ea014538c925c2ba447e1c6f8cd5`.
- `archive/stable09-website`: vollständig reproduzierbares öffentliches 13-Systeme-Website-Paket, erfolgreich archiviert in [Workflow 42812088967](https://github.com/hhhihihihpdwwd/SHLM-TRNST/actions/runs/42812088967).
- Originale 10.407 Fahrten, 61 Gleisgeometrien, vollständige Fotos und Zugmarker dürfen nicht verändert werden.

## Verifizierte Vy-Fahrplandaten
- Schwedisches historisches GTFS: `sweden-20261104.zip`, Referenztage 6.–8. November 2026.
- Betreiber `Vy Tåg`, `agency_id=315`.
- Zehn authentische Zugfahrten der Freitag-/Samstag-/Sonntag-Muster mit den Zügen u. a. 8940, 8946, 8944, 8937, 8943, 8947, 18900, 18935, 18941, 8916.
- Ziele Stockholm, Oslo, Karlstad und Charlottenberg; Wochenendverkehr muss auf entsprechende Wochentage begrenzt sein und darf nicht täglich wiederholt werden.
- [Fahrplan-Audit 42812324775](https://github.com/hhhihihihpdwwd/SHLM-TRNST/actions/runs/42812324775) erfolgreich.

## Entwicklung in `feature/vy-stockholm-oslo-01`
- `scripts/build_vy_candidates.py`, `scripts/append_vy.py`, `scripts/prepare_vy_site.py`.
- Eigener Vy-Filter und -Marker sowie historischer Wochentagskalender.
- `tests/vy-weekend.test.mjs` prüft Vy nur Fr/Sa/So, die 13 alten Filter und unveränderte SJ-Wiederholung.
- [Quellcode-/Regressionstest 42813966376](https://github.com/hhhihihihpdwwd/SHLM-TRNST/actions/runs/42813966376) erfolgreich.

## Veröffentlichungsblocker: vollständige tatsächliche Gleise
- [OSM-Routingtest 42812778432](https://github.com/hhhihihihpdwwd/SHLM-TRNST/actions/runs/42812778432) konnte zunächst mehrere verifizierte Streckenbereiche herunterladen, ist danach an wiederholten externen Overpass 502-/504-Fehlern gescheitert. Es wurde **keine vollständige** Stockholm–Oslo-Route validiert.
- [Alternativer Relations-Audit 42814804038](https://github.com/hhhihihihpdwwd/SHLM-TRNST/actions/runs/42814804038) abgeschlossen, jedoch lieferte die geprüfte Relation 4078008 einen HTTP-422-Fehler, keine nachweislich vollständige OSM-Geometrie.
- Deshalb **kein 14-Systeme-Deploy**; die öffentliche 13-Systeme-Version bleibt unangetastet.

## Nächster notwendiger Schritt
1. OSM-Datenquelle stabilisieren und aus tatsächlichen verbundenen `railway=rail`-Wegknoten die durchgehende Strecke Stockholm–Västerås–Örebro–Hallsberg–Karlstad–Charlottenberg–Kongsvinger–Oslo bauen.
2. Alle authentischen GTFS-Haltestellen chronologisch entlang der verifizierten Gleise projizieren, beide Richtungen und alle aktiven Wochenendfahrten prüfen; keine Luftlinien.
3. Nur echte überprüfte Fahrten hinzufügen; unveränderte STABLE09-Daten byteweise kontrollieren.
4. Lizenziertes echtes Zug-Beispielfoto und neuen freigestellten Mini-3D-Marker prüfen, korrekte Cache-Versionen setzen.
5. Originale 13 Systeme und Vy in echten Chromium-Desktop-/Mobiltests überprüfen.
6. Erst bei allen grünen Tests exakt das getestete Paket deployen, danach die öffentliche Website erneut in Chromium testen.
