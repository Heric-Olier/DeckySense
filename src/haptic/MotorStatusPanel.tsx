import { useEffect, useState } from "react";
import {
  PanelSection,
  PanelSectionRow,
  ToggleField,
  staticClasses,
} from "@decky/ui";
import { getSystemStatus, setFfEnabled, type SystemStatus } from "../api";

/** Small label/value row used across the status panel. */
function StatusRow({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "2px 0",
      }}
    >
      <span style={{ fontSize: "0.8em", opacity: 0.7 }}>{label}</span>
      <span style={{ fontSize: "0.8em", fontWeight: 600 }}>{value}</span>
    </div>
  );
}

/**
 * Live status of the haptic stack: plugin/backend versions, the physical
 * controller's input mode (sysfs) and the InputPlumber FF toggle.
 * Everything is read fail-safe — missing data renders "unknown".
 */
export function MotorStatusPanel() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const s = await getSystemStatus();
      setStatus(s);
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const onToggle = async (value: boolean) => {
    setBusy(true);
    setError(null);
    try {
      const r = await setFfEnabled(value);
      setStatus((s) => (s ? { ...s, ff_enabled: r.enabled } : s));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const modeLabel = status?.controller.mode
    ? status.controller.mode.toUpperCase()
    : "unknown";

  return (
    <PanelSection title="Motor">
      <PanelSectionRow>
        <div>
          <StatusRow
            label="Plugin"
            value={`v${status?.plugin_version ?? "…"}`}
          />
          <StatusRow label="Backend" value={status?.backend.name ?? "…"} />
          <StatusRow label="Controller mode" value={modeLabel} />
        </div>
      </PanelSectionRow>

      <PanelSectionRow>
        <ToggleField
          label="System rumble"
          description="InputPlumber force feedback. Turn it off if an external controller gets duplicated rumble."
          checked={status?.ff_enabled === true}
          disabled={busy || status?.ff_enabled === null}
          onChange={onToggle}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <div
          style={{
            fontSize: "0.7em",
            lineHeight: 1.45,
            opacity: 0.65,
            padding: "2px 0 6px",
          }}
        >
          <b>Firmware vibration level:</b> 4 levels (off / low / medium /
          strong, default medium). Official combo:{" "}
          <b>Legion L + D-pad ↑/↓</b> — unverified on SteamOS so far.
        </div>
      </PanelSectionRow>

      {error && (
        <PanelSectionRow>
          <div
            className={staticClasses.Text}
            style={{ opacity: 0.6, padding: "0 8px" }}
          >
            {error}
          </div>
        </PanelSectionRow>
      )}
    </PanelSection>
  );
}
