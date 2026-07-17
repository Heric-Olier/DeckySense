import { useEffect, useRef, useState, type CSSProperties } from "react";

interface Props {
  text: string;
  className?: string;
  style?: CSSProperties;
  /** Pause between scroll directions, in ms. Default 800. */
  pause?: number;
  /** Pixels-per-second scroll speed. Default 40. */
  speed?: number;
}

/**
 * Ping-pong scrolling text for the narrow QAM width.
 *
 * Only animates when the text overflows its container by more than 2px.
 * Uses the Web Animations API on a single transform property so the
 * work stays on the compositor thread and doesn't trigger React
 * re-renders per frame.
 *
 * Adapted from Panel de Control's MarqueeText.
 */
export function MarqueeText({ text, className, style, pause = 800, speed = 40 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  const [needsScroll, setNeedsScroll] = useState(false);

  useEffect(() => {
    const c = containerRef.current;
    const t = textRef.current;
    if (!c || !t) return;

    const overflow = t.scrollWidth - c.clientWidth;
    if (overflow <= 2) {
      setNeedsScroll(false);
      return;
    }

    setNeedsScroll(true);
    const distance = overflow;
    const travelMs = (distance / speed) * 1000;
    const halfPeriod = travelMs + pause;

    const anim = t.animate(
      [
        { transform: "translateX(0)" },
        { transform: `translateX(${-distance}px)` },
      ],
      {
        duration: halfPeriod,
        iterations: Infinity,
        direction: "alternate",
        easing: "ease-in-out",
      }
    );

    return () => anim.cancel();
  }, [text, pause, speed]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        overflow: "hidden",
        whiteSpace: "nowrap",
        position: "relative",
        ...style,
      }}
    >
      <span ref={textRef} style={{ display: "inline-block", willChange: needsScroll ? "transform" : "auto" }}>
        {text}
      </span>
    </div>
  );
}
