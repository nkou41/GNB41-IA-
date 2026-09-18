import { useState, useEffect } from 'react';

export default function AnimatedPlaceholder({ text, active }: { text: string; active: boolean }) {
  const [displayed, setDisplayed] = useState('');

  useEffect(() => {
    if (!active) { setDisplayed(''); return; }
    let i = 0;
    let deleting = false;
    let cancelled = false;
    let timeout: ReturnType<typeof setTimeout> | null = null;

    function tick() {
      if (cancelled) return;
      if (!deleting) {
        i++;
        setDisplayed(text.slice(0, i));
        if (i >= text.length) {
          timeout = setTimeout(() => { if (!cancelled) { deleting = true; tick(); } }, 1800);
          return;
        }
        timeout = setTimeout(tick, 45);
      } else {
        i--;
        setDisplayed(text.slice(0, i));
        if (i <= 0) {
          deleting = false;
          timeout = setTimeout(tick, 400);
          return;
        }
        timeout = setTimeout(tick, 20);
      }
    }
    timeout = setTimeout(tick, 300);
    return () => {
      cancelled = true;
      if (timeout) clearTimeout(timeout);
    };
  }, [text, active]);

  return <span className="animated-placeholder" style={{ visibility: active ? 'visible' : 'hidden' }}>{displayed}<span className="animated-cursor">|</span></span>;
}
