import { useState } from "react";
import ProgressBar from "../components/ProgressBar";
import ApiStateView from "../components/ApiStateView";
import { pillClass } from "../statusColors";
import { useApi } from "../hooks/useApi";
import { SocialApi } from "../api/endpoints";
import { getSessionUser, isManager } from "../auth";
import type { CsrActivity, CsrCategory, Participation } from "../api/types";

// CONTRACT.md exposes participants only per-activity (GET /social/activities/{id}/participants) —
// there is no bulk "all participation records" endpoint, so this reconstructs a flat list
// client-side with one call per activity.
function ParticipationSection({ activities, categories }: { activities: CsrActivity[]; categories: CsrCategory[] }) {
  const participantsByActivity = useApi(
    () => Promise.all(activities.map((a) => SocialApi.participants(a.id).then((p) => [a.id, p] as const))),
    [activities]
  );
  const [overrides, setOverrides] = useState<Record<number, string>>({});
  // PATCH /social/participation/{id} (verify/approve) requires MANAGER/ADMIN
  // server-side — the queue is hidden for EMPLOYEE so the UI never shows a
  // button that would 403.
  const canManage = isManager(getSessionUser());

  function setStatus(id: number, status: "VERIFIED" | "REJECTED") {
    SocialApi.updateParticipation(id, { status }).then(
      () => setOverrides((prev) => ({ ...prev, [id]: status })),
      () => setOverrides((prev) => ({ ...prev, [id]: `ERROR` }))
    );
  }

  return (
    <ApiStateView state={participantsByActivity}>
      {(pairs) => {
        const flat: Participation[] = pairs.flatMap(([, list]) => list);
        const withOverrides = flat.map((p) => (overrides[p.id] ? { ...p, status: overrides[p.id] } : p));
        const evidenceCountByActivity = new Map<number, number>();
        for (const p of flat) {
          if (p.proof_url) evidenceCountByActivity.set(p.csr_activity_id, (evidenceCountByActivity.get(p.csr_activity_id) ?? 0) + 1);
        }
        const registeredCountByActivity = new Map<number, number>();
        for (const p of flat) {
          registeredCountByActivity.set(p.csr_activity_id, (registeredCountByActivity.get(p.csr_activity_id) ?? 0) + 1);
        }
        const pendingQueue = withOverrides.filter((p) => p.status === "REGISTERED");

        return (
          <>
            <div className="card">
              <h2>CSR Activities</h2>
              <div className="activity-card-grid">
                {activities.map((a) => {
                  const registered = registeredCountByActivity.get(a.id) ?? 0;
                  const evidence = evidenceCountByActivity.get(a.id) ?? 0;
                  const isFull = registered >= a.capacity;
                  return (
                    <div className="activity-card" key={a.id}>
                      <div className="activity-card-top">
                        <span className="pill pill--neutral">{categoryName(categories, a.category_id)}</span>
                        <span className={pillClass(a.status)}>{a.status}</span>
                      </div>
                      <h3 className="activity-card-title">{a.title}</h3>
                      <p className="activity-card-meta">
                        📍 {a.location} · {a.start_date}
                      </p>
                      <div className="activity-card-badges">
                        <span className="pill">{a.points_reward} pts</span>
                        <span className="uncertainty-badge">📎 evidence required · {evidence} submitted</span>
                      </div>
                      <div className="activity-card-progress">
                        <ProgressBar pct={(registered / a.capacity) * 100} colorVar="var(--pillar-s)" />
                        <span className="activity-card-progress-label">
                          {registered}/{a.capacity} registered
                        </span>
                      </div>
                      <JoinButton activityId={a.id} disabled={isFull} full={isFull} />
                    </div>
                  );
                })}
              </div>
            </div>

            {canManage && (
              <div className="card">
                <h2>Approval Queue</h2>
                {pendingQueue.length === 0 ? (
                  <p className="uncertainty-badge">No pending submissions.</p>
                ) : (
                  <table>
                    <thead>
                      <tr>
                        <th>Activity</th>
                        <th>User</th>
                        <th>Evidence</th>
                        <th>Status</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pendingQueue.map((p) => (
                        <tr key={p.id}>
                          <td>{activities.find((a) => a.id === p.csr_activity_id)?.title ?? `#${p.csr_activity_id}`}</td>
                          <td>#{p.user_id}</td>
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
            )}

            <div className="card">
              <h2>Participation</h2>
              <table>
                <thead>
                  <tr>
                    <th>Activity</th>
                    <th>User</th>
                    <th>Hours</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {withOverrides.map((p) => (
                    <tr key={p.id}>
                      <td>{activities.find((a) => a.id === p.csr_activity_id)?.title ?? `#${p.csr_activity_id}`}</td>
                      <td>#{p.user_id}</td>
                      <td>{p.hours ?? "—"}</td>
                      <td>
                        <span className={pillClass(p.status)}>{p.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        );
      }}
    </ApiStateView>
  );
}

function JoinButton({ activityId, disabled, full }: { activityId: number; disabled: boolean; full: boolean }) {
  const [state, setState] = useState<"idle" | "joining" | "joined" | "error">("idle");

  function join() {
    setState("joining");
    // CONTRACT.md's join body carries proof_url, but there is no documented upload
    // endpoint to obtain one before joining — sent empty (see wiring report).
    SocialApi.join(activityId, "").then(
      () => setState("joined"),
      () => setState("error")
    );
  }

  if (state === "joined") {
    return (
      <button type="button" className="btn btn-quick btn-quick--s btn--disabled" disabled>
        ✓ Registered
      </button>
    );
  }
  return (
    <button
      type="button"
      className={"btn btn-quick btn-quick--s" + (disabled ? " btn--disabled" : "")}
      disabled={disabled || state === "joining"}
      onClick={join}
    >
      {full ? "Activity Full" : state === "joining" ? "Joining…" : state === "error" ? "Failed — retry" : "Join Activity"}
    </button>
  );
}

function categoryName(categories: CsrCategory[], id: number) {
  return categories.find((c) => c.id === id)?.name ?? `#${id}`;
}

export default function Social() {
  const activities = useApi(() => SocialApi.activities(), []);
  const categories = useApi(() => SocialApi.categories(), []);

  return (
    <div>
      <div className="page-header">
        <h1>Social</h1>
        <p>CSR activities, volunteering, and employee participation.</p>
      </div>

      {activities.status !== "success" && (
        <div className="card">
          <ApiStateView state={activities}>{() => null}</ApiStateView>
        </div>
      )}

      {activities.status === "success" && categories.status === "success" && (
        <ParticipationSection activities={activities.data} categories={categories.data} />
      )}
      {activities.status === "success" && categories.status !== "success" && (
        <div className="card">
          <ApiStateView state={categories}>{() => null}</ApiStateView>
        </div>
      )}
    </div>
  );
}
