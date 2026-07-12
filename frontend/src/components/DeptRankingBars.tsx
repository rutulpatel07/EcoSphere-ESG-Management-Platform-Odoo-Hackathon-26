interface DeptScore {
  department: string;
  total: number;
}

export default function DeptRankingBars({ data }: { data: DeptScore[] }) {
  const ranked = [...data].sort((a, b) => b.total - a.total);

  return (
    <div className="dept-ranking">
      {ranked.map((d, i) => (
        <div className="dept-bar-row" key={d.department}>
          <span className="dept-bar-rank">#{i + 1}</span>
          <span className="dept-bar-label">{d.department}</span>
          <div className="dept-bar-track">
            <div className="dept-bar-fill" style={{ width: `${d.total}%` }} />
          </div>
          <span className="dept-bar-value">{d.total.toFixed(1)}/100</span>
        </div>
      ))}
    </div>
  );
}
