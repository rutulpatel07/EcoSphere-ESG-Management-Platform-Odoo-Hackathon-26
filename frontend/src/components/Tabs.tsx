import { ReactNode, useState } from "react";

export interface TabItem {
  key: string;
  label: string;
  content: ReactNode;
}

export default function Tabs({ items, initialKey }: { items: TabItem[]; initialKey?: string }) {
  const [active, setActive] = useState(initialKey ?? items[0]?.key);
  const activeItem = items.find((item) => item.key === active) ?? items[0];

  return (
    <div>
      <div className="tabs-bar" role="tablist">
        {items.map((item) => (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={item.key === active}
            className={"tab-btn" + (item.key === active ? " tab-btn--active" : "")}
            onClick={() => setActive(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="tab-panel">{activeItem?.content}</div>
    </div>
  );
}
