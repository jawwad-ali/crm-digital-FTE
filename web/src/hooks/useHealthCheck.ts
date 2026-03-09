"use client";

import { useEffect, useState } from "react";
import { checkHealth } from "@/lib/api";

export function useHealthCheck() {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;

    checkHealth().then((healthy) => {
      if (!cancelled) setIsHealthy(healthy);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  return { isHealthy };
}
