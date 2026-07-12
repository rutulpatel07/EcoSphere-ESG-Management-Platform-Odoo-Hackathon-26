// Typed calls against docs/CONTRACT.md. Routes/fields are contract-authoritative — do not rename.
import apiClient from "./client";
import type {
  Audit,
  Badge,
  CarbonTransaction,
  Challenge,
  ComplianceIssue,
  CsrActivity,
  CsrCategory,
  DashboardSummary,
  Department,
  EmissionFactor,
  EnvGoal,
  LeaderboardRow,
  LedgerEntry,
  LedgerVerify,
  LoginResponse,
  NotificationItem,
  Participation,
  PlatformSettings,
  Policy,
  ProductProfile,
  Redemption,
  ReportAvailable,
  RecentReport,
  Reward,
} from "./types";

export const AuthApi = {
  login: (email: string, password: string) =>
    apiClient.post<LoginResponse>("/auth/login", { email, password }).then((r) => r.data),
};

export const DashboardApi = {
  summary: () => apiClient.get<DashboardSummary>("/dashboard/summary").then((r) => r.data),
};

export const EnvironmentalApi = {
  goals: () => apiClient.get<EnvGoal[]>("/environmental/goals").then((r) => r.data),
  emissionFactors: () => apiClient.get<EmissionFactor[]>("/environmental/emission-factors").then((r) => r.data),
  products: () => apiClient.get<ProductProfile[]>("/environmental/products").then((r) => r.data),
  carbonTransactions: () =>
    apiClient.get<CarbonTransaction[]>("/environmental/carbon-transactions").then((r) => r.data),
};

export const SocialApi = {
  categories: () => apiClient.get<CsrCategory[]>("/social/categories").then((r) => r.data),
  activities: () => apiClient.get<CsrActivity[]>("/social/activities").then((r) => r.data),
  participants: (activityId: number) =>
    apiClient.get<Participation[]>(`/social/activities/${activityId}/participants`).then((r) => r.data),
  join: (activityId: number, proofUrl: string) =>
    apiClient.post<Participation>(`/social/activities/${activityId}/join`, { proof_url: proofUrl }).then((r) => r.data),
  updateParticipation: (id: number, patch: { status?: string; hours?: number }) =>
    apiClient.patch<Participation>(`/social/participation/${id}`, patch).then((r) => r.data),
};

export const GovernanceApi = {
  policies: () => apiClient.get<Policy[]>("/governance/policies").then((r) => r.data),
  audits: () => apiClient.get<Audit[]>("/governance/audits").then((r) => r.data),
  complianceIssues: () => apiClient.get<ComplianceIssue[]>("/governance/compliance-issues").then((r) => r.data),
  ledger: () => apiClient.get<LedgerEntry[]>("/governance/ledger").then((r) => r.data),
  ledgerVerify: () => apiClient.get<LedgerVerify>("/governance/ledger/verify").then((r) => r.data),
};

export const GamificationApi = {
  challenges: () => apiClient.get<Challenge[]>("/gamification/challenges").then((r) => r.data),
  leaderboard: () => apiClient.get<LeaderboardRow[]>("/gamification/leaderboard").then((r) => r.data),
  badges: () => apiClient.get<Badge[]>("/gamification/badges").then((r) => r.data),
  rewards: () => apiClient.get<Reward[]>("/gamification/rewards").then((r) => r.data),
  redeem: (rewardId: number) =>
    apiClient.post<Redemption>(`/gamification/rewards/${rewardId}/redeem`).then((r) => r.data),
  joinChallenge: (challengeId: number) => apiClient.post(`/gamification/challenges/${challengeId}/join`).then((r) => r.data),
};

export const ReportsApi = {
  available: () => apiClient.get<ReportAvailable[]>("/reports/available").then((r) => r.data),
  recent: () => apiClient.get<RecentReport[]>("/reports/recent").then((r) => r.data),
  generate: (payload: { report_id: string; format: string; period: string }) =>
    apiClient.post("/reports/generate", payload, { responseType: "blob" }).then((r) => r),
};

export const SettingsApi = {
  get: () => apiClient.get<PlatformSettings>("/settings").then((r) => r.data),
  update: (patch: Partial<Pick<PlatformSettings, "gamification_enabled" | "csr_module_enabled" | "notifications_enabled" | "public_leaderboard" | "esg_weights">>) =>
    apiClient.patch<PlatformSettings>("/settings", patch).then((r) => r.data),
};

export const DepartmentsApi = {
  list: () => apiClient.get<Department[]>("/departments").then((r) => r.data),
};

export const NotificationsApi = {
  list: () => apiClient.get<NotificationItem[]>("/notifications").then((r) => r.data),
  markRead: (id: number) => apiClient.post<{ id: number; is_read: boolean }>(`/notifications/${id}/read`).then((r) => r.data),
};
