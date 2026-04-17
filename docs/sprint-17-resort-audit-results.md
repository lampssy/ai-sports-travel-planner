# Sprint 17 Resort Audit Results

This document records the completed Sprint 17 phase-1 audit for the current 23-resort dataset.
It follows the source policy defined in
[sprint-17-resort-audit-template.md](./sprint-17-resort-audit-template.md).

## Summary

- audited resorts: 23
- factual fields patched in the dataset:
  - area naming cleanup across clearly synthetic placeholders
  - St. Moritz base elevation adjusted to the official town altitude
- season-month corrections: none applied in this pass
- unresolved product questions: 0 blockers for Sprint 17
- realism-test shortlist for phase 2:
  - Ischgl
  - Solden
  - Zermatt
  - Cervinia
  - Tignes
  - St Anton am Arlberg
  - Kitzbuhel

## Audit Results

## Chamonix Mont-Blanc
- resort_id: `chamonix-mont-blanc`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Centre Village`, season=`11-5`, elevation=`1035-3842`
- proposed_verified_values: area=`Chamonix Centre`, season kept, elevations kept
- source_links:
  - official resort source: https://en.chamonix.com/
  - map / geospatial source: https://www.openstreetmap.org/search?query=Chamonix%20Mont-Blanc
  - secondary cross-check: https://www.skiresort.info/ski-resort/chamonixmont-blanc/
- notes: central accommodation anchor renamed to a real town-centre label; broad late-season month kept and handled in phase-2 calibration.

## Val d'Isere
- resort_id: `val-disere`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Front de Neige`, season=`11-5`, elevation=`1850-3456`
- proposed_verified_values: area=`Val d'Isere Centre`, season kept, elevations kept
- source_links:
  - official resort source: https://www.valdisere.com/en/
  - map / geospatial source: https://www.openstreetmap.org/search?query=Val%20d%27Isere
  - secondary cross-check: https://www.skiresort.info/ski-resort/val-disere/
- notes: the app should use a stable village-centre accommodation anchor rather than a piste-front label.

## Tignes
- resort_id: `tignes`
- review_status: `verified`
- confidence: `high`
- current_app_values: area=`Le Lac`, season=`11-5`, elevation=`1550-3456`
- proposed_verified_values: unchanged
- source_links:
  - official resort source: https://en.tignes.net/
  - map / geospatial source: https://www.openstreetmap.org/search?query=Tignes
  - secondary cross-check: https://www.skiresort.info/ski-resort/tignes-val-d-isere/
- notes: `Le Lac` is already a credible resort-area label.

## Les Arcs
- resort_id: `les-arcs`
- review_status: `verified`
- confidence: `high`
- current_app_values: area=`Arc 1800 Village`, season=`12-4`, elevation=`1200-3226`
- proposed_verified_values: unchanged
- source_links:
  - official resort source: https://www.lesarcs.com/en
  - map / geospatial source: https://www.openstreetmap.org/search?query=Les%20Arcs%201800
  - secondary cross-check: https://www.skiresort.info/ski-resort/les-arcsbourg-saint-maurice/
- notes: existing area label is already tied to a real resort village.

## La Plagne
- resort_id: `la-plagne`
- review_status: `verified`
- confidence: `high`
- current_app_values: area=`Plagne Centre`, season=`12-4`, elevation=`1250-3250`
- proposed_verified_values: unchanged
- source_links:
  - official resort source: https://www.la-plagne.com/en
  - map / geospatial source: https://www.openstreetmap.org/search?query=Plagne%20Centre
  - secondary cross-check: https://www.skiresort.info/ski-resort/la-plagne/
- notes: existing area label is credible and central to the resort.

## St Anton am Arlberg
- resort_id: `st-anton-am-arlberg`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Galzig Base`, season=`12-4`, elevation=`1304-2811`
- proposed_verified_values: area=`St Anton Dorf`, season kept, elevations kept
- source_links:
  - official resort source: https://www.stantonamarlberg.com/en
  - map / geospatial source: https://www.openstreetmap.org/search?query=St%20Anton%20am%20Arlberg
  - secondary cross-check: https://www.skiresort.info/ski-resort/st-antonst-christofstubenlechzuerswarthschroecken-ski-arlberg/
- notes: switched from a lift-base label to the real village accommodation anchor.

## Ischgl
- resort_id: `ischgl`
- review_status: `verified_with_adjustment`
- confidence: `high`
- current_app_values: area=`Dorf Core`, season=`11-5`, elevation=`1377-2872`
- proposed_verified_values: area=`Ischgl Dorf`, season kept, elevations kept
- source_links:
  - official resort source: https://www.ischgl.com/en
  - map / geospatial source: https://www.openstreetmap.org/search?query=Ischgl
  - secondary cross-check: https://www.skiresort.info/ski-resort/ischglsilvretta-arena-samnaun/
- notes: area label was clearly synthetic; May season window is plausible but should no longer score optimistically on sparse evidence.

## Solden
- resort_id: `solden`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Giggijoch Quarter`, season=`11-5`, elevation=`1350-3340`
- proposed_verified_values: area=`Solden Zentrum`, season kept, elevations kept
- source_links:
  - official resort source: https://www.soelden.com/en/
  - map / geospatial source: https://www.openstreetmap.org/search?query=S%C3%B6lden
  - secondary cross-check: https://www.skiresort.info/ski-resort/soelden/
- notes: the app should anchor accommodation to the village centre rather than an invented neighborhood label.

## Kitzbuhel
- resort_id: `kitzbuhel`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Hahnenkamm Side`, season=`12-4`, elevation=`800-2000`
- proposed_verified_values: area=`Kitzbuhel Centre`, season kept, elevations kept
- source_links:
  - official resort source: https://www.kitzbuehel.com/en/
  - map / geospatial source: https://www.openstreetmap.org/search?query=Kitzbuhel
  - secondary cross-check: https://www.skiresort.info/ski-resort/kitzski-kitzbuehelkirchberg/
- notes: Hahnenkamm is a mountain/slope anchor, not a stable accommodation-zone label.

## Saalbach Hinterglemm
- resort_id: `saalbach-hinterglemm`
- review_status: `verified`
- confidence: `medium`
- current_app_values: area=`Saalbach Centre`, season=`12-4`, elevation=`1003-2096`
- proposed_verified_values: unchanged
- source_links:
  - official resort source: https://www.saalbach.com/en/winter
  - map / geospatial source: https://www.openstreetmap.org/search?query=Saalbach
  - secondary cross-check: https://www.skiresort.info/ski-resort/skicircus-saalbach-hinterglemm-leogang-fieberbrunn/
- notes: current area naming is already credible.

## Mayrhofen
- resort_id: `mayrhofen`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Penken Base`, season=`12-4`, elevation=`630-2500`
- proposed_verified_values: area=`Mayrhofen Zentrum`, season kept, elevations kept
- source_links:
  - official resort source: https://www.mayrhofen.at/en/stories/winter/
  - map / geospatial source: https://www.openstreetmap.org/search?query=Mayrhofen
  - secondary cross-check: https://www.skiresort.info/ski-resort/mayrhofenmountopolis/
- notes: changed from a lift-base label to the real town accommodation anchor.

## Zermatt
- resort_id: `zermatt`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Matterhorn Village`, season=`11-5`, elevation=`1620-3883`
- proposed_verified_values: area=`Zermatt Centre`, season kept, elevations kept
- source_links:
  - official resort source: https://www.zermatt.ch/en/Skiing
  - map / geospatial source: https://www.openstreetmap.org/search?query=Zermatt
  - secondary cross-check: https://www.skiresort.info/ski-resort/zermattmatterhorn-ski-paradise/
- notes: central accommodation label normalized to the real village name.

## Verbier
- resort_id: `verbier`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Medran Hub`, season=`12-4`, elevation=`1500-3330`
- proposed_verified_values: area=`Medran`, season kept, elevations kept
- source_links:
  - official resort source: https://www.verbier.ch/en
  - map / geospatial source: https://www.openstreetmap.org/search?query=M%C3%A9dran%20Verbier
  - secondary cross-check: https://www.skiresort.info/ski-resort/verbier4-vallees/
- notes: cleaned the area name to the established local spelling without app-internal wording.

## St Moritz
- resort_id: `st-moritz`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Dorf Core`, base=`1772`, summit=`3057`, season=`12-4`
- proposed_verified_values: area=`St. Moritz Dorf`, base=`1856`, summit kept, season kept
- source_links:
  - official resort source: https://www.stmoritz.com/en
  - map / geospatial source: https://www.openstreetmap.org/search?query=St.%20Moritz%20Dorf
  - secondary cross-check: https://www.skiresort.info/ski-resort/st-moritzcorviglia/
- notes: area label corrected to the real village quarter; base elevation aligned to the official resort altitude rather than a lower approximation.

## Davos Klosters
- resort_id: `davos-klosters`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Jakobshorn Base`, season=`12-4`, elevation=`1560-2844`
- proposed_verified_values: area=`Davos Platz`, season kept, elevations kept
- source_links:
  - official resort source: https://www.davos.ch/en
  - map / geospatial source: https://www.openstreetmap.org/search?query=Davos%20Platz
  - secondary cross-check: https://www.skiresort.info/ski-resort/davos-klosters-mountains/
- notes: changed from a mountain-base label to a real accommodation zone.

## Laax
- resort_id: `laax`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Rocksresort Base`, season=`12-4`, elevation=`1100-3018`
- proposed_verified_values: area=`rocksresort`, season kept, elevations kept
- source_links:
  - official resort source: https://www.laax.com/en
  - map / geospatial source: https://www.openstreetmap.org/search?query=rocksresort%20Laax
  - secondary cross-check: https://www.skiresort.info/ski-resort/laaxflimsfalera/
- notes: normalized the casing to the branded lodging zone actually used by the resort.

## Grindelwald Wengen
- resort_id: `grindelwald-wengen`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Terminal Side`, season=`12-4`, elevation=`1034-2500`
- proposed_verified_values: area=`Grindelwald Terminal`, season kept, elevations kept
- source_links:
  - official resort source: https://www.jungfrau.ch/en-gb/grindelwald-wengen/
  - map / geospatial source: https://www.openstreetmap.org/search?query=Grindelwald%20Terminal
  - secondary cross-check: https://www.skiresort.info/ski-resort/grindelwaldwengen-jungfrau/
- notes: renamed to the real transport and accommodation anchor used by the ski area.

## Cortina d'Ampezzo
- resort_id: `cortina-dampezzo`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Corso Italia Stay`, season=`12-4`, elevation=`1224-2930`
- proposed_verified_values: area=`Cortina Centre`, season kept, elevations kept
- source_links:
  - official resort source: https://cortina.dolomiti.org/en
  - map / geospatial source: https://www.openstreetmap.org/search?query=Cortina%20d%27Ampezzo
  - secondary cross-check: https://www.skiresort.info/ski-resort/cortina-dampezzo/
- notes: replaced an app-internal phrasing with the real town-centre anchor.

## Madonna di Campiglio
- resort_id: `madonna-di-campiglio`
- review_status: `verified`
- confidence: `medium`
- current_app_values: area=`Centro Campiglio`, season=`12-4`, elevation=`1550-2504`
- proposed_verified_values: unchanged
- source_links:
  - official resort source: https://www.campigliodolomiti.it/en/ski-area
  - map / geospatial source: https://www.openstreetmap.org/search?query=Madonna%20di%20Campiglio
  - secondary cross-check: https://www.skiresort.info/ski-resort/madonna-di-campiglio/
- notes: current central-area naming is already close enough to real local usage.

## Livigno
- resort_id: `livigno`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Mottolino Side`, season=`11-5`, elevation=`1816-2798`
- proposed_verified_values: area=`Livigno Centro`, season kept, elevations kept
- source_links:
  - official resort source: https://www.livigno.eu/en/winter
  - map / geospatial source: https://www.openstreetmap.org/search?query=Livigno
  - secondary cross-check: https://www.skiresort.info/ski-resort/livigno/
- notes: changed from a ski-area side label to the real town-centre accommodation anchor.

## Val Gardena
- resort_id: `val-gardena`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Ortisei Core`, season=`12-4`, elevation=`1236-2518`
- proposed_verified_values: area=`Ortisei Centre`, season kept, elevations kept
- source_links:
  - official resort source: https://www.valgardena.it/en/winter-holidays-dolomites/ski-holiday/
  - map / geospatial source: https://www.openstreetmap.org/search?query=Ortisei
  - secondary cross-check: https://www.skiresort.info/ski-resort/val-gardena-groeden/
- notes: normalized to the real village name used by the resort.

## Cervinia
- resort_id: `cervinia`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Breuil Base`, season=`11-5`, elevation=`2050-3480`
- proposed_verified_values: area=`Breuil-Cervinia Centre`, season kept, elevations kept
- source_links:
  - official resort source: https://www.cervinia.it/en
  - map / geospatial source: https://www.openstreetmap.org/search?query=Breuil-Cervinia
  - secondary cross-check: https://www.skiresort.info/ski-resort/breuil-cervinia-valtournenche-zermatt-matterhorn-ski-paradise/
- notes: switched to the full official resort-village name used for accommodation searches.

## Alta Badia
- resort_id: `alta-badia`
- review_status: `verified_with_adjustment`
- confidence: `medium`
- current_app_values: area=`Corvara Core`, season=`12-4`, elevation=`1324-2550`
- proposed_verified_values: area=`Corvara`, season kept, elevations kept
- source_links:
  - official resort source: https://www.altabadia.org/en/winter-holidays-dolomites/ski-holiday
  - map / geospatial source: https://www.openstreetmap.org/search?query=Corvara%20Alta%20Badia
  - secondary cross-check: https://www.skiresort.info/ski-resort/alta-badia/
- notes: normalized to the real accommodation village instead of a synthetic label.

## Editorial Fields Intentionally Left Unchanged

The following fields remain product-curated in Sprint 17:
- price levels
- area price ranges
- rental provider choice
- rental price ranges
- quality labels
- lift-distance labels
- supported skill levels at area level

## Unresolved Cases

None block Sprint 17 implementation. The main remaining judgment calls belong to phase 2:
- how conservative late-spring sparse-evidence planning should be for May-close resorts
- whether a future version should explicitly model glacier or snow-sure exceptions
