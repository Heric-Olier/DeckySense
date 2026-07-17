import { callable } from "@decky/api";

export type UpdateState =
  | "idle"
  | "checking"
  | "available"
  | "up_to_date"
  | "installing"
  | "done"
  | "error"
  | "restarting";

export interface UpdateStatus {
  state: UpdateState;
  current_version: string;
  latest_version?: string | null;
  release_notes?: string | null;
  asset_url?: string | null;
  error?: string | null;
}

export interface RestartResult {
  state: string;
  error?: string;
}

export const checkForUpdate = callable<[force: boolean], UpdateStatus>(
  "check_for_update"
);
export const installUpdate = callable<[], UpdateStatus>("install_update");
export const restartLoader = callable<[], RestartResult>("restart_loader");
export const getCurrentVersion = callable<[], string>("get_current_version");
