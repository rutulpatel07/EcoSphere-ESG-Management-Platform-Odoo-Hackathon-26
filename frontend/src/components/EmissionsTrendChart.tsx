interface TrendPoint {
  month: string;
  scope1: number;
  scope2: number;
  scope3: number;
}

const SCOPE_COLORS = {
  scope1: "var(--pillar-e)",
  scope2: "#5fb98c",
  scope3: "#a7dcc1",
} as const;

const CHART_HEIGHT = 160;

export default function EmissionsTrendChart({ data }: { data: TrendPoint[] }) {
  const max = Math.max(...data.map((d) => d.scope1 + d.scope2 + d.scope3));

  return (
    <div className="emissions-chart">
      <div className="emissions-chart-bars">
        {data.map((point) => {
          const total = point.scope1 + point.scope2 + point.scope3;
          const scale = CHART_HEIGHT / max;
          return (
            <div className="emissions-chart-col" key={point.month}>
              <div className="emissions-chart-total">{total}</div>
              <div className="emissions-chart-stack" style={{ height: CHART_HEIGHT }}>
                <div
                  className="emissions-chart-seg"
                  style={{ height: point.scope3 * scale, background: SCOPE_COLORS.scope3 }}
                  title={`Scope 3: ${point.scope3}`}
                />
                <div
                  className="emissions-chart-seg"
                  style={{ height: point.scope2 * scale, background: SCOPE_COLORS.scope2 }}
                  title={`Scope 2: ${point.scope2}`}
                />
                <div
                  className="emissions-chart-seg"
                  style={{ height: point.scope1 * scale, background: SCOPE_COLORS.scope1 }}
                  title={`Scope 1: ${point.scope1}`}
                />
              </div>
              <div className="emissions-chart-month">{point.month}</div>
            </div>
          );
        })}
      </div>
      <div className="emissions-chart-legend">
        <span><i style={{ background: SCOPE_COLORS.scope1 }} /> Scope 1</span>
        <span><i style={{ background: SCOPE_COLORS.scope2 }} /> Scope 2</span>
        <span><i style={{ background: SCOPE_COLORS.scope3 }} /> Scope 3</span>
      </div>
    </div>
  );
}
