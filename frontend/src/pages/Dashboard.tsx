import { dashboardMock } from "../mock/mockData";

export default function Dashboard() {
  const { esgScore, kpis, departmentScores } = dashboardMock;

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Company-wide ESG performance at a glance.</p>
      </div>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">ESG Score</div>
          <div className="stat-value">{esgScore.total}</div>
          <div className="stat-label">
            E {esgScore.e} · S {esgScore.s} · G {esgScore.g}
          </div>
        </div>
        {kpis.map((kpi) => (
          <div className="stat-card" key={kpi.label}>
            <div className="stat-label">{kpi.label}</div>
            <div className="stat-value">{kpi.value}</div>
            <div className="stat-label">{kpi.delta}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <h2>Department Scores — {departmentScores[0]?.period}</h2>
        <table>
          <thead>
            <tr>
              <th>Department</th>
              <th>E</th>
              <th>S</th>
              <th>G</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {departmentScores.map((d) => (
              <tr key={d.department}>
                <td>{d.department}</td>
                <td>{d.e}</td>
                <td>{d.s}</td>
                <td>{d.g}</td>
                <td>{d.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
