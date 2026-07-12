import { FormEvent, useState } from "react";
import Tabs from "../components/Tabs";
import Modal from "../components/Modal";
import ProgressBar from "../components/ProgressBar";
import ApiStateView from "../components/ApiStateView";
import { pillClass } from "../statusColors";
import { useApi, describeApiError } from "../hooks/useApi";
import { DepartmentsApi, EnvironmentalApi, GovernanceApi } from "../api/endpoints";
import { getSessionUser, isManager } from "../auth";
import type { EnvGoal, LedgerEntry, OpType, RecomputeResponse } from "../api/types";

const OP_TYPES: OpType[] = ["PURCHASE", "MANUFACTURING", "EXPENSE", "FLEET"];

function goalProgressPct(g: Pick<EnvGoal, "baseline_value" | "target_value" | "current_value">) {
  const span = g.target_value - g.baseline_value;
  if (span === 0) return 100;
  return ((g.current_value - g.baseline_value) / span) * 100;
}

function GoalsTab() {
  const goals = useApi(() => EnvironmentalApi.goals(), []);
  return (
    <div className="card">
      <h2>Reduction Goals</h2>
      <ApiStateView state={goals}>
        {(data) => (
          <table>
            <thead>
              <tr>
                <th>Goal</th>
                <th>Metric</th>
                <th>Current</th>
                <th>Target</th>
                <th>Progress</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.map((g) => (
                <tr key={g.id}>
                  <td>{g.title}</td>
                  <td>{g.metric}</td>
                  <td>
                    {g.current_value} {g.unit}
                  </td>
                  <td>
                    {g.target_value} {g.unit}
                  </td>
                  <td style={{ minWidth: 140 }}>
                    <ProgressBar
                      pct={goalProgressPct(g)}
                      colorVar={g.status === "AT_RISK" ? "var(--pillar-gamification)" : "var(--pillar-e)"}
                    />
                  </td>
                  <td>
                    <span className={pillClass(g.status)}>{g.status}</span>
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

// POST /environmental/carbon-transactions/recompute requires MANAGER/ADMIN
// server-side — hidden for EMPLOYEE so the UI never shows a control that 403s.
function RecomputeCard({ versions }: { versions: number[] }) {
  const [version, setVersion] = useState<number | "">(versions[versions.length - 1] ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RecomputeResponse | null>(null);

  async function run() {
    if (version === "") return;
    setLoading(true);
    setError(null);
    try {
      const res = await EnvironmentalApi.recompute(Number(version));
      setResult(res);
    } catch (err) {
      setError(describeApiError(err));
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <h2>Recompute vs Version</h2>
      <p className="uncertainty-badge">
        Re-price every carbon transaction against a target emission-factor version. Quantities are held constant, so
        the movement splits cleanly into a methodology change (the factor value changed) and a real change (always 0
        by construction for a recompute).
      </p>
      <div className="filter-grid">
        <label className="field">
          <span className="field-label">Target Version</span>
          <select
            className="field-input"
            value={version}
            onChange={(e) => setVersion(e.target.value === "" ? "" : Number(e.target.value))}
          >
            {versions.length === 0 && <option value="">No versions available</option>}
            {versions.map((v) => (
              <option key={v} value={v}>
                v{v}
              </option>
            ))}
          </select>
        </label>
      </div>
      <button
        type="button"
        className="btn btn-primary"
        disabled={loading || version === ""}
        onClick={run}
        style={{ marginTop: 12 }}
      >
        {loading ? "Recomputing…" : "Recompute"}
      </button>

      {error && (
        <div className="api-error" style={{ marginTop: 12 }}>
          <span>⚠ {error}</span>
        </div>
      )}

      {result && (
        <div style={{ marginTop: 16 }}>
          <div className="stat-grid">
            <div className="stat-card">
              <div className="stat-label">Total Old CO₂e</div>
              <div className="stat-value">{result.total_old_co2e_kg.toFixed(1)} kg</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total New CO₂e</div>
              <div className="stat-value">{result.total_new_co2e_kg.toFixed(1)} kg</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Methodology Change</div>
              <div className="stat-value">{result.methodology_change_kg.toFixed(1)} kg</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Real Change</div>
              <div className="stat-value">{result.real_change_kg.toFixed(1)} kg</div>
            </div>
          </div>
          <p className="uncertainty-badge" style={{ marginTop: 12 }}>
            {result.note}
          </p>
        </div>
      )}
    </div>
  );
}

function FactorsTab() {
  const factors = useApi(() => EnvironmentalApi.emissionFactors(), []);
  const canManage = isManager(getSessionUser());
  const versions =
    factors.status === "success" ? Array.from(new Set(factors.data.map((f) => f.version))).sort((a, b) => a - b) : [];

  return (
    <>
      <div className="card">
        <h2>Emission Factors</h2>
        <ApiStateView state={factors}>
          {(data) => (
            <table>
              <thead>
                <tr>
                  <th>Activity</th>
                  <th>Value</th>
                  <th>Unit</th>
                  <th>Source</th>
                  <th>Version</th>
                  <th>Valid From</th>
                </tr>
              </thead>
              <tbody>
                {data.map((f) => (
                  <tr key={f.id}>
                    <td>{f.activity_type}</td>
                    <td>{f.factor_value}</td>
                    <td>{f.unit}</td>
                    <td>{f.source}</td>
                    <td>
                      <span className="pill">v{f.version}</span>
                    </td>
                    <td>{f.valid_from}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ApiStateView>
      </div>

      {canManage && factors.status === "success" && <RecomputeCard versions={versions} />}
    </>
  );
}

function ProductsTab() {
  const products = useApi(() => EnvironmentalApi.products(), []);
  return (
    <div className="card">
      <h2>Product ESG Profiles</h2>
      <ApiStateView state={products}>
        {(data) => (
          <table>
            <thead>
              <tr>
                <th>SKU</th>
                <th>Product</th>
                <th>Embodied Carbon</th>
                <th>Recyclable</th>
                <th>Water Usage</th>
                <th>Ethical Score</th>
                <th>Certifications</th>
              </tr>
            </thead>
            <tbody>
              {data.map((p) => (
                <tr key={p.id}>
                  <td>{p.sku}</td>
                  <td>{p.name}</td>
                  <td>{p.embodied_carbon_kg} kg</td>
                  <td>{p.recyclable_pct}%</td>
                  <td>{p.water_usage_l} L</td>
                  <td>{p.ethical_score}/100</td>
                  <td>
                    {p.certifications.map((c) => (
                      <span className="pill pill--neutral" key={c} style={{ marginRight: 6 }}>
                        {c}
                      </span>
                    ))}
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

interface FieldErrors {
  activityType?: string;
  unit?: string;
  quantity?: string;
  occurredOn?: string;
}

function LogOperationForm({
  onLogged,
}: {
  onLogged: (info: { activityType: string; unit: string; txnId: number | null }) => void;
}) {
  const departments = useApi(() => DepartmentsApi.list(), []);
  const [opType, setOpType] = useState<OpType>("MANUFACTURING");
  const [departmentId, setDepartmentId] = useState("");
  const [activityType, setActivityType] = useState("");
  const [unit, setUnit] = useState("");
  const [quantity, setQuantity] = useState("");
  const [occurredOn, setOccurredOn] = useState(() => new Date().toISOString().slice(0, 10));
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function validate(): FieldErrors {
    const next: FieldErrors = {};
    if (!activityType.trim()) next.activityType = "Activity type is required.";
    if (!unit.trim()) next.unit = "Unit is required.";
    if (quantity.trim() === "") next.quantity = "Quantity is required.";
    else if (Number.isNaN(Number(quantity))) next.quantity = "Quantity must be a number.";
    else if (Number(quantity) <= 0) next.quantity = "Quantity must be greater than 0.";
    if (!occurredOn) next.occurredOn = "Date is required.";
    return next;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const next = validate();
    setErrors(next);
    setFormError(null);
    if (Object.keys(next).length > 0) return;

    setSubmitting(true);
    try {
      const created = await EnvironmentalApi.logOperation({
        op_type: opType,
        activity_type: activityType.trim(),
        quantity: Number(quantity),
        unit: unit.trim(),
        occurred_on: occurredOn,
        department_id: departmentId === "" ? null : Number(departmentId),
      });
      onLogged({ activityType: created.activity_type, unit, txnId: created.carbon_transaction_id });
      setActivityType("");
      setQuantity("");
      setUnit("");
    } catch (err) {
      setFormError(describeApiError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card">
      <h2>Log Operation</h2>
      <form onSubmit={handleSubmit} noValidate>
        {formError && <div className="auth-error-banner">{formError}</div>}
        <div className="filter-grid">
          <label className="field">
            <span className="field-label">Operation Type</span>
            <select className="field-input" value={opType} onChange={(e) => setOpType(e.target.value as OpType)}>
              {OP_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span className="field-label">Department</span>
            <select className="field-input" value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
              <option value="">Unassigned</option>
              {departments.status === "success" &&
                departments.data.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
            </select>
          </label>

          <label className="field">
            <span className="field-label">Activity Type</span>
            <input
              className={"field-input" + (errors.activityType ? " field-input--invalid" : "")}
              value={activityType}
              onChange={(e) => setActivityType(e.target.value)}
              placeholder="e.g. Diesel Consumption"
            />
            {errors.activityType && <span className="field-error">{errors.activityType}</span>}
          </label>

          <label className="field">
            <span className="field-label">Quantity</span>
            <input
              type="number"
              min="0"
              step="any"
              className={"field-input" + (errors.quantity ? " field-input--invalid" : "")}
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="0"
            />
            {errors.quantity && <span className="field-error">{errors.quantity}</span>}
          </label>

          <label className="field">
            <span className="field-label">Unit</span>
            <input
              className={"field-input" + (errors.unit ? " field-input--invalid" : "")}
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              placeholder="e.g. liters, kWh"
            />
            {errors.unit && <span className="field-error">{errors.unit}</span>}
          </label>

          <label className="field">
            <span className="field-label">Occurred On</span>
            <input
              type="date"
              className={"field-input" + (errors.occurredOn ? " field-input--invalid" : "")}
              value={occurredOn}
              onChange={(e) => setOccurredOn(e.target.value)}
            />
            {errors.occurredOn && <span className="field-error">{errors.occurredOn}</span>}
          </label>
        </div>

        <button type="submit" className="btn btn-primary" disabled={submitting} style={{ marginTop: 12 }}>
          {submitting ? "Logging…" : "Log Operation"}
        </button>
      </form>
    </div>
  );
}

function TransactionsTab() {
  const transactions = useApi(() => EnvironmentalApi.carbonTransactions(), []);
  const factors = useApi(() => EnvironmentalApi.emissionFactors(), []);
  const ledger = useApi(() => GovernanceApi.ledger(), []);
  const [ledgerEntry, setLedgerEntry] = useState<LedgerEntry | null>(null);
  const [lastLogged, setLastLogged] = useState<{ activityType: string; unit: string; txnId: number | null } | null>(
    null
  );

  function activityLabel(emissionFactorId: number) {
    if (factors.status !== "success") return `factor #${emissionFactorId}`;
    return factors.data.find((f) => f.id === emissionFactorId)?.activity_type ?? `factor #${emissionFactorId}`;
  }

  function openLedger(transactionId: number) {
    if (ledger.status !== "success") return;
    const entry = ledger.data.find((l) => l.ref_table === "carbon_transactions" && l.ref_id === transactionId);
    if (entry) setLedgerEntry(entry);
  }

  function handleLogged(info: { activityType: string; unit: string; txnId: number | null }) {
    transactions.refetch();
    ledger.refetch();
    setLastLogged(info);
  }

  const resolvedTxn =
    lastLogged && lastLogged.txnId !== null && transactions.status === "success"
      ? transactions.data.find((t) => t.id === lastLogged.txnId)
      : undefined;

  return (
    <div>
      <LogOperationForm onLogged={handleLogged} />

      {lastLogged && (
        <div className="card">
          {lastLogged.txnId === null && (
            <div className="banner-success">
              <span>
                ✓ Operational record logged. No active emission factor matched "{lastLogged.activityType}" /{" "}
                {lastLogged.unit} — no carbon transaction was created.
              </span>
              <button type="button" className="chip-btn" onClick={() => setLastLogged(null)}>
                Dismiss
              </button>
            </div>
          )}
          {lastLogged.txnId !== null && !resolvedTxn && (
            <div className="banner-success">
              <span>✓ Operational record logged — computing carbon transaction…</span>
              <button type="button" className="chip-btn" onClick={() => setLastLogged(null)}>
                Dismiss
              </button>
            </div>
          )}
          {resolvedTxn && (
            <div className="banner-success">
              <span>
                ✓ Carbon transaction #{resolvedTxn.id}: <strong>{resolvedTxn.co2e_kg} kg CO₂e</strong> (scope{" "}
                {resolvedTxn.scope}, {resolvedTxn.data_tier}, ±{resolvedTxn.uncertainty_pct}%)
              </span>
              <button type="button" className="chip-btn" onClick={() => setLastLogged(null)}>
                Dismiss
              </button>
            </div>
          )}
        </div>
      )}

      <div className="card">
        <h2>Recent Carbon Transactions</h2>
        <ApiStateView state={transactions}>
          {(data) => (
            <table>
              <thead>
                <tr>
                  <th>Activity</th>
                  <th>Qty</th>
                  <th>Factor</th>
                  <th>tCO2e (kg)</th>
                  <th>Scope</th>
                  <th>Tier</th>
                  <th>Ledger</th>
                </tr>
              </thead>
              <tbody>
                {data.map((t) => {
                  const hasLedgerEntry =
                    ledger.status === "success" &&
                    ledger.data.some((l) => l.ref_table === "carbon_transactions" && l.ref_id === t.id);
                  return (
                    <tr key={t.id}>
                      <td>{activityLabel(t.emission_factor_id)}</td>
                      <td>{t.quantity}</td>
                      <td>{t.factor_value_used}</td>
                      <td>
                        {t.co2e_kg} <span className="uncertainty-badge">± {t.uncertainty_pct}%</span>
                      </td>
                      <td>{t.scope}</td>
                      <td>
                        <span className={pillClass(t.data_tier)}>{t.data_tier}</span>
                      </td>
                      <td>
                        {ledger.status === "loading" && <span className="uncertainty-badge">checking…</span>}
                        {ledger.status === "error" && <span className="uncertainty-badge">ledger unavailable</span>}
                        {hasLedgerEntry && (
                          <button type="button" className="chip-btn" onClick={() => openLedger(t.id)}>
                            🔗 verified
                          </button>
                        )}
                        {ledger.status === "success" && !hasLedgerEntry && (
                          <span className="uncertainty-badge">unrecorded</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </ApiStateView>
      </div>

      {ledgerEntry && (
        <Modal title="ESG Ledger Entry" onClose={() => setLedgerEntry(null)}>
          <dl className="kv-list">
            <dt>Sequence</dt>
            <dd>#{ledgerEntry.seq}</dd>
            <dt>Entry type</dt>
            <dd>
              <span className="pill">{ledgerEntry.entry_type}</span>
            </dd>
            <dt>Reference</dt>
            <dd>
              {ledgerEntry.ref_table} #{ledgerEntry.ref_id}
            </dd>
            <dt>Row hash</dt>
            <dd>
              <code className="hash-value">{ledgerEntry.row_hash}</code>
            </dd>
            <dt>Previous hash</dt>
            <dd>
              <code className="hash-value">{ledgerEntry.prev_hash}</code>
            </dd>
            <dt>Recorded</dt>
            <dd>{new Date(ledgerEntry.created_at).toLocaleString()}</dd>
          </dl>
        </Modal>
      )}
    </div>
  );
}

export default function Environmental() {
  return (
    <div>
      <div className="page-header">
        <h1>Environmental</h1>
        <p>Carbon accounting, emission factors, and reduction goals.</p>
      </div>

      <Tabs
        items={[
          { key: "factors", label: "Factors", content: <FactorsTab /> },
          { key: "products", label: "Product Profiles", content: <ProductsTab /> },
          { key: "transactions", label: "Carbon Transactions", content: <TransactionsTab /> },
          { key: "goals", label: "Goals", content: <GoalsTab /> },
        ]}
      />
    </div>
  );
}
