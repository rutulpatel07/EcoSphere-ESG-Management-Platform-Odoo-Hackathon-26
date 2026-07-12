import { useState } from "react";
import ApiStateView from "../components/ApiStateView";
import { useApi } from "../hooks/useApi";
import { DepartmentsApi, ReportsApi } from "../api/endpoints";

// parse_period (backend/app/services_features/reports_data.py) accepts "YYYY",
// "YYYY-MM", or "YYYY-Qn" — "2026" (not "2026 Full Year") is the valid full-year form.
const PERIODS = [
  { value: "2026-Q1", label: "2026 Q1" },
  { value: "2026-Q2", label: "2026 Q2" },
  { value: "2026-Q3", label: "2026 Q3" },
  { value: "2026-Q4", label: "2026 Q4" },
  { value: "2026", label: "2026 Full Year" },
];

const MODULES = [
  { value: "ALL", label: "All Modules" },
  { value: "ENVIRONMENTAL", label: "Environmental" },
  { value: "SOCIAL", label: "Social" },
  { value: "GOVERNANCE", label: "Governance" },
  { value: "GAMIFICATION", label: "Gamification" },
];

const ESG_CATEGORIES = [
  { value: "ALL", label: "All Categories" },
  { value: "E", label: "Environmental (E)" },
  { value: "S", label: "Social (S)" },
  { value: "G", label: "Governance (G)" },
];

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
  const departments = useApi(() => DepartmentsApi.list(), []);

  const [period, setPeriod] = useState(PERIODS[1].value);
  const [genState, setGenState] = useState<Record<string, "idle" | "generating" | "error">>({});

  // Custom Report Builder filters — every one of these maps directly onto a field
  // POST /reports/custom accepts (department_id, start_date, end_date, module,
  // esg_category). No framework/scope/data-tier controls: the backend has no such
  // filters, and a control that silently does nothing isn't worth showing.
  const [departmentId, setDepartmentId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [moduleFilter, setModuleFilter] = useState("ALL");
  const [esgCategory, setEsgCategory] = useState("ALL");

  function generate(id: string, format: string) {
    const key = `${id}:${format}`;
    setGenState((prev) => ({ ...prev, [key]: "generating" }));
    ReportsApi.generate({ report_id: id, format, period })
      .then((res) => {
        const fallback = `${id}-${period}.${format === "XLSX" ? "xlsx" : format.toLowerCase()}`;
        downloadBlob(res.data as Blob, filenameFromDisposition(res.headers?.["content-disposition"], fallback));
        setGenState((prev) => ({ ...prev, [key]: "idle" }));
        recent.refetch();
      })
      .catch(() => setGenState((prev) => ({ ...prev, [key]: "error" })));
  }

  function generateCustom(format: string) {
    const key = `custom:${format}`;
    setGenState((prev) => ({ ...prev, [key]: "generating" }));
    ReportsApi.custom({
      department_id: departmentId === "" ? undefined : Number(departmentId),
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      module: moduleFilter === "ALL" ? undefined : moduleFilter,
      esg_category: esgCategory === "ALL" ? undefined : esgCategory,
      format,
    })
      .then((res) => {
        const fallback = `Custom_ESG_Report.${format === "XLSX" ? "xlsx" : format.toLowerCase()}`;
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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Available Reports</h2>
          <label className="field" style={{ margin: 0 }}>
            <span className="field-label">Period</span>
            <select className="field-input" value={period} onChange={(e) => setPeriod(e.target.value)}>
              {PERIODS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
        </div>
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
        <ApiStateView state={departments}>
          {(deptData) => (
            <>
              <div className="filter-grid">
                <label className="field">
                  <span className="field-label">Department</span>
                  <select
                    className="field-input"
                    value={departmentId}
                    onChange={(e) => setDepartmentId(e.target.value)}
                  >
                    <option value="">All Departments</option>
                    {deptData.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span className="field-label">Start Date</span>
                  <input
                    type="date"
                    className="field-input"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </label>

                <label className="field">
                  <span className="field-label">End Date</span>
                  <input
                    type="date"
                    className="field-input"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </label>

                <label className="field">
                  <span className="field-label">Module</span>
                  <select className="field-input" value={moduleFilter} onChange={(e) => setModuleFilter(e.target.value)}>
                    {MODULES.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span className="field-label">ESG Category</span>
                  <select className="field-input" value={esgCategory} onChange={(e) => setEsgCategory(e.target.value)}>
                    {ESG_CATEGORIES.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="report-builder-actions">
                <button
                  type="button"
                  className="btn btn-quick btn-quick--e"
                  disabled={genState["custom:PDF"] === "generating"}
                  onClick={() => generateCustom("PDF")}
                >
                  {genState["custom:PDF"] === "generating"
                    ? "Generating…"
                    : genState["custom:PDF"] === "error"
                      ? "Failed — retry"
                      : "PDF Export"}
                </button>
                <button
                  type="button"
                  className="btn btn-quick btn-quick--s"
                  disabled={genState["custom:XLSX"] === "generating"}
                  onClick={() => generateCustom("XLSX")}
                >
                  {genState["custom:XLSX"] === "generating"
                    ? "Generating…"
                    : genState["custom:XLSX"] === "error"
                      ? "Failed — retry"
                      : "Excel Export"}
                </button>
                <button
                  type="button"
                  className="btn btn-quick btn-quick--gamification"
                  disabled={genState["custom:CSV"] === "generating"}
                  onClick={() => generateCustom("CSV")}
                >
                  {genState["custom:CSV"] === "generating"
                    ? "Generating…"
                    : genState["custom:CSV"] === "error"
                      ? "Failed — retry"
                      : "CSV Export"}
                </button>
              </div>
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
