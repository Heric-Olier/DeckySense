import { useEffect, useState } from "react";
import { DialogButton, Focusable, ModalRoot } from "@decky/ui";
import { useUpdate } from "./useUpdate";

interface Props {
  open: boolean;
  onClose: () => void;
}

/**
 * Update modal: aggregated release notes (every version since the one
 * installed), then install → restart. The state is shared with the panel
 * and the tab badge through useUpdate's module-level store, so installing
 * here immediately updates the rest of the UI.
 */
export function UpdateModal({ open, onClose }: Props) {
  const { view, install, restart } = useUpdate();
  const { phase, info, error } = view;
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (phase !== "installing") setBusy(false);
  }, [phase]);

  return (
    <ModalRoot open={open} onClose={onClose} bAllowFullSize>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "12px",
          minWidth: 0,
        }}
      >
        {(phase === "available" || phase === "idle" || phase === "checking") && (
          <>
            <div>
              DeckySense v{info?.latest ?? "…"} is available (you have v
              {info?.current ?? "…"}).
            </div>
            {info?.notes ? (
              <Focusable
                style={{
                  maxHeight: "300px",
                  overflow: "auto",
                  background: "rgba(255,255,255,0.05)",
                  borderRadius: "4px",
                  padding: "8px",
                }}
              >
                <pre
                  style={{
                    whiteSpace: "pre-wrap",
                    margin: 0,
                    fontSize: "0.85em",
                  }}
                >
                  {info.notes}
                </pre>
              </Focusable>
            ) : (
              <div style={{ opacity: 0.7 }}>
                No release notes for this version.
              </div>
            )}
            <DialogButton
              disabled={busy || phase === "checking"}
              onClick={async () => {
                setBusy(true);
                await install();
              }}
            >
              {busy ? "Installing…" : "Install update"}
            </DialogButton>
          </>
        )}

        {phase === "installing" && <div>Installing…</div>}

        {phase === "done" && (
          <>
            <div>Update installed. Restart Decky to apply it.</div>
            <DialogButton
              onClick={async () => {
                await restart();
                onClose();
              }}
            >
              Restart Decky
            </DialogButton>
          </>
        )}

        {phase === "error" && (
          <>
            <div style={{ color: "#ff8a80" }}>Something went wrong.</div>
            <div style={{ opacity: 0.7, fontSize: "0.85em" }}>{error}</div>
            <DialogButton onClick={onClose}>Close</DialogButton>
          </>
        )}
      </div>
    </ModalRoot>
  );
}
