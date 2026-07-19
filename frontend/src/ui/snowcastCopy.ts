export const snowRiskSignal = {
  title: "April is risky below 1,800m",
  body: "Use archive snow evidence before you commit.",
};

export const initialHeroCopy = {
  heading: "Book the mountain, not the guesswork.",
  body:
    "Search by trip intent. Snowcast ranks ski resorts by snow window, stay fit, travel effort, and evidence.",
};

export const evidenceQualityCopy = {
  archiveBacked: {
    label: "Archive-backed",
    description: "Historical seasons support this travel window.",
  },
  forecastAssisted: {
    label: "Forecast-assisted",
    description: "Current forecast supports the recommendation.",
  },
  fallbackHeavy: {
    label: "Limited evidence",
    description: "Some parts of this recommendation rely on limited data.",
  },
} as const;

export type EvidenceQualityMode = keyof typeof evidenceQualityCopy;
