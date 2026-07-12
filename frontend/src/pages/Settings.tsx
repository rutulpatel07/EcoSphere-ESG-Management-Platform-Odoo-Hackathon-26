import { useEffect, useState } from "react";
import ApiStateView from "../components/ApiStateView";
import { pillClass } from "../statusColors";
import { useApi } from "../hooks/useApi";
import { DepartmentsApi, NotificationsApi, SettingsApi, SocialApi } from "../api/endpoints";
import { getSessionUser, isAdmin } from "../auth";
import type { Department, PlatformSettings } from "../api/types";

function deptName(departments: Department[], id: number | null) {
  if (id === null) return "—";
  return departments.find((d) => d.id === id)?.name ?? `#${id}`;
}

function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className={"toggle-switch" + (disabled ? " toggle-switch--disabled" : "")}>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      <span className="toggle-switch-track" />
    </label>
  );
}

function DepartmentsCard() {
  const departments = useApi(() => DepartmentsApi.list(), []);
  return (
    <div className="card">
      <h2>Departments</h2>
      <ApiStateView state={departments}>
        {(data) => (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Code</th>
                <th>Parent</th>
                <th>Manager</th>
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.id}>
                  <td>{d.name}</td>
                  <td>
                    <span className="pill pill--neutral">{d.code}</span>
                  </td>
                  <td>{deptName(data, d.parent_id)}</td>
                  <td>{d.manager_id === null ? "—" : `#${d.manager_id}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </ApiStateView>
    </div>
  );
}

function CategoriesCard() {
  // CONTRACT.md documents this route under Social (`GET /social/categories?type=CSR`);
  // called without the filter here to also pick up CHALLENGE-type categories.
  const categories = useApi(() => SocialApi.categories(), []);
  return (
    <div className="card">
      <h2>Categories</h2>
      <ApiStateView state={categories}>
        {(data) => (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.map((c) => (
                <tr key={c.id}>
                  <td>{c.name}</td>
                  <td>
                    <span className="pill pill--neutral">{c.type}</span>
                  </td>
                  <td>
                    <span className={pillClass(c.is_active ? "ACTIVE" : "ARCHIVED")}>
                      {c.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </ApiStateView>
    </div>
  );
}

function EsgConfigCard() {
  const settings = useApi(() => SettingsApi.get(), []);
  const [draft, setDraft] = useState<PlatformSettings | null>(null);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  // PATCH /settings requires ADMIN server-side — read-only for everyone else so
  // the UI never shows a Save button that would 403.
  const canEdit = isAdmin(getSessionUser());

  useEffect(() => {
    if (settings.status === "success") setDraft(settings.data);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.status]);

  if (settings.status !== "success" || !draft) {
    return (
      <div className="card">
        <h2>ESG Configuration</h2>
        <ApiStateView state={settings}>{() => null}</ApiStateView>
      </div>
    );
  }

  const weightSum = draft.esg_weights.E + draft.esg_weights.S + draft.esg_weights.G;
  const weightsValid = weightSum === 100;

  function setToggle(key: keyof Pick<PlatformSettings, "gamification_enabled" | "csr_module_enabled" | "notifications_enabled" | "public_leaderboard">, value: boolean) {
    setDraft((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  function setWeight(key: "E" | "S" | "G", value: number) {
    setDraft((prev) => (prev ? { ...prev, esg_weights: { ...prev.esg_weights, [key]: value } } : prev));
  }

  function save() {
    if (!draft) return;
    setSaveState("saving");
    SettingsApi.update({
      gamification_enabled: draft.gamification_enabled,
      csr_module_enabled: draft.csr_module_enabled,
      notifications_enabled: draft.notifications_enabled,
      public_leaderboard: draft.public_leaderboard,
      esg_weights: draft.esg_weights,
    }).then(
      () => setSaveState("saved"),
      () => setSaveState("error")
    );
  }

  return (
    <div className="card">
      <h2>ESG Configuration</h2>
      {!canEdit && (
        <p className="uncertainty-badge">Only admins can change platform configuration. Showing current values.</p>
      )}

      <div className="settings-toggle-row">
        <span>Gamification enabled</span>
        <Toggle
          checked={draft.gamification_enabled}
          onChange={(v) => setToggle("gamification_enabled", v)}
          disabled={!canEdit}
        />
      </div>
      <div className="settings-toggle-row">
        <span>CSR module enabled</span>
        <Toggle
          checked={draft.csr_module_enabled}
          onChange={(v) => setToggle("csr_module_enabled", v)}
          disabled={!canEdit}
        />
      </div>
      <div className="settings-toggle-row">
        <span>Notifications enabled</span>
        <Toggle
          checked={draft.notifications_enabled}
          onChange={(v) => setToggle("notifications_enabled", v)}
          disabled={!canEdit}
        />
      </div>
      <div className="settings-toggle-row">
        <span>Public leaderboard</span>
        <Toggle
          checked={draft.public_leaderboard}
          onChange={(v) => setToggle("public_leaderboard", v)}
          disabled={!canEdit}
        />
      </div>

      <h2 style={{ marginTop: 24 }}>ESG Weights</h2>
      <div className="weight-input-grid">
        <div className="weight-input-field">
          <span className="field-label">Environmental %</span>
          <input
            type="number"
            min={0}
            max={100}
            disabled={!canEdit}
            value={draft.esg_weights.E}
            onChange={(e) => setWeight("E", Number(e.target.value))}
          />
        </div>
        <div className="weight-input-field">
          <span className="field-label">Social %</span>
          <input
            type="number"
            min={0}
            max={100}
            disabled={!canEdit}
            value={draft.esg_weights.S}
            onChange={(e) => setWeight("S", Number(e.target.value))}
          />
        </div>
        <div className="weight-input-field">
          <span className="field-label">Governance %</span>
          <input
            type="number"
            min={0}
            max={100}
            disabled={!canEdit}
            value={draft.esg_weights.G}
            onChange={(e) => setWeight("G", Number(e.target.value))}
          />
        </div>
      </div>
      {canEdit && (
        <>
          <p className={"weight-sum-note " + (weightsValid ? "weight-sum-note--ok" : "weight-sum-note--bad")}>
            {weightsValid ? "✓ Weights sum to 100%." : `Weights must sum to 100% (currently ${weightSum}%).`}
          </p>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!weightsValid || saveState === "saving"}
            onClick={save}
          >
            {saveState === "saving"
              ? "Saving…"
              : saveState === "saved"
                ? "✓ Saved"
                : saveState === "error"
                  ? "Failed — retry"
                  : "Save Configuration"}
          </button>
        </>
      )}
    </div>
  );
}

function NotificationSettingsCard() {
  const notifications = useApi(() => NotificationsApi.list(), []);
  const [overrides, setOverrides] = useState<Set<number>>(new Set());

  function markRead(id: number) {
    NotificationsApi.markRead(id).then(() => setOverrides((prev) => new Set(prev).add(id)));
  }

  return (
    <div className="card">
      <ApiStateView state={notifications}>
        {(data) => {
          const withOverrides = data.map((n) => (overrides.has(n.id) ? { ...n, is_read: true } : n));
          const unreadCount = withOverrides.filter((n) => !n.is_read).length;
          return (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h2>
                  Notification Settings
                  {unreadCount > 0 && <span className="pill pill--warning" style={{ marginLeft: 8 }}>{unreadCount} unread</span>}
                </h2>
                <button
                  type="button"
                  className="btn btn-quick btn-quick--neutral"
                  disabled={unreadCount === 0}
                  onClick={() => withOverrides.filter((n) => !n.is_read).forEach((n) => markRead(n.id))}
                >
                  Mark all as read
                </button>
              </div>
              {withOverrides.map((n) => (
                <div className={"notification-row" + (n.is_read ? "" : " notification-row--unread")} key={n.id}>
                  <div className="notification-row-body">
                    <div className="notification-row-title">{n.title}</div>
                    <div className="notification-row-text">{n.body}</div>
                  </div>
                  <span className="pill pill--neutral">{n.type}</span>
                  {!n.is_read && (
                    <button type="button" className="chip-btn" onClick={() => markRead(n.id)}>
                      Mark read
                    </button>
                  )}
                </div>
              ))}
            </>
          );
        }}
      </ApiStateView>
    </div>
  );
}

export default function Settings() {
  return (
    <div>
      <div className="page-header">
        <h1>Settings</h1>
        <p>Departments, categories, platform module toggles, and ESG scoring weights.</p>
      </div>

      <DepartmentsCard />
      <CategoriesCard />
      <EsgConfigCard />
      <NotificationSettingsCard />
    </div>
  );
}
