import { useEffect, useRef } from "react";
import { cycleTab } from "./nav";

interface Options {
  ids: string[];
  active: string;
  onSelect: (id: string) => void;
}

/**
 * L1/R1 (SteamOS bumpers — "shoulders") to cycle tabs.
 *
 * The listener is registered once on mount. Refs keep `ids`, `active`
 * and `onSelect` fresh inside the callback without re-registering.
 *
 * Degrades silently when `SteamClient.Input.RegisterForControllerInputMessages`
 * is unavailable (non-Steam runtime, future API change, etc.).
 *
 * Button ids: 30 = LSHOULDER, 31 = RSHOULDER (per Steam Input).
 */
// SteamClient is declared globally by @decky/ui. We cast to any to read
// the optional Input.RegisterForControllerInputMessages method, which is
// not always present in the typed surface.
const SC = (SteamClient as unknown as {
  Input?: {
    RegisterForControllerInputMessages?: (
      cb: (msg: { button?: number }) => void
    ) => () => void;
  };
});

export function useShoulderNav({ ids, active, onSelect }: Options) {
  const idsRef = useRef(ids);
  const activeRef = useRef(active);
  const onSelectRef = useRef(onSelect);

  idsRef.current = ids;
  activeRef.current = active;
  onSelectRef.current = onSelect;

  useEffect(() => {
    const register = SC.Input?.RegisterForControllerInputMessages;
    if (typeof register !== "function") return;

    let unregister: (() => void) | undefined;
    try {
      unregister = register.call(SC.Input, (msg) => {
        if (msg?.button === 30) {
          onSelectRef.current(cycleTab(idsRef.current, activeRef.current, -1));
        } else if (msg?.button === 31) {
          onSelectRef.current(cycleTab(idsRef.current, activeRef.current, 1));
        }
      });
    } catch {
      // Silent degradation.
    }

    return () => {
      try {
        unregister?.();
      } catch {
        // ignore
      }
    };
  }, []);
}
