import type { CatalogTrustStatus } from "../types";

export const snowRiskSignal = {
  title: "April is risky below 1,800m",
  body: "Use archive snow evidence before you commit.",
};

export const initialHeroCopy = {
  heading: "Book the mountain, not the guesswork.",
  body:
    "Tell Snowcast what matters for your ski trip. Snowcast compares trip options using snow fit for your dates, where to stay, travel effort, and evidence.",
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

export const catalogTrustStatusCopy = {
  verified: {
    primary: "Based on source data",
    technical: "Based on source data.",
  },
  verified_with_adjustment: {
    primary: "Estimated from source data for this trip",
    technical: "Estimated from source data for this trip option.",
  },
  estimated: {
    primary: "Estimated from available data",
    technical: "Estimated from available catalog data.",
  },
  needs_source: {
    primary: "Source confirmation needed",
    technical: "Source confirmation is still needed.",
  },
} as const satisfies Record<
  CatalogTrustStatus,
  { primary: string; technical: string }
>;
