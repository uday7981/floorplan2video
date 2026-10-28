/**
 * Flips `html.fonts-ready` once the critical display face has actually painted.
 * Combined with .font-gate CSS, this prevents any flash of fallback serif.
 */
export function FontGateScript() {
  return (
    <script
      // Must inline + run before React hydrates to catch cached-font case.
      dangerouslySetInnerHTML={{
        __html: `
          (function () {
            function ready() { document.documentElement.classList.add('fonts-ready'); }
            if (document.fonts && document.fonts.ready) {
              document.fonts.ready.then(ready).catch(ready);
              // Safety: if fonts never resolve (offline + unsupported), unhide at 1s.
              setTimeout(ready, 1000);
            } else {
              ready();
            }
          })();
        `,
      }}
    />
  );
}
