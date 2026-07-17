import { useState } from "react";
import { staticClasses } from "@decky/ui";
import { definePlugin } from "@decky/api";
import { FaTachometerAlt } from "react-icons/fa";
import { SECTIONS } from "./sections/registry";
import { TabBar } from "./sections/TabBar";

function Content() {
  const [active, setActive] = useState(SECTIONS[0].id);
  const activeSection = SECTIONS.find((s) => s.id === active) ?? SECTIONS[0];
  const Active = activeSection.component;

  return (
    <>
      <TabBar sections={SECTIONS} active={active} onSelect={setActive} />
      <Active />
    </>
  );
}

export default definePlugin(() => {
  return {
    name: "DeckySense",
    titleView: <div className={staticClasses.Title}>DeckySense</div>,
    content: <Content />,
    icon: <FaTachometerAlt />,
    onDismount() {},
  };
});
