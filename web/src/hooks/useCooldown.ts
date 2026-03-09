"use client";

import { useCallback, useRef, useState } from "react";

export function useCooldown(durationMs: number = 10000) {
  const [isCoolingDown, setIsCoolingDown] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const startCooldown = useCallback(() => {
    setIsCoolingDown(true);

    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(() => {
      setIsCoolingDown(false);
      timerRef.current = null;
    }, durationMs);
  }, [durationMs]);

  return { isCoolingDown, startCooldown };
}
