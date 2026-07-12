import { reportsMock } from "../mock/mockData";

export default function Reports() {
  const { available, recent } = reportsMock;

  return (
    <div>
      <div className="page-header">
        <h1>Reports</h1>
        <p>Generate and download ESG, carbon, and compliance reports.</p>
      </div>

      <div className="card">
        <h2>Available Reports</h2>
        <table>
          <thead>
            <tr>
              <th>Report</th>
              <th>Formats</th>
            </tr>
          </thead>
          <tbody>
            {available.map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td>{r.formats.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Recently Generated</h2>
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
            {recent.map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td>{r.format}</td>
                <td>{r.generated_at}</td>
                <td>{r.size_kb} KB</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
