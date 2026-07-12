import { socialMock } from "../mock/mockData";

export default function Social() {
  const { activities, participation } = socialMock;

  return (
    <div>
      <div className="page-header">
        <h1>Social</h1>
        <p>CSR activities, volunteering, and employee participation.</p>
      </div>

      <div className="card">
        <h2>CSR Activities</h2>
        <table>
          <thead>
            <tr>
              <th>Activity</th>
              <th>Category</th>
              <th>Location</th>
              <th>Points</th>
              <th>Registered</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {activities.map((a) => (
              <tr key={a.id}>
                <td>{a.title}</td>
                <td>{a.category}</td>
                <td>{a.location}</td>
                <td>{a.points_reward}</td>
                <td>
                  {a.registered}/{a.capacity}
                </td>
                <td>
                  <span className="pill">{a.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Participation</h2>
        <table>
          <thead>
            <tr>
              <th>Activity</th>
              <th>Employee</th>
              <th>Hours</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {participation.map((p) => (
              <tr key={p.id}>
                <td>{p.activity}</td>
                <td>{p.user}</td>
                <td>{p.hours ?? "—"}</td>
                <td>
                  <span className="pill">{p.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
