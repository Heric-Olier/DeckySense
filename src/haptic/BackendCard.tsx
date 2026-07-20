import { Focusable } from "@decky/ui";
import type { BackendInfo } from "../api";

interface Props {
  backend: BackendInfo;
  active: boolean;
  onSelect: (id: string) => void;
}

const FEATURE_LABELS: Record<string, string> = {
  gain: "Gain slider",
  balance: "Balance slider",
  game_gain: "Gain → Games",
  game_balance: "Balance → Games",
};

/**
 * A selectable card that describes a haptic backend mode.
 * Shows the backend name, a short description, and feature tags.
 */
export function BackendCard({ backend, active, onSelect }: Props) {
  return (
    <Focusable
      onActivate={() => onSelect(backend.id)}
      style={{
        flex: 1,
        minWidth: 0,
        padding: "8px 10px",
        borderRadius: "6px",
        cursor: "pointer",
        background: active
          ? "rgba(255,255,255,0.12)"
          : "rgba(255,255,255,0.04)",
        border: active
          ? "1px solid rgba(255,255,255,0.25)"
          : "1px solid rgba(255,255,255,0.06)",
        transition: "background 0.15s, border 0.15s",
      }}
    >
      <div
        style={{
          fontWeight: 600,
          fontSize: "0.85em",
          marginBottom: "3px",
        }}
      >
        {backend.name}
      </div>
      <div
        style={{
          fontSize: "0.7em",
          opacity: 0.65,
          lineHeight: 1.3,
          marginBottom: "5px",
        }}
      >
        {backend.description}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "3px" }}>
        {backend.features.map((f) => (
          <span
            key={f}
            style={{
              fontSize: "0.6em",
              padding: "1px 5px",
              borderRadius: "3px",
              background: active
                ? "rgba(255,255,255,0.15)"
                : "rgba(255,255,255,0.06)",
              opacity: 0.8,
            }}
          >
            {FEATURE_LABELS[f] ?? f}
          </span>
        ))}
      </div>
    </Focusable>
  );
}
