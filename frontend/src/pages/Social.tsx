import { useState } from "react";
import { socialMock } from "../mock/mockData";
import ProgressBar from "../components/ProgressBar";
import { pillClass } from "../statusColors";

export default function Social() {
  const { activities, participation: initialParticipation } = socialMock;
  const [participation, setParticipation] = useState(initialParticipation);
  const [joined, setJoined] = useState<Set<number>>(new Set());

  function evidenceCount(activityTitle: string) {
    return participation.filter((p) => p.activity === activityTitle && p.proof_url).length;
  }

  function setStatus(id: number, status: "VERIFIED" | "REJECTED") {
    setParticipation((prev) => prev.map((p) => (p.id === id ? { ...p, status } : p)));
  }

  const pendingQueue = participation.filter((p) => p.status === "REGISTERED");

  return (
    <div>
      <div className="page-header">
        <h1>Social</h1>
        <p>CSR activities, volunteering, and employee participation.</p>
      </div>

      <div className="card">
        <h2>CSR Activities</h2>
        <div className="activity-card-grid">
          {activities.map((a) => {
            const isFull = a.status === "FULL";
            const isJoined = joined.has(a.id);
            return (
              <div className="activity-card" key={a.id}>
                <div className="activity-card-top">
                  <span className="pill pill--neutral">{a.category}</span>
                  <span className={pillClass(a.status)}>{a.status}</span>
                </div>
                <h3 className="activity-card-title">{a.title}</h3>
                <p className="activity-card-meta">
                  📍 {a.location} · {a.start_date}
                </p>
                <div className="activity-card-badges">
                  <span className="pill">{a.points_reward} pts</span>
                  <span className="uncertainty-badge">📎 evidence required · {evidenceCount(a.title)} submitted</span>
                </div>
                <div className="activity-card-progress">
                  <ProgressBar pct={(a.registered / a.capacity) * 100} colorVar="var(--pillar-s)" />
                  <span className="activity-card-progress-label">
                    {a.registered}/{a.capacity} registered
                  </span>
                </div>
                <button
                  type="button"
                  className={"btn btn-quick btn-quick--s" + (isJoined || isFull ? " btn--disabled" : "")}
                  disabled={isJoined || isFull}
                  onClick={() => setJoined((prev) => new Set(prev).add(a.id))}
                >
                  {isJoined ? "✓ Registered" : isFull ? "Activity Full" : "Join Activity"}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      <div className="card">
        <h2>Approval Queue</h2>
        {pendingQueue.length === 0 ? (
          <p className="uncertainty-badge">No pending submissions.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Activity</th>
                <th>Employee</th>
                <th>Evidence</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {pendingQueue.map((p) => (
                <tr key={p.id}>
                  <td>{p.activity}</td>
                  <td>{p.user}</td>
                  <td>
                    {p.proof_url ? (
                      <a href={p.proof_url} target="_blank" rel="noreferrer">
                        📎 view proof
                      </a>
                    ) : (
                      <span className="uncertainty-badge">not submitted</span>
                    )}
                  </td>
                  <td>
                    <span className={pillClass(p.status)}>{p.status}</span>
                  </td>
                  <td className="approval-actions">
                    <button type="button" className="btn btn-approve" onClick={() => setStatus(p.id, "VERIFIED")}>
                      Approve
                    </button>
                    <button type="button" className="btn btn-reject" onClick={() => setStatus(p.id, "REJECTED")}>
                      Reject
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h2>Participation</h2>
        <table>
          <thead>
            <tr>
              <th>Activity</th>
              <th>Employee</th>
              <th>Hours</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {participation.map((p) => (
              <tr key={p.id}>
                <td>{p.activity}</td>
                <td>{p.user}</td>
                <td>{p.hours ?? "—"}</td>
                <td>
                  <span className={pillClass(p.status)}>{p.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
