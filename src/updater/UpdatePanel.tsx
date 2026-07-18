import {
  ButtonItem,
  PanelSection,
  PanelSectionRow,
  staticClasses,
} from "@decky/ui";
import { useUpdate } from "./useUpdate";

/**
 * Inline update flow: a single button whose label and action depend on
 * the current update state. No modal — fewer moving parts, less to
 * break in the narrow QAM width.
 *
 * - idle / error → "Check for updates" / "Update failed — retry"
 * - checking → disabled "Checking…"
 * - available → "Update to v<latest>" → install()
 * - installing → disabled "Installing…"
 * - done → "Installed. Restart." → restart()
 * - restarting → disabled "Restarting…"
 */
export function UpdatePanel() {
  const { status, check, install, restart } = useUpdate();

  const onButtonClick = async () => {
    if (status.state === "available") {
      await install();
    } else if (status.state === "done") {
      await restart();
    } else if (status.state === "checking" || status.state === "installing" || status.state === "restarting") {
      // No-op while a transition is in flight.
      return;
    } else {
      await check(true);
    }
  };

  const label = (() => {
    switch (status.state) {
      case "checking":
        return "Checking…";
      case "up_to_date":
        return `Up to date (v${status.current_version})`;
      case "available":
        return `Update to v${status.latest_version}`;
      case "installing":
        return "Installing…";
      case "done":
        return "Installed. Restart.";
      case "restarting":
        return "Restarting…";
      case "error":
        return "Update failed — retry";
      default:
        return "Check for updates";
    }
  })();

  const isDisabled =
    status.state === "checking" ||
    status.state === "installing" ||
    status.state === "restarting";

  return (
    <PanelSection title="Updates">
      <PanelSectionRow>
        <ButtonItem layout="below" disabled={isDisabled} onClick={onButtonClick}>
          {label}
        </ButtonItem>
      </PanelSectionRow>
      {status.state === "error" && status.error && (
        <PanelSectionRow>
          <div
            className={staticClasses.Text}
            style={{ opacity: 0.6, padding: "0 8px" }}
          >
            {status.error}
          </div>
        </PanelSectionRow>
      )}
      {status.release_notes && status.state === "available" && (
        <PanelSectionRow>
          <pre
            style={{
              whiteSpace: "pre-wrap",
              margin: 0,
              maxHeight: "180px",
              overflow: "auto",
              background: "rgba(255,255,255,0.05)",
              padding: "8px",
              borderRadius: "4px",
              fontSize: "0.85em",
            }}
          >
            {status.release_notes}
          </pre>
        </PanelSectionRow>
      )}
    </PanelSection>
  );
}
