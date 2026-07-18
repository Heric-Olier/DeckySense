import { useEffect, useRef, useState } from "react";
import {
  ButtonItem,
  PanelSection,
  PanelSectionRow,
  SliderField,
  staticClasses,
} from "@decky/ui";
import {
  debugHapticTest,
  getHapticParams,
  previewRumble,
  setHapticGain,
  stopRumble,
  type DebugInfo,
} from "../api";

const PREVIEW_INTENSITY = 0.5;

/**
 * Haptic Studio — global gain control with live preview.
 *
 * The slider sets the persisted gain multiplier; the Preview button
 * fires a single rumble at `PREVIEW_INTENSITY * gain` so the user can
 * feel the effect of their setting instantly. Stop cancels an ongoing
 * rumble.
 *
 * Backend path: InputPlumber D-Bus Rumble(double) on CompositeDevice0.
 */
export function GainPanel() {
  const [gain, setGain] = useState(1.0);
  const [previewing, setPreviewing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [debug, setDebug] = useState<string | null>(null);
  const stopTimeoutRef = useRef<number | null>(null);

  // Load persisted gain on mount.
  useEffect(() => {
    void (async () => {
      const params = await getHapticParams();
      setGain(params.gain);
    })();
    return () => {
      if (stopTimeoutRef.current !== null) {
        window.clearTimeout(stopTimeoutRef.current);
      }
    };
  }, []);

  const onChange = async (value: number) => {
    setGain(value);
    setError(null);
    try {
      await setHapticGain(value);
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
    // Auto-stop preview after 1.2s so it can't run forever.
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

  return (
    <PanelSection title="Haptic Studio">
      <PanelSectionRow>
        <SliderField
          label="Global gain"
          value={gain}
          min={0}
          max={2}
          step={0.05}
          onChange={onChange}
          description={`${gain.toFixed(2)}× multiplier applied to rumble intensity`}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={previewing ? onStop : onPreview}>
          {previewing ? "Stop preview" : `Preview at ${(PREVIEW_INTENSITY * gain).toFixed(2)} intensity`}
        </ButtonItem>
      </PanelSectionRow>
      {error && (
        <PanelSectionRow>
          <div className={staticClasses.Text} style={{ opacity: 0.6, padding: "0 8px" }}>
            {error}
          </div>
        </PanelSectionRow>
      )}
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
