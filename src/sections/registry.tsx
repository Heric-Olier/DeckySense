import type { ComponentType } from "react";
import {
  FaGamepad,
  FaSlidersH,
  FaTachometerAlt,
  FaWrench,
} from "react-icons/fa";
import { DisplayTab } from "./DisplayTab";
import { HapticTab } from "./HapticTab";
import { ProfilesTab } from "./ProfilesTab";
import { SettingsTab } from "./SettingsTab";

export interface SectionDef {
  id: string;
  label: string;
  icon: ComponentType<{ size?: number }>;
  component: ComponentType;
}

/**
 * Single source of truth for the plugin's tabs. To add, remove or
 * reorder sections, edit this array only — the tab bar and the
 * content router both consume it.
 */
export const SECTIONS: SectionDef[] = [
  { id: "display", label: "Display", icon: FaSlidersH, component: DisplayTab },
  { id: "haptic", label: "Haptic", icon: FaTachometerAlt, component: HapticTab },
  { id: "profiles", label: "Profiles", icon: FaGamepad, component: ProfilesTab },
  { id: "settings", label: "Settings", icon: FaWrench, component: SettingsTab },
];
