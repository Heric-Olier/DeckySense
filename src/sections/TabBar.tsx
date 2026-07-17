import { Focusable } from "@decky/ui";
import type { SectionDef } from "./registry";
import { MarqueeText } from "../components/MarqueeText";
import { AlertDot } from "../components/AlertDot";

interface Props {
  sections: SectionDef[];
  active: string;
  onSelect: (id: string) => void;
  /** Per-tab alert dot visibility, keyed by section id. */
  alerts?: Record<string, boolean>;
}

/**
 * Top tab bar. Active tab grows and shows its label (with marquee
 * scroll if it overflows); inactive tabs are icon-only with an
 * optional AlertDot to surface state from any tab.
 *
 * Each tab is a `Focusable` so the gamepad can navigate between them.
 * `onActivate` fires on gamepad activate (A button) and on click.
 *
 * L1/R1 shoulder navigation is wired in `index.tsx` via `useShoulderNav`.
 */
export function TabBar({ sections, active, onSelect, alerts = {} }: Props) {
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
              position: "relative",
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
            {isActive && (
              <MarqueeText
                text={s.label}
                style={{ minWidth: 0, flex: 1 }}
                // MarqueeText forwards `style` if it accepts it.
              />
            )}
            <AlertDot show={!!alerts[s.id]} />
          </Focusable>
        );
      })}
    </Focusable>
  );
}

