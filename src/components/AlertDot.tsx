interface Props {
  show: boolean;
  color?: string;
  size?: number;
}

/**
 * Small coloured dot badge for tab icons. Used to surface state
 * (e.g. "an update is available") so the user sees it from any tab,
 * not just the one where the state originated.
 *
 * Render inside a `position: relative` parent; AlertDot is positioned
 * absolutely to its top-right corner.
 */
export function AlertDot({ show, color = "#5f6cff", size = 8 }: Props) {
  if (!show) return null;
  return (
    <span
      style={{
        position: "absolute",
        top: -size / 4,
        right: -size / 4,
        width: size,
        height: size,
        borderRadius: "50%",
        background: color,
        boxShadow: `0 0 4px ${color}`,
        pointerEvents: "none",
      }}
    />
  );
}
