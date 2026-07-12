import { useState } from "react";
import { environmentalMock, governanceMock } from "../mock/mockData";
import Tabs from "../components/Tabs";
import Modal from "../components/Modal";
import ProgressBar from "../components/ProgressBar";
import { pillClass } from "../statusColors";

function goalProgressPct(g: { baseline_value: number; target_value: number; current_value: number }) {
  const span = g.target_value - g.baseline_value;
  if (span === 0) return 100;
  return ((g.current_value - g.baseline_value) / span) * 100;
}

function GoalsTab() {
  return (
    <div className="card">
      <h2>Reduction Goals</h2>
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
          {environmentalMock.goals.map((g) => (
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
    </div>
  );
}

function FactorsTab() {
  return (
    <div className="card">
      <h2>Emission Factors</h2>
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
          {environmentalMock.emissionFactors.map((f) => (
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
    </div>
  );
}

function ProductsTab() {
  return (
    <div className="card">
      <h2>Product ESG Profiles</h2>
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
          {environmentalMock.products.map((p) => (
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
    </div>
  );
}

function TransactionsTab() {
  const [ledgerEntry, setLedgerEntry] = useState<(typeof governanceMock.ledger)[number] | null>(null);

  function openLedger(transactionId: number) {
    const entry = governanceMock.ledger.find(
      (l) => l.ref_table === "carbon_transactions" && l.ref_id === transactionId
    );
    if (entry) setLedgerEntry(entry);
  }

  return (
    <div className="card">
      <h2>Recent Carbon Transactions</h2>
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
          {environmentalMock.carbonTransactions.map((t) => {
            const hasLedgerEntry = governanceMock.ledger.some(
              (l) => l.ref_table === "carbon_transactions" && l.ref_id === t.id
            );
            return (
              <tr key={t.id}>
                <td>{t.activity_type}</td>
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
                  {hasLedgerEntry ? (
                    <button type="button" className="chip-btn" onClick={() => openLedger(t.id)}>
                      🔗 verified
                    </button>
                  ) : (
                    <span className="uncertainty-badge">unrecorded</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

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
