/**
 * No-op stand-in for framer-motion.
 *
 * v1.0.37: aliased via vite.config.ts so that the entire codebase
 * keeps its `import { motion, AnimatePresence, ... } from "framer-motion"`
 * imports, but at runtime nothing animates. Every `<motion.div>` resolves
 * to a plain `<div>`, AnimatePresence is a fragment, the hooks return
 * inert primitives. Trace logs (v1.0.36) finally narrowed the
 * boot-time renderer crash to framer-motion's per-frame work piling
 * up under WebView2 with --disable-gpu - removing the library
 * entirely is the cleanest way to confirm + fix.
 */
import * as React from "react";

type AnyProps = Record<string, unknown>;

const FRAMER_PROP_NAMES = new Set<string>([
  "initial",
  "animate",
  "exit",
  "transition",
  "variants",
  "layout",
  "layoutId",
  "layoutDependency",
  "layoutScroll",
  "whileHover",
  "whileTap",
  "whileFocus",
  "whileDrag",
  "whileInView",
  "viewport",
  "drag",
  "dragConstraints",
  "dragElastic",
  "dragMomentum",
  "dragSnapToOrigin",
  "dragTransition",
  "onDrag",
  "onDragStart",
  "onDragEnd",
  "onPan",
  "onPanStart",
  "onPanEnd",
  "onAnimationStart",
  "onAnimationComplete",
  "onUpdate",
  "onHoverStart",
  "onHoverEnd",
  "onTap",
  "onTapStart",
  "onTapCancel",
  "custom",
  "inherit",
  "transformTemplate",
  "transformValues",
  "originX",
  "originY",
  "originZ",
  "perspective",
  "style",
]);

function stripFramerProps(props: AnyProps): AnyProps {
  const out: AnyProps = {};
  for (const k in props) {
    if (k === "style") {
      // Style is fine to keep, but framer-motion's style values include
      // MotionValue objects we can't render. Strip those.
      const s = props.style as Record<string, unknown> | undefined;
      if (s) {
        const cleaned: Record<string, unknown> = {};
        for (const sk in s) {
          const v = s[sk];
          if (v != null && typeof v === "object" && "get" in (v as object)) continue;
          cleaned[sk] = v;
        }
        out.style = cleaned;
      }
      continue;
    }
    if (FRAMER_PROP_NAMES.has(k)) continue;
    out[k] = props[k];
  }
  return out;
}

function passthrough(tag: keyof React.JSX.IntrinsicElements) {
  return React.forwardRef<unknown, AnyProps>((props, ref) =>
    React.createElement(tag, { ...stripFramerProps(props), ref }),
  );
}

// `motion` in framer-motion is callable like `motion.div`, `motion.span`, etc.
// Use a Proxy so any tag is supported without an explicit list.
const motionTarget = {} as Record<string, React.ComponentType<AnyProps>>;
export const motion = new Proxy(motionTarget, {
  get(target, prop: string) {
    if (!target[prop]) {
      target[prop] = passthrough(prop as keyof React.JSX.IntrinsicElements);
    }
    return target[prop];
  },
}) as unknown as Record<string, React.ComponentType<AnyProps>>;

// AnimatePresence: just render children. Children won't get exit animations,
// but they also won't get unmount-delay hangs - WebView2 likes this better.
export function AnimatePresence({ children }: { children?: React.ReactNode }) {
  return React.createElement(React.Fragment, null, children);
}

// MotionConfig: no-op provider.
export function MotionConfig({ children }: { children?: React.ReactNode }) {
  return React.createElement(React.Fragment, null, children);
}

// Hooks. These need to be valid React hooks (call useState/useRef under the
// hood) so the rules-of-hooks check stays happy.
export function useMotionValue<T>(initial: T) {
  const ref = React.useRef(initial);
  return {
    get: () => ref.current,
    set: (v: T) => {
      ref.current = v;
    },
    onChange: () => () => undefined,
    on: () => () => undefined,
  };
}

export function useTransform<O>(_input: unknown, _ranges: unknown, _outputs?: unknown, _opts?: unknown): {
  get(): O;
  set(v: O): void;
  onChange(): () => void;
} {
  return {
    get: () => undefined as unknown as O,
    set: () => undefined,
    onChange: () => () => undefined,
  };
}

export function useSpring<T>(input: T): T {
  return input;
}

export function useAnimation() {
  return {
    start: () => Promise.resolve(),
    stop: () => undefined,
    set: () => undefined,
  };
}

export function useAnimationControls() {
  return useAnimation();
}

export function useInView() {
  return false;
}

export function useScroll() {
  return {
    scrollX: useMotionValue(0),
    scrollY: useMotionValue(0),
    scrollXProgress: useMotionValue(0),
    scrollYProgress: useMotionValue(0),
  };
}

export function useDragControls() {
  return {
    start: () => undefined,
  };
}

// Misc named exports referenced occasionally in framer-motion docs.
export const LayoutGroup = MotionConfig;
export const LazyMotion = MotionConfig;
export const Reorder = motion;
export const domAnimation = {};
export const domMax = {};

// Default export — framer-motion's default is `motion`.
const defaultExport = { motion, AnimatePresence, MotionConfig };
export default defaultExport;
