import { PanelSection, PanelSectionRow, staticClasses } from "@decky/ui";

export function HapticTab() {
  return (
    <PanelSection title="Haptic Studio">
      <PanelSectionRow>
        <div className={staticClasses.Text} style={{ opacity: 0.7 }}>
          Coming in v0.0.3 — gain slider with live preview.
        </div>
      </PanelSectionRow>
    </PanelSection>
  );
}
