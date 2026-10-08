import { useState } from "react";
import {
  ButtonItem,
  PanelSection,
  PanelSectionRow,
  staticClasses,
} from "@decky/ui";
import { useUpdate } from "./useUpdate";
import { UpdateModal } from "./UpdateModal";

/**
 * Inline update flow: one status line + one contextual button; the full
 * notes/install flow lives in the modal. No progress bar — coarse states
 * only, and the label always reflects exactly what the next click does.
 */
export function UpdatePanel() {
  const { view, check, restart } = useUpdate();
  const [modalOpen, setModalOpen] = useState(false);
  const { phase, info, error } = view;
  const current = info?.current ?? "";

  const statusLine = (() => {
    switch (phase) {
      case "checking":
        return current ? `Version ${current} · checking…` : "Checking…";
      case "available":
        return `Version ${current} · new v${info?.latest} available`;
      case "up_to_date":
        return `Version ${current} · up to date`;
      case "installing":
        return "Installing…";
      case "done":
        return "Update installed — restart Decky to apply";
      case "error":
        return "Update check failed";
      default:
        return current ? `Version ${current}` : "";
    }
  })();

  const label = (() => {
    switch (phase) {
      case "checking":
        return "Checking…";
      case "available":
        return `View v${info?.latest} notes & install`;
      case "installing":
        return "Installing…";
      case "done":
        return "Restart Decky";
      default:
        return "Check for updates";
    }
  })();

  const disabled = phase === "checking" || phase === "installing";

  const onButton = async () => {
    if (phase === "available") {
      setModalOpen(true);
      return;
    }
    if (phase === "done") {
      await restart();
      return;
    }
    if (disabled) return;
    await check(true);
  };

  return (
    <PanelSection title="Updates">
      <PanelSectionRow>
        <div
          className={staticClasses.Text}
          style={{ opacity: 0.8, padding: "0 8px", fontSize: "0.9em" }}
        >
          {statusLine}
        </div>
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" disabled={disabled} onClick={onButton}>
          {label}
        </ButtonItem>
      </PanelSectionRow>
      {phase === "error" && error && (
        <PanelSectionRow>
          <div
            className={staticClasses.Text}
            style={{ opacity: 0.6, padding: "0 8px", fontSize: "0.85em" }}
          >
            {error === "network" ? "Could not reach GitHub. Try again." : error}
          </div>
        </PanelSectionRow>
      )}
      <UpdateModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </PanelSection>
  );
}
