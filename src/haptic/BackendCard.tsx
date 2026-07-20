import type { ComponentType } from "react";
import { Focusable } from "@decky/ui";
import type { BackendInfo } from "../api";

interface Props {
  backend: BackendInfo;
  active: boolean;
  onSelect: (id: string) => void;
  icon: ComponentType<{ size?: number }>;
}

const chipBase = {
  flex: 1,
  display: "flex",
  flexDirection: "column" as const,
  alignItems: "center" as const,
  gap: 2,
  padding: "6px 4px",
  borderRadius: 8,
  cursor: "pointer" as const,
  transition: "background 140ms ease, box-shadow 140ms ease",
};

function chipStyle(active: boolean) {
  return {
    ...chipBase,
    background: active
      ? "rgba(255,255,255,0.10)"
      : "rgba(255,255,255,0.04)",
    boxShadow: active
      ? "inset 0 0 0 1.5px rgba(255,255,255,0.35)"
      : "inset 0 0 0 1px rgba(255,255,255,0.06)",
    color: active
      ? "rgba(255,255,255,0.92)"
      : "rgba(255,255,255,0.55)",
  };
}

/**
 * Compact chip — icon + label, accent-highlighted when active.
 * Loosely based on Panel de Control's iconChipStyle / FirmwareModes.
 */
export function BackendCard({ backend, active, onSelect, icon: Icon }: Props) {
  return (
    <Focusable
      onActivate={() => onSelect(backend.id)}
      onClick={() => onSelect(backend.id)}
      style={chipStyle(active)}
    >
      <Icon size={16} />
      <span style={{ fontSize: 10, fontWeight: active ? 600 : 400 }}>
        {backend.name}
      </span>
    </Focusable>
  );
}
