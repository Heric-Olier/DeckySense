import { useCallback, useEffect, useState } from "react";
import { toaster } from "@decky/api";
import {
  checkForUpdate,
  installUpdate,
  restartLoader,
  UpdateInfo,
} from "../api";

export type UpdatePhase =
  | "idle"
  | "checking"
  | "available"
  | "up_to_date"
  | "installing"
  | "done"
  | "error";

export interface UpdateView {
  phase: UpdatePhase;
  info: UpdateInfo | null;
  error: string;
}

// Module-level shared state. The QAM panel, the update modal and the tab
// badge live in separate React trees (each modal renders its own document),
// so a per-hook useState would desync them. One store, many subscribers.
let shared: UpdateView = { phase: "idle", info: null, error: "" };
const listeners = new Set<(v: UpdateView) => void>();

function setShared(next: UpdateView) {
  shared = next;
  listeners.forEach((fn) => fn(next));
}

// Session guards survive remounts: at most one GitHub check and one toast
// per plugin process. The backend additionally caches the result.
let sessionChecked = false;
let sessionToasted = false;

export function useUpdate() {
  const [view, setView] = useState<UpdateView>(shared);

  useEffect(() => {
    listeners.add(setView);
    setView(shared); // catch up with state set before this mount
    return () => {
      listeners.delete(setView);
    };
  }, []);

  const check = useCallback(async (force = false) => {
    setShared({ ...shared, phase: "checking", error: "" });
    try {
      const info = await checkForUpdate(force);
      if (info.error) {
        setShared({ phase: "error", info, error: info.error });
        return;
      }
      if (info.has_update) {
        setShared({ phase: "available", info, error: "" });
        if (!sessionToasted) {
          sessionToasted = true;
          toaster.toast({
            title: "DeckySense update available",
            body: `v${info.latest} is ready to install.`,
          });
        }
      } else {
        setShared({ phase: "up_to_date", info, error: "" });
      }
    } catch (e) {
      setShared({ phase: "error", info: null, error: String(e) });
    }
  }, []);

  const install = useCallback(async () => {
    setShared({ ...shared, phase: "installing" });
    try {
      const res = await installUpdate();
      if (res.ok) {
        setShared({ phase: "done", info: shared.info, error: "" });
        return true;
      }
      setShared({ ...shared, phase: "error", error: res.message });
      return false;
    } catch (e) {
      setShared({ ...shared, phase: "error", error: String(e) });
      return false;
    }
  }, []);

  const restart = useCallback(async () => {
    await restartLoader();
  }, []);

  // Auto-check on first mount (module guard keeps it to once per session).
  useEffect(() => {
    if (sessionChecked) return;
    sessionChecked = true;
    void check(false);
  }, [check]);

  return { view, check, install, restart };
}
