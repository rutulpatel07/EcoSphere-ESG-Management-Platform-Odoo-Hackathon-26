import { useState } from "react";
import Tabs from "../components/Tabs";
import ApiStateView from "../components/ApiStateView";
import { pillClass } from "../statusColors";
import { useApi } from "../hooks/useApi";
import { GamificationApi } from "../api/endpoints";
import apiClient from "../api/client";
import type { Badge } from "../api/types";
import { getSessionUser } from "../auth";

const RANK_MEDAL: Record<number, string> = { 1: "🥇", 2: "🥈", 3: "🥉" };

function ChallengesTab() {
  const challenges = useApi(() => GamificationApi.challenges(), []);
  return (
    <ApiStateView state={challenges}>
      {(data) => (
        <div className="challenge-card-grid">
          {data.map((c) => (
            <div className="challenge-card" key={c.id}>
              <div className="challenge-card-top">
                <span className={pillClass(c.lifecycle)}>{c.lifecycle}</span>
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
              <span className="activity-card-progress-label">Goal: {c.goal_target.toLocaleString()} {c.goal_metric}</span>
            </div>
          ))}
        </div>
      )}
    </ApiStateView>
  );
}

function ParticipationTab() {
  return (
    <div className="card">
      <h2>Challenge Participation</h2>
      <p className="uncertainty-badge">
        docs/CONTRACT.md defines no endpoint to list challenge participation records — only{" "}
        <code className="hash-value">POST /gamification/challenges/&#123;id&#125;/join</code> and{" "}
        <code className="hash-value">PATCH /gamification/challenge-participation/&#123;id&#125;</code> by a known id exist.
        This tab cannot be populated from a live source until a list endpoint is added (see wiring report).
      </p>
    </div>
  );
}

function BadgesTab() {
  const allBadges = useApi(() => GamificationApi.badges(), []);
  const user = getSessionUser();
  const userBadges = useApi(
    () => (user ? apiClient.get<Badge[]>(`/gamification/users/${user.id}/badges`).then((r) => r.data) : Promise.resolve([])),
    [user?.id]
  );

  return (
    <ApiStateView state={allBadges}>
      {(badges) => {
        const unlockedIds = new Set(userBadges.status === "success" ? userBadges.data.map((b) => b.id) : []);
        return (
          <div className="badge-gallery">
            {badges.map((b) => {
              const unlocked = unlockedIds.has(b.id);
              return (
                <div className={"badge-card" + (unlocked ? "" : " badge-card--locked")} key={b.id}>
                  <div className={"badge-card-icon badge-card-icon--" + b.tier.toLowerCase()}>{unlocked ? "🏅" : "🔒"}</div>
                  <div className="badge-card-name">{b.name}</div>
                  <span className={"pill badge-card-tier badge-card-tier--" + b.tier.toLowerCase()}>{b.tier}</span>
                  <div className="uncertainty-badge">{b.points_value} pts</div>
                </div>
              );
            })}
            {userBadges.status === "error" && (
              <p className="uncertainty-badge">Could not load your unlocked badges: {userBadges.error}</p>
            )}
          </div>
        );
      }}
    </ApiStateView>
  );
}

function RewardsTab() {
  const rewards = useApi(() => GamificationApi.rewards(), []);
  const [redeemState, setRedeemState] = useState<Record<number, "idle" | "redeeming" | "done" | "error">>({});
  const balance = getSessionUser()?.points_balance ?? 0;

  function redeem(id: number) {
    setRedeemState((prev) => ({ ...prev, [id]: "redeeming" }));
    GamificationApi.redeem(id).then(
      () => {
        setRedeemState((prev) => ({ ...prev, [id]: "done" }));
        rewards.refetch();
      },
      () => setRedeemState((prev) => ({ ...prev, [id]: "error" }))
    );
  }

  return (
    <div className="card">
      <h2>Rewards Store</h2>
      <p className="uncertainty-badge">Your balance: {balance.toLocaleString()} pts</p>
      <ApiStateView state={rewards}>
        {(data) => (
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
              {data.map((r) => {
                const outOfStock = r.stock <= 0;
                const tooExpensive = r.cost_points > balance;
                const rState = redeemState[r.id] ?? "idle";
                return (
                  <tr key={r.id}>
                    <td>{r.name}</td>
                    <td>{r.cost_points} pts</td>
                    <td>{outOfStock ? <span className={pillClass("OUT_OF_STOCK")}>Out of stock</span> : r.stock}</td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-quick btn-quick--gamification"
                        disabled={outOfStock || tooExpensive || rState === "redeeming"}
                        onClick={() => redeem(r.id)}
                      >
                        {rState === "done" ? "✓ Redeemed" : rState === "redeeming" ? "Redeeming…" : rState === "error" ? "Failed — retry" : outOfStock ? "Unavailable" : "Redeem"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </ApiStateView>
    </div>
  );
}

function LeaderboardTab() {
  const leaderboard = useApi(() => GamificationApi.leaderboard(), []);
  return (
    <div className="card">
      <h2>Leaderboard</h2>
      <ApiStateView state={leaderboard}>
        {(data) => (
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
              {data.map((row) => (
                <tr key={row.rank}>
                  <td>{RANK_MEDAL[row.rank] ?? row.rank}</td>
                  <td>{row.user}</td>
                  <td>{row.department}</td>
                  <td>{row.points.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </ApiStateView>
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
