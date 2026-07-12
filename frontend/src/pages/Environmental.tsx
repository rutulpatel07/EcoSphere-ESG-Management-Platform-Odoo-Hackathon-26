import { environmentalMock } from "../mock/mockData";

export default function Environmental() {
  const { goals, carbonTransactions, emissionFactors } = environmentalMock;

  return (
    <div>
      <div className="page-header">
        <h1>Environmental</h1>
        <p>Carbon accounting, emission factors, and reduction goals.</p>
      </div>

      <div className="card">
        <h2>Reduction Goals</h2>
        <table>
          <thead>
            <tr>
              <th>Goal</th>
              <th>Metric</th>
              <th>Current</th>
              <th>Target</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {goals.map((g) => (
              <tr key={g.id}>
                <td>{g.title}</td>
                <td>{g.metric}</td>
                <td>
                  {g.current_value} {g.unit}
                </td>
                <td>
                  {g.target_value} {g.unit}
                </td>
                <td>
                  <span className="pill">{g.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

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
            </tr>
          </thead>
          <tbody>
            {carbonTransactions.map((t) => (
              <tr key={t.id}>
                <td>{t.activity_type}</td>
                <td>{t.quantity}</td>
                <td>{t.factor_value_used}</td>
                <td>
                  {t.co2e_kg} <span className="uncertainty-badge">± {t.uncertainty_pct}%</span>
                </td>
                <td>{t.scope}</td>
                <td>
                  <span className="pill">{t.data_tier}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

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
            </tr>
          </thead>
          <tbody>
            {emissionFactors.map((f) => (
              <tr key={f.id}>
                <td>{f.activity_type}</td>
                <td>{f.factor_value}</td>
                <td>{f.unit}</td>
                <td>{f.source}</td>
                <td>v{f.version}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
