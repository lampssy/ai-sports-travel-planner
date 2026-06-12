# Snowcast Accommodation-Layer UI Concepts

Generated on 2026-06-10 for the updated grouped recommendation and suggested-stay guidelines.

These images are design references, not production UI assets. Keep UI text and controls code-native during implementation.

## Files

- `01-search-results-grouped-accommodation-cues.png` — search result board with grouped destination/ski-area recommendations and accommodation cues only.
- `02-selected-dossier-suggested-stays.png` — selected-result dossier with suggested stays nested under the selected stay base.
- `03-suggested-stays-detail-panel.png` — close-up of provider-backed, stale, and estimate-only lodging evidence states.
- `04-current-trip-accommodation-context.png` — current-trip view showing selected accommodation as optional trip context.

## Design Rules Captured

- Ranking unit can be a full trip option, but the displayed search result remains a grouped recommendation.
- Hotels and apartments do not appear as global search result cards.
- Suggested stays sit under the selected stay base on the detail route.
- Property-level cards require provider/freshness evidence.
- Without provider-backed lodging data, show `Stay-base estimate, not live hotel inventory`.
- Accommodation refines lodging price, booking handoff, and lodging tradeoffs; it does not replace snow, mountain, or stay-base fit.
