import { useNavigate } from "react-router-dom";
import { dashboardMock } from "../mock/mockData";
import EmissionsTrendChart from "../components/EmissionsTrendChart";
import DeptRankingBars from "../components/DeptRankingBars";

const ACTIVITY_ICON: Record<string, string> = {
  CARBON: "🌱",
  SOCIAL: "🤝",
  GOVERNANCE: "⚖️",
  GAMIFICATION: "🏆",
  COMPLIANCE: "⚠️",
};

export default function Dashboard() {
  const { esgScore, kpis, emissionsTrend, departmentScores, recentActivity } = dashboardMock;
  const navigate = useNavigate();

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Company-wide ESG performance at a glance.</p>
      </div>

      <div className="score-card-grid">
        <div className="score-card score-card--e">
          <div className="score-card-label">Environmental</div>
          <div className="score-card-value">
            {esgScore.e}
            <span className="score-card-max">/100</span>
          </div>
        </div>
        <div className="score-card score-card--s">
          <div className="score-card-label">Social</div>
          <div className="score-card-value">
            {esgScore.s}
            <span className="score-card-max">/100</span>
          </div>
        </div>
        <div className="score-card score-card--g">
          <div className="score-card-label">Governance</div>
          <div className="score-card-value">
            {esgScore.g}
            <span className="score-card-max">/100</span>
          </div>
        </div>
        <div className="score-card score-card--overall">
          <div className="score-card-label">Overall ESG Score</div>
          <div className="score-card-value">
            {esgScore.total}
            <span className="score-card-max">/100</span>
          </div>
        </div>
      </div>

      <div className="stat-grid">
        {kpis.map((kpi) => (
          <div className="stat-card" key={kpi.label}>
            <div className="stat-label">{kpi.label}</div>
            <div className="stat-value">
              {kpi.value}
              {"uncertaintyPct" in kpi && kpi.uncertaintyPct !== undefined && (
                <span className="uncertainty-badge">± {kpi.uncertaintyPct}%</span>
              )}
            </div>
            <div className={"stat-delta stat-delta--" + kpi.trend}>{kpi.delta}</div>
          </div>
        ))}
      </div>

      <div className="dashboard-grid">
        <div className="card">
          <h2>Emissions Trend (tCO2e)</h2>
          <EmissionsTrendChart data={emissionsTrend} />
        </div>

        <div className="card">
          <h2>Department ESG Ranking</h2>
          <DeptRankingBars data={departmentScores} />
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="card">
          <h2>Recent Activity</h2>
          <ul className="activity-feed">
            {recentActivity.map((item) => (
              <li className="activity-item" key={item.id}>
                <span className="activity-icon">{ACTIVITY_ICON[item.type] ?? "•"}</span>
                <span className="activity-text">{item.text}</span>
                <span className="activity-when">{item.when}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="card">
          <h2>Quick Actions</h2>
          <div className="quick-actions">
            <button className="btn btn-quick btn-quick--e" onClick={() => navigate("/environmental")}>
              🌱 Log Emission
            </button>
            <button className="btn btn-quick btn-quick--gamification" onClick={() => navigate("/gamification")}>
              🏆 Join Challenge
            </button>
            <button className="btn btn-quick btn-quick--neutral" onClick={() => navigate("/reports")}>
              📑 Generate Report
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
