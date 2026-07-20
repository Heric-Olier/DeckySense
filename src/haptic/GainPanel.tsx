import { useEffect, useRef, useState } from "react";
import {
  ButtonItem,
  Focusable,
  PanelSection,
  PanelSectionRow,
  SliderField,
  staticClasses,
} from "@decky/ui";
import {
  getHapticBackendInfo,
  getHapticParams,
  listHapticBackends,
  previewRumble,
  setHapticBalance,
  setHapticGain,
  stopRumble,
  switchHapticBackend,
  type BackendInfo,
  type DebugInfo,
  debugHapticTest,
} from "../api";
import { BackendCard } from "./BackendCard";

const PREVIEW_INTENSITY = 0.5;

/**
 * Haptic Studio — backend mode selector + gain/balance controls.
 *
 * The user picks a backend mode (three cards at the top), then adjusts
 * gain/balance.  Controls adapt: balance slider is only shown when the
 * active backend supports it.  A feature summary tells the user what
 * each mode can do.
 */
export function GainPanel() {
  // ── backend list ────────────────────────────────────────────────
  const [backends, setBackends] = useState<BackendInfo[]>([]);
  const [activeBackend, setActiveBackend] = useState<BackendInfo | null>(null);
  const [switching, setSwitching] = useState(false);

  // ── gain/balance ────────────────────────────────────────────────
  const [gain, setGain] = useState(1.0);
  const [balance, setBalance] = useState(0.5);
  const [previewing, setPreviewing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [debug, setDebug] = useState<string | null>(null);
  const stopTimeoutRef = useRef<number | null>(null);

  // Load everything on mount
  useEffect(() => {
    void (async () => {
      const [bList, active, params] = await Promise.all([
        listHapticBackends(),
        getHapticBackendInfo(),
        getHapticParams(),
      ]);
      setBackends(bList);
      setActiveBackend(active);
      setGain(params.gain);
      setBalance(params.balance);
    })();
    return () => {
      if (stopTimeoutRef.current !== null) {
        window.clearTimeout(stopTimeoutRef.current);
      }
    };
  }, []);

  // ── helpers ─────────────────────────────────────────────────────

  const hasFeature = (f: string) => activeBackend?.features.includes(f) ?? false;

  const onBackendSelect = async (id: string) => {
    if (id === activeBackend?.id || switching) return;
    setSwitching(true);
    setError(null);
    try {
      const info = await switchHapticBackend(id);
      setActiveBackend(info);
    } catch (e) {
      setError(String(e));
    } finally {
      setSwitching(false);
    }
  };

  const onGainChange = async (value: number) => {
    setGain(value);
    setError(null);
    try {
      await setHapticGain(value);
    } catch (e) {
      setError(String(e));
    }
  };

  const onBalanceChange = async (value: number) => {
    setBalance(value);
    setError(null);
    try {
      await setHapticBalance(value);
    } catch (e) {
      setError(String(e));
    }
  };

  const onPreview = async () => {
    setError(null);
    const result = await previewRumble(PREVIEW_INTENSITY);
    if (result.state === "error") {
      setError(result.error ?? "unknown error");
      return;
    }
    setPreviewing(true);
    if (stopTimeoutRef.current !== null) {
      window.clearTimeout(stopTimeoutRef.current);
    }
    stopTimeoutRef.current = window.setTimeout(async () => {
      await onStop();
    }, 1200);
  };

  const onStop = async () => {
    if (stopTimeoutRef.current !== null) {
      window.clearTimeout(stopTimeoutRef.current);
      stopTimeoutRef.current = null;
    }
    await stopRumble();
    setPreviewing(false);
  };

  // ── render ──────────────────────────────────────────────────────

  return (
    <PanelSection title="Haptic Studio">
      {/* Mode selector */}
      <PanelSectionRow>
        <Focusable
          style={{
            display: "flex",
            gap: "6px",
            marginBottom: "8px",
          }}
        >
          {backends.map((b) => (
            <BackendCard
              key={b.id}
              backend={b}
              active={b.id === activeBackend?.id}
              onSelect={onBackendSelect}
            />
          ))}
        </Focusable>
      </PanelSectionRow>

      {/* Feature summary for the active backend */}
      {activeBackend && (
        <PanelSectionRow>
          <div
            style={{
              display: "flex",
              gap: "8px",
              fontSize: "0.7em",
              opacity: 0.7,
              padding: "0 2px 8px",
              flexWrap: "wrap",
            }}
          >
            <span>
              Preview gain:{" "}
              <span style={{ fontWeight: 600 }}>
                {hasFeature("gain") ? "[YES]" : "[NO]"}
              </span>
            </span>
            <span>
              Preview balance:{" "}
              <span style={{ fontWeight: 600 }}>
                {hasFeature("balance") ? "[YES]" : "[NO]"}
              </span>
            </span>
            <span>
              Game gain:{" "}
              <span style={{ fontWeight: 600 }}>
                {hasFeature("game_gain") ? "[YES]" : "[NO]"}
              </span>
            </span>
            <span>
              Game balance:{" "}
              <span style={{ fontWeight: 600 }}>
                {hasFeature("game_balance") ? "[YES]" : "[NO]"}
              </span>
            </span>
          </div>
        </PanelSectionRow>
      )}

      {/* Gain slider (always shown) */}
      <PanelSectionRow>
        <SliderField
          label="Gain"
          value={gain}
          min={0}
          max={2}
          step={0.05}
          onChange={onGainChange}
          description={`${gain.toFixed(2)}× multiplier`}
        />
      </PanelSectionRow>

      {/* Balance slider (only when supported) */}
      {hasFeature("balance") && (
        <PanelSectionRow>
          <SliderField
            label="Motor balance"
            value={balance}
            min={0}
            max={1}
            step={0.05}
            onChange={onBalanceChange}
            description={
              balance < 0.33
                ? "Light / buzzy"
                : balance > 0.66
                  ? "Deep / heavy"
                  : "Balanced"
            }
          />
        </PanelSectionRow>
      )}

      {/* Preview */}
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={previewing ? onStop : onPreview}>
          {previewing
            ? "Stop preview"
            : `Preview at ${(PREVIEW_INTENSITY * gain).toFixed(2)} intensity`}
        </ButtonItem>
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

      {/* Debug */}
      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={async () => {
            const r: DebugInfo = await debugHapticTest();
            setDebug(JSON.stringify(r, null, 2));
          }}
        >
          Run haptic debug
        </ButtonItem>
      </PanelSectionRow>
      {debug && (
        <PanelSectionRow>
          <pre
            style={{
              whiteSpace: "pre-wrap",
              margin: 0,
              background: "rgba(255,255,255,0.05)",
              padding: "8px",
              borderRadius: "4px",
              fontSize: "0.8em",
            }}
          >
            {debug}
          </pre>
        </PanelSectionRow>
      )}
    </PanelSection>
  );
}
