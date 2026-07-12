// Response shapes mirrored exactly from docs/CONTRACT.md. Field names are contract-authoritative.

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  role: string;
  department_id: number;
  points_balance: number;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface DashboardSummary {
  esgScore: { total: number; e: number; s: number; g: number; weights: { E: number; S: number; G: number } };
  kpis: { label: string; value: string; delta: string; trend: string }[];
  emissionsTrend: { month: string; scope1: number; scope2: number; scope3: number }[];
  departmentScores: { department: string; period: string; e: number; s: number; g: number; total: number }[];
}

export interface EnvGoal {
  id: number;
  title: string;
  metric: string;
  baseline_value: number;
  target_value: number;
  current_value: number;
  unit: string;
  department_id: number | null;
  start_date: string;
  target_date: string;
  status: string;
}

export interface EmissionFactor {
  id: number;
  activity_type: string;
  unit: string;
  factor_value: number;
  source: string;
  version: number;
  valid_from: string;
  valid_to: string | null;
  uncertainty_pct: number;
}

export interface CarbonTransaction {
  id: number;
  operational_record_id: number;
  emission_factor_id: number;
  factor_value_used: number;
  factor_version_used: number;
  quantity: number;
  co2e_kg: number;
  scope: number;
  data_tier: string;
  uncertainty_pct: number;
  department_id: number;
  occurred_on: string;
}

export interface ProductProfile {
  id: number;
  sku: string;
  name: string;
  embodied_carbon_kg: number;
  recyclable_pct: number;
  water_usage_l: number;
  ethical_score: number;
  certifications: string[];
}

export interface CsrCategory {
  id: number;
  name: string;
  type: "CSR" | "CHALLENGE";
  is_active: boolean;
}

export interface CsrActivity {
  id: number;
  title: string;
  category_id: number;
  department_id: number;
  location: string;
  points_reward: number;
  capacity: number;
  start_date: string;
  end_date: string | null;
  status: string;
}

export interface Participation {
  id: number;
  csr_activity_id: number;
  user_id: number;
  proof_url: string | null;
  status: string;
  hours: number | null;
  verified_by: number | null;
}

export interface Policy {
  id: number;
  title: string;
  version: number;
  category: string;
  is_mandatory: boolean;
  effective_date: string;
}

export interface Audit {
  id: number;
  title: string;
  framework: string;
  status: string;
  auditor_user_id: number;
  period_start: string;
  period_end: string;
  scheduled_date: string;
}

export interface ComplianceIssue {
  id: number;
  audit_id: number;
  title: string;
  severity: string;
  status: string;
  owner_user_id: number;
  due_date: string;
  resolved_at: string | null;
}

export interface LedgerEntry {
  seq: number;
  entry_type: string;
  ref_table: string;
  ref_id: number;
  prev_hash: string;
  row_hash: string;
  actor_user_id: number;
  created_at: string;
}

export interface LedgerVerify {
  valid: boolean;
  entries: number;
  broken_at_seq: number | null;
}

export interface Challenge {
  id: number;
  title: string;
  category_id: number;
  lifecycle: string;
  goal_metric: string;
  goal_target: number;
  points_reward: number;
  badge_id: number | null;
  start_date: string;
  end_date: string;
}

export interface Badge {
  id: number;
  name: string;
  description: string;
  icon: string;
  tier: string;
  unlock_rule: unknown;
  points_value: number;
  is_active: boolean;
}

export interface Reward {
  id: number;
  name: string;
  description: string;
  cost_points: number;
  stock: number;
  is_active: boolean;
}

export interface Redemption {
  id: number;
  user_id: number;
  reward_id: number;
  points_spent: number;
  status: string;
  created_at: string;
}

export interface LeaderboardRow {
  rank: number;
  user_id: number;
  user: string;
  department: string;
  points: number;
}

export interface ReportAvailable {
  id: string;
  name: string;
  formats: string[];
}

export interface RecentReport {
  id: number;
  name: string;
  format: string;
  generated_at: string;
  size_kb: number;
}

export interface Department {
  id: number;
  name: string;
  code: string;
  parent_id: number | null;
  manager_id: number | null;
}

export interface PlatformSettings {
  id: number;
  gamification_enabled: boolean;
  csr_module_enabled: boolean;
  notifications_enabled: boolean;
  public_leaderboard: boolean;
  esg_weights: { E: number; S: number; G: number };
  updated_at: string;
}

export interface NotificationItem {
  id: number;
  user_id: number;
  title: string;
  body: string;
  type: string;
  link: string | null;
  is_read: boolean;
  created_at: string;
}
