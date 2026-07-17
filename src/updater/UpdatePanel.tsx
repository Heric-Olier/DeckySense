import { useState } from "react";
import {
  ButtonItem,
  PanelSection,
  PanelSectionRow,
  staticClasses,
} from "@decky/ui";
import { useUpdate } from "./useUpdate";
import { UpdateModal } from "./UpdateModal";

export function UpdatePanel() {
  const { status, check } = useUpdate();
  const [modalOpen, setModalOpen] = useState(false);

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
        return "Restart required";
      case "restarting":
        return "Restarting…";
      case "error":
        return "Update failed — retry";
      default:
        return "Check for updates";
    }
  })();

  const onClick = () => {
    if (status.state === "available") {
      setModalOpen(true);
    } else {
      void check(true);
    }
  };

  return (
    <PanelSection title="Updates">
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={onClick}>
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
      <UpdateModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </PanelSection>
  );
}
