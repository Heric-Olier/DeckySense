import { PanelSection, PanelSectionRow, staticClasses } from "@decky/ui";

export function DisplayTab() {
  return (
    <PanelSection title="Display Studio">
      <PanelSectionRow>
        <div className={staticClasses.Text} style={{ opacity: 0.7 }}>
          Coming in v0.0.3 — first presets (Sharp, OLED-like).
        </div>
      </PanelSectionRow>
    </PanelSection>
  );
}
