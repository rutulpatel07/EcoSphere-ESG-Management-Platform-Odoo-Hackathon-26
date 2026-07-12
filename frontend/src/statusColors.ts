// Maps the various status/lifecycle enums used across pages to a consistent pill color.
const SUCCESS = new Set(["ON_TRACK", "OPEN", "VERIFIED", "ACTIVE", "COMPLETED", "APPROVED", "MEASURED"]);
const WARNING = new Set(["AT_RISK", "UNDERREVIEW", "REGISTERED", "IN_PROGRESS", "PENDING", "CALCULATED"]);
const DANGER = new Set(["OFF_TRACK", "REJECTED", "HIGH", "OUT_OF_STOCK"]);
const NEUTRAL = new Set(["FULL", "CLOSED", "DRAFT", "ARCHIVED", "ESTIMATED", "DEFAULT"]);

export function pillClass(status: string): string {
  const key = status.toUpperCase().replace(/\s+/g, "");
  if (SUCCESS.has(key)) return "pill pill--success";
  if (WARNING.has(key)) return "pill pill--warning";
  if (DANGER.has(key)) return "pill pill--danger";
  if (NEUTRAL.has(key)) return "pill pill--neutral";
  return "pill";
}
