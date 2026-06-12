# Snowcast Review-Aligned UI Concepts

Generated after the external UI/UX review to reflect these changes:

- explicit Destination / Ski area / Stay base hierarchy
- `Trip fit` instead of primary `Confidence`
- `Snow reliability` / `Snow outlook` instead of `Snow signal`
- stronger evidence-quality framework: Archive-backed, Forecast-assisted, Fallback-heavy
- clarifications above rankings when they materially affect recommendation quality
- alpenglow pink reserved for date/window emphasis; amber/orange owns risk

Concept files:

- `01-search-results-board.png`
- `02-selected-result-dossier.png`
- `03-current-trip.png`
- `04-public-resort-guide.png`

These images are visual references only. UI text and controls should be implemented as code-native React/FastAPI-rendered UI, not as image assets.
