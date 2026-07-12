import { gamificationMock } from "../mock/mockData";

export default function Gamification() {
  const { leaderboard, challenges, rewards } = gamificationMock;

  return (
    <div>
      <div className="page-header">
        <h1>Gamification</h1>
        <p>Challenges, leaderboard, badges, and the rewards store.</p>
      </div>

      <div className="card">
        <h2>Leaderboard</h2>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Employee</th>
              <th>Department</th>
              <th>Points</th>
            </tr>
          </thead>
          <tbody>
            {leaderboard.map((row) => (
              <tr key={row.rank}>
                <td>{row.rank}</td>
                <td>{row.user}</td>
                <td>{row.department}</td>
                <td>{row.points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Active Challenges</h2>
        <table>
          <thead>
            <tr>
              <th>Challenge</th>
              <th>Lifecycle</th>
              <th>Progress</th>
              <th>Target</th>
              <th>Points</th>
            </tr>
          </thead>
          <tbody>
            {challenges.map((c) => (
              <tr key={c.id}>
                <td>{c.title}</td>
                <td>
                  <span className="pill">{c.lifecycle}</span>
                </td>
                <td>{c.progress}</td>
                <td>{c.goal_target}</td>
                <td>{c.points_reward}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Rewards Store</h2>
        <table>
          <thead>
            <tr>
              <th>Reward</th>
              <th>Cost</th>
              <th>Stock</th>
            </tr>
          </thead>
          <tbody>
            {rewards.map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td>{r.cost_points} pts</td>
                <td>{r.stock}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
