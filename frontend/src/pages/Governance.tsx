import { governanceMock } from "../mock/mockData";

export default function Governance() {
  const { policies, complianceIssues, ledger } = governanceMock;

  return (
    <div>
      <div className="page-header">
        <h1>Governance</h1>
        <p>Policies, audits, compliance issues, and the ESG ledger.</p>
      </div>

      <div className="card">
        <h2>Policies</h2>
        <table>
          <thead>
            <tr>
              <th>Policy</th>
              <th>Version</th>
              <th>Category</th>
              <th>Ack Rate</th>
            </tr>
          </thead>
          <tbody>
            {policies.map((p) => (
              <tr key={p.id}>
                <td>{p.title}</td>
                <td>v{p.version}</td>
                <td>{p.category}</td>
                <td>{Math.round(p.ack_rate * 100)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Compliance Issues</h2>
        <table>
          <thead>
            <tr>
              <th>Issue</th>
              <th>Severity</th>
              <th>Owner</th>
              <th>Due</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {complianceIssues.map((c) => (
              <tr key={c.id}>
                <td>{c.title}</td>
                <td>{c.severity}</td>
                <td>{c.owner}</td>
                <td>{c.due_date}</td>
                <td>
                  <span className="pill">{c.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>ESG Ledger (append-only)</h2>
        <table>
          <thead>
            <tr>
              <th>Seq</th>
              <th>Type</th>
              <th>Ref</th>
              <th>Row Hash</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {ledger.map((l) => (
              <tr key={l.seq}>
                <td>{l.seq}</td>
                <td>{l.entry_type}</td>
                <td>
                  {l.ref_table}#{l.ref_id}
                </td>
                <td>
                  <code>{l.row_hash}</code>
                </td>
                <td>{l.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
