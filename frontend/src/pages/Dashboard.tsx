import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import EmissionsTrendChart from "../components/EmissionsTrendChart";
import DeptRankingBars from "../components/DeptRankingBars";
import ApiStateView from "../components/ApiStateView";
import { useApi } from "../hooks/useApi";
import { useNotificationsStream } from "../hooks/useNotificationsStream";
import { DashboardApi, GamificationApi, GovernanceApi } from "../api/endpoints";
import type { Badge, LedgerEntry, Policy } from "../api/types";

const LEDGER_ICON: Record<string, string> = {
  CARBON: "🌱",
  POINTS: "⚡",
  BADGE: "🏅",
  POLICY: "⚖️",
  AUDIT: "⚠️",
};

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function asString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number") return value;
  if (typeof value === "string" && value.trim() !== "" && !Number.isNaN(Number(value))) return Number(value);
  return null;
}

// Turns a raw ledger row (entry_type + payload) into a human sentence for the
// Recent Activity feed. Payload shapes come from the services that append each
// entry type (services/ledger.py callers) — see the field access below for what
// each entry_type actually carries.
function humanizeLedgerEntry(entry: LedgerEntry, badgesById: Map<number, Badge>, policiesById: Map<number, Policy>): string {
  const p = entry.payload ?? {};
  switch (entry.entry_type) {
    case "CARBON": {
      const activity = asString(p.activity_type) ?? "Activity";
      const co2e = asNumber(p.co2e_kg);
      return co2e !== null ? `${activity} logged — ${Math.round(co2e).toLocaleString()} kg CO₂e` : `${activity} logged`;
    }
    case "POINTS": {
      const reason = asString(p.reason) ?? "Points adjustment";
      const delta = asNumber(p.delta);
      if (delta === null) return reason;
      return delta >= 0 ? `${reason} (+${delta} pts)` : `${reason} (${delta} pts)`;
    }
    case "BADGE": {
      const badgeId = asNumber(p.badge_id);
      const name = badgeId !== null ? badgesById.get(badgeId)?.name : undefined;
      return `Badge unlocked: ${name ?? (badgeId !== null ? `#${badgeId}` : "unknown")}`;
    }
    case "POLICY": {
      const policyId = asNumber(p.policy_id);
      const title = policyId !== null ? policiesById.get(policyId)?.title : undefined;
      return `Policy acknowledged: ${title ?? (policyId !== null ? `#${policyId}` : "unknown")}`;
    }
    case "AUDIT": {
      const issueId = asNumber(p.issue_id);
      const newStatus = asString(p.new_status);
      const oldStatus = asString(p.old_status);
      if (newStatus) {
        return `Compliance issue #${issueId} status: ${oldStatus ?? "?"} → ${newStatus}`;
      }
      const severity = asString(p.severity);
      return `Compliance issue raised${severity ? ` (${severity})` : ""}`;
    }
    default:
      return `${entry.entry_type} entry recorded`;
  }
}

export default function Dashboard() {
  const navigate = useNavigate();
  const summary = useApi(() => DashboardApi.summary(), []);
  const ledgerFeed = useApi(() => GovernanceApi.ledger(8), []);
  const badges = useApi(() => GamificationApi.badges(), []);
  const policies = useApi(() => GovernanceApi.policies(), []);

  const [flash, setFlash] = useState(false);
  const flashTimeout = useRef<number | undefined>(undefined);

  // Ticks the dashboard live: any inbound SSE event (carbon.created / score.updated)
  // refetches the summary + recent ledger feed and flashes the live badge green.
  const streamStatus = useNotificationsStream(() => {
    summary.refetch();
    ledgerFeed.refetch();
    setFlash(true);
    window.clearTimeout(flashTimeout.current);
    flashTimeout.current = window.setTimeout(() => setFlash(false), 1200);
  });

  useEffect(() => () => window.clearTimeout(flashTimeout.current), []);

  const badgesById = new Map((badges.status === "success" ? badges.data : []).map((b) => [b.id, b]));
  const policiesById = new Map((policies.status === "success" ? policies.data : []).map((p) => [p.id, p]));

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>
          Company-wide ESG performance at a glance.{" "}
          <span className={"uncertainty-badge live-indicator" + (flash ? " live-indicator--flash" : "")}>
            live updates:{" "}
            {streamStatus === "open" ? "🟢 connected" : streamStatus === "connecting" ? "🟡 connecting…" : "⚪ unavailable"}
          </span>
        </p>
      </div>

      {summary.status === "loading" && <p className="uncertainty-badge">Loading dashboard…</p>}

      {summary.status === "error" && (
        <div className="card api-error">
          <span>⚠ {summary.error}</span>
          <button type="button" className="chip-btn" onClick={summary.refetch}>
            Retry
          </button>
        </div>
      )}

      {summary.status === "success" && (
        <>
          <div className="score-card-grid">
            <div className="score-card score-card--e">
              <div className="score-card-label">Environmental</div>
              <div className="score-card-value">
                {summary.data.esgScore.e}
                <span className="score-card-max">/100</span>
              </div>
            </div>
            <div className="score-card score-card--s">
              <div className="score-card-label">Social</div>
              <div className="score-card-value">
                {summary.data.esgScore.s}
                <span className="score-card-max">/100</span>
              </div>
            </div>
            <div className="score-card score-card--g">
              <div className="score-card-label">Governance</div>
              <div className="score-card-value">
                {summary.data.esgScore.g}
                <span className="score-card-max">/100</span>
              </div>
            </div>
            <div className="score-card score-card--overall">
              <div className="score-card-label">Overall ESG Score</div>
              <div className="score-card-value">
                {summary.data.esgScore.total}
                <span className="score-card-max">/100</span>
              </div>
            </div>
          </div>

          <div className="stat-grid">
            {summary.data.kpis.map((kpi) => (
              <div className="stat-card" key={kpi.label}>
                <div className="stat-label">{kpi.label}</div>
                <div className="stat-value">{kpi.value}</div>
                <div className={"stat-delta stat-delta--" + kpi.trend}>{kpi.delta}</div>
              </div>
            ))}
          </div>

          <div className="dashboard-grid">
            <div className="card">
              <h2>Emissions Trend (tCO2e)</h2>
              <EmissionsTrendChart data={summary.data.emissionsTrend} />
            </div>

            <div className="card">
              <h2>Department ESG Ranking</h2>
              <DeptRankingBars data={summary.data.departmentScores} />
            </div>
          </div>
        </>
      )}

      <div className="dashboard-grid">
        <div className="card">
          <h2>Recent Activity</h2>
          <ApiStateView state={ledgerFeed}>
            {(entries) =>
              entries.length === 0 ? (
                <p className="uncertainty-badge">No ledger activity yet.</p>
              ) : (
                <ul className="activity-feed">
                  {entries.map((entry) => (
                    <li className="activity-item" key={entry.seq}>
                      <span className="activity-icon">{LEDGER_ICON[entry.entry_type] ?? "•"}</span>
                      <span className="activity-text">{humanizeLedgerEntry(entry, badgesById, policiesById)}</span>
                      <span className="activity-when">{timeAgo(entry.created_at)}</span>
                    </li>
                  ))}
                </ul>
              )
            }
          </ApiStateView>
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
