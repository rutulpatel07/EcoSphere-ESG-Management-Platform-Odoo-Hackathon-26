// Realistic sample data used to render the UI before the API is wired in.
// Shapes mirror docs/CONTRACT.md response payloads.

export const dashboardMock = {
  esgScore: {
    total: 78.4,
    e: 82.1,
    s: 74.6,
    g: 76.0,
    weights: { E: 40, S: 30, G: 30 },
    footprintUncertaintyPct: 4.8,
  },
  kpis: [
    { label: "Total Emissions (tCO2e)", value: "1,284", delta: "-6.2%", trend: "down", uncertaintyPct: 4.8 },
    { label: "CSR Participation", value: "63%", delta: "+4.1%", trend: "up" },
    { label: "Open Compliance Issues", value: "7", delta: "-2", trend: "down" },
    { label: "Active Challenges", value: "5", delta: "+1", trend: "up" },
  ],
  emissionsTrend: [
    { month: "Feb", scope1: 120, scope2: 210, scope3: 90 },
    { month: "Mar", scope1: 118, scope2: 205, scope3: 95 },
    { month: "Apr", scope1: 112, scope2: 198, scope3: 88 },
    { month: "May", scope1: 108, scope2: 190, scope3: 84 },
    { month: "Jun", scope1: 101, scope2: 182, scope3: 80 },
    { month: "Jul", scope1: 97, scope2: 176, scope3: 78 },
  ],
  departmentScores: [
    { department: "Operations", period: "2026-Q2", e: 71, s: 68, g: 74, total: 71.0 },
    { department: "Manufacturing", period: "2026-Q2", e: 64, s: 70, g: 66, total: 66.4 },
    { department: "Logistics", period: "2026-Q2", e: 59, s: 72, g: 70, total: 66.1 },
    { department: "R&D", period: "2026-Q2", e: 88, s: 80, g: 82, total: 84.0 },
  ],
  recentActivity: [
    { id: 1, type: "CARBON", text: "Logistics logged 1,800 L diesel fleet usage (+4.8t CO2e)", when: "2h ago" },
    { id: 2, type: "SOCIAL", text: "Amara Osei verified for Riverside Cleanup Drive (+150 pts)", when: "5h ago" },
    { id: 3, type: "GOVERNANCE", text: "Anti-Bribery & Corruption Policy v3 acknowledged by 12 employees", when: "1d ago" },
    { id: 4, type: "GAMIFICATION", text: "Bike-to-Work Fortnight passed 3,120 / 5,000 km goal", when: "1d ago" },
    { id: 5, type: "COMPLIANCE", text: "New compliance issue assigned: Missing Scope 3 supplier data", when: "2d ago" },
  ],
};

export const environmentalMock = {
  goals: [
    {
      id: 1,
      title: "Cut Scope 1+2 by 25% vs 2024 baseline",
      metric: "Scope1+2 tCO2e",
      baseline_value: 1710,
      target_value: 1282,
      current_value: 1284,
      unit: "tCO2e",
      status: "ON_TRACK",
      target_date: "2026-12-31",
    },
    {
      id: 2,
      title: "80% renewable electricity",
      metric: "Renewable share",
      baseline_value: 32,
      target_value: 80,
      current_value: 61,
      unit: "%",
      status: "AT_RISK",
      target_date: "2027-06-30",
    },
  ],
  emissionFactors: [
    {
      id: 11,
      activity_type: "grid_electricity_uk",
      unit: "kgCO2e/kWh",
      factor_value: 0.20705,
      source: "DEFRA 2024",
      version: 2,
      valid_from: "2024-01-01",
      valid_to: null,
      uncertainty_pct: 5.0,
    },
    {
      id: 12,
      activity_type: "diesel_fleet",
      unit: "kgCO2e/litre",
      factor_value: 2.6871,
      source: "DEFRA 2024",
      version: 2,
      valid_from: "2024-01-01",
      valid_to: null,
      uncertainty_pct: 3.5,
    },
  ],
  carbonTransactions: [
    {
      id: 501,
      activity_type: "grid_electricity_uk",
      quantity: 42000,
      factor_value_used: 0.20705,
      factor_version_used: 2,
      co2e_kg: 8696.1,
      scope: 2,
      data_tier: "MEASURED",
      uncertainty_pct: 5.0,
      department: "Manufacturing",
      occurred_on: "2026-06-30",
    },
    {
      id: 502,
      activity_type: "diesel_fleet",
      quantity: 1800,
      factor_value_used: 2.6871,
      factor_version_used: 2,
      co2e_kg: 4836.8,
      scope: 1,
      data_tier: "CALCULATED",
      uncertainty_pct: 3.5,
      department: "Logistics",
      occurred_on: "2026-06-28",
    },
  ],
  products: [
    {
      id: 90,
      sku: "ECO-BTL-500",
      name: "rPET Water Bottle 500ml",
      embodied_carbon_kg: 0.084,
      recyclable_pct: 100,
      water_usage_l: 1.4,
      ethical_score: 86,
      certifications: ["B-Corp", "FSC"],
    },
    {
      id: 91,
      sku: "ECO-BOX-M",
      name: "Recycled Shipping Box (M)",
      embodied_carbon_kg: 0.31,
      recyclable_pct: 95,
      water_usage_l: 3.2,
      ethical_score: 79,
      certifications: ["FSC"],
    },
  ],
};

export const socialMock = {
  categories: [
    { id: 1, name: "Community Outreach", type: "CSR", is_active: true },
    { id: 2, name: "Environmental Cleanup", type: "CSR", is_active: true },
    { id: 3, name: "Education & Mentoring", type: "CSR", is_active: true },
  ],
  activities: [
    {
      id: 301,
      title: "Riverside Cleanup Drive",
      category: "Environmental Cleanup",
      location: "Riverside Park",
      points_reward: 150,
      capacity: 40,
      registered: 28,
      start_date: "2026-07-20",
      status: "OPEN",
    },
    {
      id: 302,
      title: "STEM Mentoring @ Lincoln High",
      category: "Education & Mentoring",
      location: "Lincoln High School",
      points_reward: 120,
      capacity: 20,
      registered: 20,
      start_date: "2026-07-25",
      status: "FULL",
    },
  ],
  participation: [
    {
      id: 7001,
      activity: "Riverside Cleanup Drive",
      user: "Amara Osei",
      status: "VERIFIED",
      hours: 4,
      proof_url: "https://files.local/proof/7001.jpg",
    },
    {
      id: 7002,
      activity: "STEM Mentoring @ Lincoln High",
      user: "Diego Marin",
      status: "REGISTERED",
      hours: null,
      proof_url: null,
    },
    {
      id: 7003,
      activity: "Riverside Cleanup Drive",
      user: "Marcus Bell",
      status: "REGISTERED",
      hours: null,
      proof_url: "https://files.local/proof/7003.jpg",
    },
  ],
};

export const governanceMock = {
  policies: [
    {
      id: 40,
      title: "Anti-Bribery & Corruption Policy",
      version: 3,
      category: "Governance",
      is_mandatory: true,
      effective_date: "2026-01-01",
      ack_rate: 0.92,
    },
    {
      id: 41,
      title: "Sustainable Procurement Policy",
      version: 2,
      category: "Environmental",
      is_mandatory: true,
      effective_date: "2026-03-01",
      ack_rate: 0.74,
    },
  ],
  audits: [
    {
      id: 12,
      title: "GRI Annual Assurance 2026",
      framework: "GRI",
      status: "IN_PROGRESS",
      auditor: "Priya Nair",
      period_start: "2026-01-01",
      period_end: "2026-06-30",
      scheduled_date: "2026-08-15",
    },
  ],
  complianceIssues: [
    {
      id: 88,
      title: "Missing Scope 3 supplier data",
      severity: "HIGH",
      status: "OPEN",
      owner: "Priya Nair",
      due_date: "2026-07-31",
    },
    {
      id: 89,
      title: "Two suppliers lack code-of-conduct sign-off",
      severity: "MEDIUM",
      status: "IN_PROGRESS",
      owner: "Marcus Bell",
      due_date: "2026-08-10",
    },
    {
      id: 90,
      title: "Overdue supplier audit sign-off",
      severity: "MEDIUM",
      status: "OPEN",
      owner: "Diego Marin",
      due_date: "2026-06-15",
    },
  ],
  ledger: [
    {
      seq: 10230,
      entry_type: "CARBON",
      ref_table: "carbon_transactions",
      ref_id: 501,
      row_hash: "77aa03bb19ce...0d2",
      prev_hash: "5e1f9c22d048...771",
      created_at: "2026-06-27T09:00:00Z",
    },
    {
      seq: 10231,
      entry_type: "CARBON",
      ref_table: "carbon_transactions",
      ref_id: 502,
      row_hash: "9f2c1a7b4e8d...c31",
      prev_hash: "77aa03bb19ce...0d2",
      created_at: "2026-06-28T14:12:00Z",
    },
    {
      seq: 10232,
      entry_type: "POLICY",
      ref_table: "policy_acknowledgements",
      ref_id: 4412,
      row_hash: "b1d9e4f0a672...aa8",
      prev_hash: "9f2c1a7b4e8d...c31",
      created_at: "2026-06-29T09:03:00Z",
    },
  ],
};

export const gamificationMock = {
  leaderboard: [
    { rank: 1, user: "Amara Osei", department: "R&D", points: 2480 },
    { rank: 2, user: "Diego Marin", department: "Operations", points: 2210 },
    { rank: 3, user: "Lin Zhao", department: "Logistics", points: 1990 },
    { rank: 4, user: "Marcus Bell", department: "Manufacturing", points: 1745 },
  ],
  challenges: [
    {
      id: 601,
      title: "Bike-to-Work Fortnight",
      lifecycle: "Active",
      goal_metric: "commute_km_by_bike",
      goal_target: 5000,
      progress: 3120,
      points_reward: 300,
      difficulty: "Medium",
      end_date: "2026-07-26",
    },
    {
      id: 602,
      title: "Zero-Waste Lunch Week",
      lifecycle: "UnderReview",
      goal_metric: "waste_free_days",
      goal_target: 500,
      progress: 500,
      points_reward: 200,
      difficulty: "Easy",
      end_date: "2026-07-05",
    },
    {
      id: 603,
      title: "Plastic-Free Office Sprint",
      lifecycle: "Draft",
      goal_metric: "single_use_plastic_avoided_kg",
      goal_target: 200,
      progress: 0,
      points_reward: 450,
      difficulty: "Hard",
      end_date: "2026-09-01",
    },
  ],
  participation: [
    { id: 9001, challenge: "Bike-to-Work Fortnight", user: "Amara Osei", progress: 3120, goal_target: 5000, status: "IN_PROGRESS" },
    { id: 9002, challenge: "Zero-Waste Lunch Week", user: "Diego Marin", progress: 500, goal_target: 500, status: "COMPLETED" },
    { id: 9003, challenge: "Bike-to-Work Fortnight", user: "Lin Zhao", progress: 4500, goal_target: 5000, status: "IN_PROGRESS" },
  ],
  badges: [
    { id: 21, name: "Carbon Cutter", tier: "Gold", points_value: 500, unlocked: true },
    { id: 22, name: "Community Hero", tier: "Silver", points_value: 300, unlocked: true },
    { id: 23, name: "Zero-Waste Champ", tier: "Bronze", points_value: 150, unlocked: false },
  ],
  rewards: [
    { id: 31, name: "Reusable Coffee Kit", cost_points: 400, stock: 24 },
    { id: 32, name: "Extra Day Off", cost_points: 2000, stock: 5 },
    { id: 33, name: "Tree Planted in Your Name", cost_points: 250, stock: 999 },
  ],
};

export const reportsMock = {
  available: [
    { id: "esg-summary", name: "ESG Summary Report", formats: ["PDF", "XLSX"] },
    { id: "carbon-inventory", name: "Carbon Inventory (GHG Protocol)", formats: ["XLSX"] },
    { id: "csr-impact", name: "CSR Impact Report", formats: ["PDF"] },
    { id: "compliance-register", name: "Compliance Register", formats: ["PDF", "XLSX"] },
  ],
  recent: [
    {
      id: 5001,
      name: "ESG Summary Report — Q2 2026",
      format: "PDF",
      generated_at: "2026-07-01T10:00:00Z",
      size_kb: 842,
    },
    {
      id: 5002,
      name: "Carbon Inventory — H1 2026",
      format: "XLSX",
      generated_at: "2026-07-02T16:30:00Z",
      size_kb: 213,
    },
  ],
};

export const departmentsMock = [
  { id: 1, name: "Company", code: "ROOT", parent_id: null, manager_id: 1 },
  { id: 2, name: "Operations", code: "OPS", parent_id: 1, manager_id: 3 },
  { id: 3, name: "Manufacturing", code: "MFG", parent_id: 1, manager_id: null },
  { id: 4, name: "R&D", code: "RND", parent_id: 1, manager_id: null },
  { id: 5, name: "Logistics", code: "LOG", parent_id: 2, manager_id: 7 },
];

// Categories are shared between CSR activities (social) and challenges (gamification),
// discriminated by `type` per docs/CONTRACT.md.
export const categoriesMock = [
  ...socialMock.categories,
  { id: 4, name: "Commute & Transport", type: "CHALLENGE", is_active: true },
  { id: 5, name: "Waste Reduction", type: "CHALLENGE", is_active: true },
  { id: 6, name: "Energy Saving", type: "CHALLENGE", is_active: false },
];

export const settingsMock = {
  gamification_enabled: true,
  csr_module_enabled: true,
  notifications_enabled: true,
  public_leaderboard: true,
  esg_weights: { E: 40, S: 30, G: 30 },
  updated_at: "2026-07-10T08:00:00Z",
};

export const notificationsMock = [
  {
    id: 9001,
    title: "New compliance issue assigned",
    body: "Missing Scope 3 supplier data is due 2026-07-31.",
    type: "COMPLIANCE",
    is_read: false,
    created_at: "2026-07-11T12:00:00Z",
  },
  {
    id: 9002,
    title: "Reward redeemed",
    body: "You redeemed Reusable Coffee Kit for 400 points.",
    type: "REWARD",
    is_read: true,
    created_at: "2026-07-09T15:20:00Z",
  },
];

// Demo credentials for local-only auth (no backend call — see docs/CONTRACT.md /auth/login shape).
export const authMock = {
  users: [
    {
      id: 1,
      email: "admin@ecosphere.io",
      password: "admin123",
      full_name: "Ada Admin",
      role: "ADMIN",
      department_id: 1,
      points_balance: 0,
    },
    {
      id: 5,
      email: "amara@ecosphere.io",
      password: "amara123",
      full_name: "Amara Osei",
      role: "EMPLOYEE",
      department_id: 4,
      points_balance: 2480,
    },
  ],
};
