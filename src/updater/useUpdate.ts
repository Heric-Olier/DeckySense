import { useCallback, useEffect, useState } from "react";
import {
  checkForUpdate,
  installUpdate,
  restartLoader,
  UpdateStatus,
} from "../api";

// Module-level session guards so multiple consumers (panel + alert dot)
// share the same fetch state without re-checking.
let sessionChecked = false;

const INITIAL: UpdateStatus = { state: "idle", current_version: "" };

export function useUpdate() {
  const [status, setStatus] = useState<UpdateStatus>(INITIAL);

  const check = useCallback(async (force = false) => {
    setStatus((prev) => ({ ...prev, state: "checking" }));
    const result = await checkForUpdate(force);
    setStatus(result);
    sessionChecked = true;
  }, []);

  const install = useCallback(async () => {
    setStatus((prev) => ({ ...prev, state: "installing" }));
    const result = await installUpdate();
    setStatus(result);
  }, []);

  const restart = useCallback(async () => {
    await restartLoader();
    setStatus((prev) => ({ ...prev, state: "restarting" }));
  }, []);

  // Auto-check once per session on first consumer mount.
  useEffect(() => {
    if (!sessionChecked) {
      void check(false);
    }
  }, [check]);

  return { status, check, install, restart };
}
