import { settingsMock } from "../mock/mockData";

export default function Settings() {
  const s = settingsMock;

  const toggles: { label: string; value: boolean }[] = [
    { label: "Gamification enabled", value: s.gamification_enabled },
    { label: "CSR module enabled", value: s.csr_module_enabled },
    { label: "Notifications enabled", value: s.notifications_enabled },
    { label: "Public leaderboard", value: s.public_leaderboard },
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Settings</h1>
        <p>Platform module toggles and ESG scoring weights.</p>
      </div>

      <div className="card">
        <h2>Module Toggles</h2>
        <table>
          <tbody>
            {toggles.map((t) => (
              <tr key={t.label}>
                <td>{t.label}</td>
                <td>
                  <span className="pill">{t.value ? "ON" : "OFF"}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>ESG Weights</h2>
        <table>
          <thead>
            <tr>
              <th>Environmental</th>
              <th>Social</th>
              <th>Governance</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{s.esg_weights.E}%</td>
              <td>{s.esg_weights.S}%</td>
              <td>{s.esg_weights.G}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
