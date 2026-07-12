import Tabs from "../components/Tabs";
import ApiStateView from "../components/ApiStateView";
import { pillClass } from "../statusColors";
import { useApi } from "../hooks/useApi";
import { GovernanceApi } from "../api/endpoints";

const TODAY = "2026-07-12";

function PoliciesTab() {
  const policies = useApi(() => GovernanceApi.policies(), []);
  return (
    <div className="card">
      <h2>Policies</h2>
      <ApiStateView state={policies}>
        {(data) => (
          <table>
            <thead>
              <tr>
                <th>Policy</th>
                <th>Version</th>
                <th>Category</th>
                <th>Mandatory</th>
              </tr>
            </thead>
            <tbody>
              {data.map((p) => (
                <tr key={p.id}>
                  <td>{p.title}</td>
                  <td>
                    <span className="pill">v{p.version}</span>
                  </td>
                  <td>{p.category}</td>
                  <td>{p.is_mandatory ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </ApiStateView>
      {/* Acknowledgement rate has no field on GET /governance/policies — see wiring report. */}
    </div>
  );
}

function AuditsTab() {
  const audits = useApi(() => GovernanceApi.audits(), []);
  return (
    <div className="card">
      <h2>Audits</h2>
      <ApiStateView state={audits}>
        {(data) => (
          <table>
            <thead>
              <tr>
                <th>Audit</th>
                <th>Framework</th>
                <th>Auditor</th>
                <th>Period</th>
                <th>Scheduled</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.map((a) => (
                <tr key={a.id}>
                  <td>{a.title}</td>
                  <td>
                    <span className="pill pill--neutral">{a.framework}</span>
                  </td>
                  <td>#{a.auditor_user_id}</td>
                  <td>
                    {a.period_start} → {a.period_end}
                  </td>
                  <td>{a.scheduled_date}</td>
                  <td>
                    <span className={pillClass(a.status)}>{a.status}</span>
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

function ComplianceTab() {
  const issues = useApi(() => GovernanceApi.complianceIssues(), []);
  return (
    <div className="card">
      <h2>Compliance Issues</h2>
      <ApiStateView state={issues}>
        {(data) => (
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
              {data.map((c) => {
                const isResolved = Boolean(c.resolved_at);
                const isOverdue = !isResolved && c.due_date < TODAY;
                return (
                  <tr key={c.id} className={isOverdue ? "row--overdue" : undefined}>
                    <td>{c.title}</td>
                    <td>
                      <span className={pillClass(c.severity)}>{c.severity}</span>
                    </td>
                    <td>#{c.owner_user_id}</td>
                    <td>
                      {c.due_date}
                      {isOverdue && <span className="pill pill--danger overdue-tag">OVERDUE</span>}
                    </td>
                    <td>
                      <span className={pillClass(c.status)}>{c.status}</span>
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

function LedgerTab() {
  const ledger = useApi(() => GovernanceApi.ledger(), []);
  const verify = useApi(() => GovernanceApi.ledgerVerify(), []);

  return (
    <div className="card">
      <h2>ESG Ledger (append-only)</h2>
      {verify.status === "success" && (
        <p className="uncertainty-badge">
          <span className={verify.data.valid ? "pill pill--success" : "pill pill--danger"}>
            {verify.data.valid ? "Chain verified" : `Chain broken at seq ${verify.data.broken_at_seq}`}
          </span>{" "}
          {verify.data.entries} entries
        </p>
      )}
      {verify.status === "error" && <p className="uncertainty-badge">Chain verification unavailable: {verify.error}</p>}

      <ApiStateView state={ledger}>
        {(data) => (
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
              {data.map((l) => (
                <tr key={l.seq}>
                  <td>{l.seq}</td>
                  <td>
                    <span className="pill pill--neutral">{l.entry_type}</span>
                  </td>
                  <td>
                    {l.ref_table}#{l.ref_id}
                  </td>
                  <td>
                    <code className="hash-value">{l.row_hash}</code>
                  </td>
                  <td>{new Date(l.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </ApiStateView>
    </div>
  );
}

export default function Governance() {
  return (
    <div>
      <div className="page-header">
        <h1>Governance</h1>
        <p>Policies, audits, compliance issues, and the ESG ledger.</p>
      </div>

      <Tabs
        items={[
          { key: "policies", label: "Policies", content: <PoliciesTab /> },
          { key: "audits", label: "Audits", content: <AuditsTab /> },
          { key: "compliance", label: "Compliance", content: <ComplianceTab /> },
          { key: "ledger", label: "Ledger", content: <LedgerTab /> },
        ]}
      />
    </div>
  );
}
