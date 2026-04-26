import { motion } from "framer-motion";

/** Full-screen splash shown while the backend boots and auth state loads. */
export function SplashScreen() {
  return (
    <div className="relative grid flex-1 place-items-center overflow-hidden">
      {/* radial gold glow */}
      <div
        aria-hidden
        className="absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(201,169,110,0.18) 0%, transparent 60%)",
        }}
      />
      {/* meander stripe top + bottom */}
      <div
        aria-hidden
        className="absolute inset-x-0 top-12 h-5 opacity-50"
        style={{ backgroundImage: "url('/meander.svg')", backgroundRepeat: "repeat-x" }}
      />
      <div
        aria-hidden
        className="absolute inset-x-0 bottom-12 h-5 opacity-50 rotate-180"
        style={{ backgroundImage: "url('/meander.svg')", backgroundRepeat: "repeat-x" }}
      />

      <motion.div
        initial={{ opacity: 0, y: 12, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.55, ease: "easeOut" }}
        className="flex flex-col items-center gap-8"
      >
        <motion.img
          src="/hermes-logo.png"
          alt="Hermes Trading Bot"
          className="h-44 w-auto select-none drop-shadow-md"
          draggable={false}
          animate={{ y: [0, -6, 0] }}
          transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
        />
        <div className="flex flex-col items-center gap-2 text-center">
          <p className="font-serif text-2xl italic text-hermes-navy/60">Ἑρμῆς</p>
          <p className="mt-1 max-w-md text-sm text-hermes-navy/55">
            Бог торговли в облике алгоритма.
            <br />
            Профессиональная автоматическая торговля.
          </p>
        </div>

        <div className="mt-2 flex items-center gap-3 text-[11px] uppercase tracking-[0.3em] text-muted-foreground">
          <span className="h-px w-12 bg-hermes-gold/40" />
          <span>Разработано BAI Core</span>
          <span className="h-px w-12 bg-hermes-gold/40" />
        </div>

        {/* Loading dots */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="flex gap-2"
        >
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className="h-1.5 w-1.5 rounded-full bg-hermes-gold"
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.18 }}
            />
          ))}
        </motion.div>
      </motion.div>
    </div>
  );
}
