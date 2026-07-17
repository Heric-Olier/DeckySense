import { Focusable } from "@decky/ui";
import type { SectionDef } from "./registry";

interface Props {
  sections: SectionDef[];
  active: string;
  onSelect: (id: string) => void;
}

/**
 * Top tab bar. Active tab grows and shows its label; inactive tabs
 * are icon-only to stay compact in the narrow QAM width.
 *
 * Each tab is a `Focusable` so the gamepad can navigate between them.
 * `onActivate` fires on gamepad activate (A button) and on click.
 */
export function TabBar({ sections, active, onSelect }: Props) {
  return (
    <Focusable
      style={{
        display: "flex",
        gap: "4px",
        padding: "4px 0 12px",
      }}
    >
      {sections.map((s) => {
        const Icon = s.icon;
        const isActive = s.id === active;
        return (
          <Focusable
            key={s.id}
            onActivate={() => onSelect(s.id)}
            style={{
              flex: isActive ? 1 : "0 0 auto",
              minWidth: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px",
              padding: "8px 10px",
              borderRadius: "4px",
              background: isActive ? "rgba(255,255,255,0.10)" : "transparent",
            }}
          >
            <Icon size={18} />
            {isActive && <span>{s.label}</span>}
          </Focusable>
        );
      })}
    </Focusable>
  );
}
