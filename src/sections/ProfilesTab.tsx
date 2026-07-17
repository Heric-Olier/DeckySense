import { PanelSection, PanelSectionRow, staticClasses } from "@decky/ui";

export function ProfilesTab() {
  return (
    <PanelSection title="Game Profiles">
      <PanelSectionRow>
        <div className={staticClasses.Text} style={{ opacity: 0.7 }}>
          Coming in a later phase.
        </div>
      </PanelSectionRow>
    </PanelSection>
  );
}
