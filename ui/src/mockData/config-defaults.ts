import type { UniverseParams, CircuitBreakers } from "./types";

export const defaultUniverse: UniverseParams = {
  capMinM: 10, capMaxM: 500, priceFloor: 1, priceCeiling: 25,
  minDollarVolM: 3, minAdvK: 500, lowFloatFlagM: 20,
  maxBorrowFeeSoftPct: 100, maxBorrowFeeHardPct: 300,
};

export const defaultBreakers: CircuitBreakers = {
  perPositionMaxLossPct: 18, dailyDrawdownLimitPct: -4, maxPositions: 6, maxGrossShort: 150000,
};
