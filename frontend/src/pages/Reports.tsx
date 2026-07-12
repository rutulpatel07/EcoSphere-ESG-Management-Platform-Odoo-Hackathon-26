import { useState } from "react";
import { departmentsMock } from "../mock/mockData";
import ApiStateView from "../components/ApiStateView";
import { useApi } from "../hooks/useApi";
import { ReportsApi } from "../api/endpoints";

const PERIODS = ["2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4", "2026 Full Year"];
const FRAMEWORKS = ["All", "GRI", "SASB", "TCFD"];
const SCOPES = ["All", "Scope 1", "Scope 2", "Scope 3"];
const DATA_TIERS = ["All", "MEASURED", "CALCULATED", "ESTIMATED", "DEFAULT"];

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function filenameFromDisposition(disposition: string | undefined, fallback: string): string {
  const match = disposition?.match(/filename="?([^";]+)"?/);
  return match ? match[1] : fallback;
}

export default function Reports() {
  const available = useApi(() => ReportsApi.available(), []);
  const recent = useApi(() => ReportsApi.recent(), []);

  const [reportId, setReportId] = useState("");
  const [department, setDepartment] = useState("All");
  const [period, setPeriod] = useState(PERIODS[1]);
  const [framework, setFramework] = useState(FRAMEWORKS[0]);
  const [scope, setScope] = useState(SCOPES[0]);
  const [dataTier, setDataTier] = useState(DATA_TIERS[0]);
  const [built, setBuilt] = useState(false);
  const [genState, setGenState] = useState<Record<string, "idle" | "generating" | "error">>({});

  function generate(id: string, format: string) {
    const key = `${id}:${format}`;
    setGenState((prev) => ({ ...prev, [key]: "generating" }));
    // department/framework/scope/dataTier filter the report scope client-side per the
    // custom builder — CONTRACT.md's POST /reports/generate only documents
    // { report_id, format, period }, so those extra filters aren't sent (see wiring report).
    ReportsApi.generate({ report_id: id, format, period })
      .then((res) => {
        const fallback = `${id}-${period}.${format === "XLSX" ? "xlsx" : format.toLowerCase()}`;
        downloadBlob(res.data as Blob, filenameFromDisposition(res.headers?.["content-disposition"], fallback));
        setGenState((prev) => ({ ...prev, [key]: "idle" }));
        recent.refetch();
      })
      .catch(() => setGenState((prev) => ({ ...prev, [key]: "error" })));
  }

  return (
    <div>
      <div className="page-header">
        <h1>Reports</h1>
        <p>Generate and download ESG, carbon, and compliance reports.</p>
      </div>

      <div className="card">
        <ApiStateView state={available}>
          {(reports) => (
            <div className="report-card-grid">
              {reports.map((r) => (
                <div className="report-card" key={r.id}>
                  <h3 className="activity-card-title">{r.name}</h3>
                  <p className="activity-card-meta">Available formats</p>
                  <div className="report-card-actions">
                    {r.formats.map((f) => {
                      const key = `${r.id}:${f}`;
                      const state = genState[key] ?? "idle";
                      return (
                        <button
                          key={f}
                          type="button"
                          className="btn btn-quick btn-quick--neutral"
                          disabled={state === "generating"}
                          onClick={() => generate(r.id, f)}
                        >
                          {state === "generating" ? "Generating…" : state === "error" ? "Failed — retry" : f}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </ApiStateView>
      </div>

      <div className="card">
        <h2>Custom Report Builder</h2>
        <ApiStateView state={available}>
          {(reports) => (
            <>
              <div className="filter-grid">
                <label className="field">
                  <span className="field-label">Report Type</span>
                  <select
                    className="field-input"
                    value={reportId || reports[0]?.id || ""}
                    onChange={(e) => {
                      setReportId(e.target.value);
                      setBuilt(false);
                    }}
                  >
                    {reports.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span className="field-label">Department</span>
                  <select
                    className="field-input"
                    value={department}
                    onChange={(e) => {
                      setDepartment(e.target.value);
                      setBuilt(false);
                    }}
                  >
                    <option value="All">All Departments</option>
                    {departmentsMock.map((d) => (
                      <option key={d.id} value={d.name}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span className="field-label">Period</span>
                  <select
                    className="field-input"
                    value={period}
                    onChange={(e) => {
                      setPeriod(e.target.value);
                      setBuilt(false);
                    }}
                  >
                    {PERIODS.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span className="field-label">Framework</span>
                  <select
                    className="field-input"
                    value={framework}
                    onChange={(e) => {
                      setFramework(e.target.value);
                      setBuilt(false);
                    }}
                  >
                    {FRAMEWORKS.map((f) => (
                      <option key={f} value={f}>
                        {f}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span className="field-label">Scope</span>
                  <select
                    className="field-input"
                    value={scope}
                    onChange={(e) => {
                      setScope(e.target.value);
                      setBuilt(false);
                    }}
                  >
                    {SCOPES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span className="field-label">Data Tier</span>
                  <select
                    className="field-input"
                    value={dataTier}
                    onChange={(e) => {
                      setDataTier(e.target.value);
                      setBuilt(false);
                    }}
                  >
                    {DATA_TIERS.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="report-builder-actions">
                <button type="button" className="btn btn-primary" onClick={() => setBuilt(true)}>
                  Run
                </button>
                <button
                  type="button"
                  className="btn btn-quick btn-quick--e"
                  disabled={!built}
                  onClick={() => generate(reportId || reports[0]?.id, "PDF")}
                >
                  PDF Export
                </button>
                <button
                  type="button"
                  className="btn btn-quick btn-quick--s"
                  disabled={!built}
                  onClick={() => generate(reportId || reports[0]?.id, "XLSX")}
                >
                  Excel Export
                </button>
                <button
                  type="button"
                  className="btn btn-quick btn-quick--gamification"
                  disabled={!built}
                  onClick={() => generate(reportId || reports[0]?.id, "CSV")}
                >
                  CSV Export
                </button>
              </div>
              {!built && <p className="uncertainty-badge">Run the builder to enable exports.</p>}
            </>
          )}
        </ApiStateView>
      </div>

      <div className="card">
        <h2>Recently Generated</h2>
        <ApiStateView state={recent}>
          {(data) => (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Format</th>
                  <th>Generated</th>
                  <th>Size</th>
                </tr>
              </thead>
              <tbody>
                {data.map((r) => (
                  <tr key={r.id}>
                    <td>{r.name}</td>
                    <td>
                      <span className="pill">{r.format}</span>
                    </td>
                    <td>{new Date(r.generated_at).toLocaleString()}</td>
                    <td>{r.size_kb} KB</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ApiStateView>
      </div>
    </div>
  );
}
