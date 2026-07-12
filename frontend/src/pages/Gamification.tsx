import { useState } from "react";
import { gamificationMock } from "../mock/mockData";
import Tabs from "../components/Tabs";
import ProgressBar from "../components/ProgressBar";
import { pillClass } from "../statusColors";
import { getSessionUser } from "../auth";

const RANK_MEDAL: Record<number, string> = { 1: "🥇", 2: "🥈", 3: "🥉" };

function ChallengesTab() {
  return (
    <div className="challenge-card-grid">
      {gamificationMock.challenges.map((c) => (
        <div className="challenge-card" key={c.id}>
          <div className="challenge-card-top">
            <span className={pillClass(c.lifecycle)}>{c.lifecycle}</span>
            <span className="pill pill--neutral">{c.difficulty}</span>
          </div>
          <h3 className="activity-card-title">{c.title}</h3>
          <div className="challenge-card-stats">
            <div className="challenge-stat">
              <span className="challenge-stat-label">XP Reward</span>
              <span className="challenge-stat-value">⚡ {c.points_reward}</span>
            </div>
            <div className="challenge-stat">
              <span className="challenge-stat-label">Deadline</span>
              <span className="challenge-stat-value">{c.end_date}</span>
            </div>
          </div>
          <ProgressBar pct={(c.progress / c.goal_target) * 100} colorVar="var(--pillar-gamification)" />
          <span className="activity-card-progress-label">
            {c.progress.toLocaleString()} / {c.goal_target.toLocaleString()} {c.goal_metric}
          </span>
        </div>
      ))}
    </div>
  );
}

function ParticipationTab() {
  return (
    <div className="card">
      <h2>Challenge Participation</h2>
      <table>
        <thead>
          <tr>
            <th>Challenge</th>
            <th>Employee</th>
            <th>Progress</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {gamificationMock.participation.map((p) => (
            <tr key={p.id}>
              <td>{p.challenge}</td>
              <td>{p.user}</td>
              <td style={{ minWidth: 160 }}>
                <ProgressBar pct={(p.progress / p.goal_target) * 100} colorVar="var(--pillar-gamification)" />
                <span className="activity-card-progress-label">
                  {p.progress.toLocaleString()} / {p.goal_target.toLocaleString()}
                </span>
              </td>
              <td>
                <span className={pillClass(p.status)}>{p.status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BadgesTab() {
  return (
    <div className="badge-gallery">
      {gamificationMock.badges.map((b) => (
        <div className={"badge-card" + (b.unlocked ? "" : " badge-card--locked")} key={b.id}>
          <div className={"badge-card-icon badge-card-icon--" + b.tier.toLowerCase()}>
            {b.unlocked ? "🏅" : "🔒"}
          </div>
          <div className="badge-card-name">{b.name}</div>
          <span className={"pill badge-card-tier badge-card-tier--" + b.tier.toLowerCase()}>{b.tier}</span>
          <div className="uncertainty-badge">{b.points_value} pts</div>
        </div>
      ))}
    </div>
  );
}

function RewardsTab() {
  const [rewards, setRewards] = useState(gamificationMock.rewards);
  const [redeemedIds, setRedeemedIds] = useState<Set<number>>(new Set());
  const balance = getSessionUser()?.points_balance ?? 0;

  function redeem(id: number, cost: number) {
    if (cost > balance) return;
    setRewards((prev) => prev.map((r) => (r.id === id && r.stock > 0 ? { ...r, stock: r.stock - 1 } : r)));
    setRedeemedIds((prev) => new Set(prev).add(id));
  }

  return (
    <div className="card">
      <h2>Rewards Store</h2>
      <p className="uncertainty-badge">Your balance: {balance.toLocaleString()} pts</p>
      <table>
        <thead>
          <tr>
            <th>Reward</th>
            <th>Cost</th>
            <th>Stock</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {rewards.map((r) => {
            const outOfStock = r.stock <= 0;
            const tooExpensive = r.cost_points > balance;
            const alreadyRedeemed = redeemedIds.has(r.id);
            return (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td>{r.cost_points} pts</td>
                <td>
                  {outOfStock ? <span className={pillClass("OUT_OF_STOCK")}>Out of stock</span> : r.stock}
                </td>
                <td>
                  <button
                    type="button"
                    className="btn btn-quick btn-quick--gamification"
                    disabled={outOfStock || tooExpensive}
                    onClick={() => redeem(r.id, r.cost_points)}
                  >
                    {alreadyRedeemed ? "✓ Redeemed" : outOfStock ? "Unavailable" : "Redeem"}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function LeaderboardTab() {
  return (
    <div className="card">
      <h2>Leaderboard</h2>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Employee</th>
            <th>Department</th>
            <th>Points</th>
          </tr>
        </thead>
        <tbody>
          {gamificationMock.leaderboard.map((row) => (
            <tr key={row.rank}>
              <td>{RANK_MEDAL[row.rank] ?? row.rank}</td>
              <td>{row.user}</td>
              <td>{row.department}</td>
              <td>{row.points.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Gamification() {
  return (
    <div>
      <div className="page-header">
        <h1>Gamification</h1>
        <p>Challenges, leaderboard, badges, and the rewards store.</p>
      </div>

      <Tabs
        items={[
          { key: "challenges", label: "Challenges", content: <ChallengesTab /> },
          { key: "participation", label: "Participation", content: <ParticipationTab /> },
          { key: "badges", label: "Badges", content: <BadgesTab /> },
          { key: "rewards", label: "Rewards", content: <RewardsTab /> },
          { key: "leaderboard", label: "Leaderboard", content: <LeaderboardTab /> },
        ]}
      />
    </div>
  );
}
