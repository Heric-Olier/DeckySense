import { useEffect, useState } from "react";
import { DialogButton, ModalRoot } from "@decky/ui";
import { useUpdate } from "./useUpdate";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function UpdateModal({ open, onClose }: Props) {
  const { status, install, restart } = useUpdate();
  const [installing, setInstalling] = useState(false);

  useEffect(() => {
    if (status.state !== "installing") setInstalling(false);
  }, [status.state]);

  return (
    <ModalRoot open={open} onClose={onClose} header="Update DeckSense">
      {status.state === "available" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div>A new version is available: v{status.latest_version}</div>
          {status.release_notes && (
            <pre
              style={{
                whiteSpace: "pre-wrap",
                margin: 0,
                maxHeight: "300px",
                overflow: "auto",
                background: "rgba(255,255,255,0.05)",
                padding: "8px",
                borderRadius: "4px",
              }}
            >
              {status.release_notes}
            </pre>
          )}
          <DialogButton
            disabled={installing}
            onClick={async () => {
              setInstalling(true);
              await install();
            }}
          >
            {installing ? "Installing…" : "Install update"}
          </DialogButton>
        </div>
      )}

      {status.state === "done" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div>Update installed. Restart the plugin loader to apply.</div>
          <DialogButton
            onClick={async () => {
              await restart();
              onClose();
            }}
          >
            Restart now
          </DialogButton>
        </div>
      )}

      {status.state === "error" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div>Update failed.</div>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
            {status.error}
          </pre>
        </div>
      )}
    </ModalRoot>
  );
}
