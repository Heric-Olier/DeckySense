import { GainPanel } from "../haptic/GainPanel";
import { MotorStatusPanel } from "../haptic/MotorStatusPanel";

export function HapticTab() {
  return (
    <>
      <MotorStatusPanel />
      <GainPanel />
    </>
  );
}
