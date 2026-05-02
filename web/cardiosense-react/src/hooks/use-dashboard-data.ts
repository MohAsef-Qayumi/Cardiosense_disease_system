import { useEffect, useState, useRef } from "react";

export function useAnimatedNumber(target: number, duration: number = 1000, suffix: string = ""): string {
  const [display, setDisplay] = useState("0" + suffix);
  const startRef = useRef<number | null>(null);
  const fromRef = useRef(0);

  useEffect(() => {
    startRef.current = null;
    fromRef.current = 0;
    
    const step = (timestamp: number) => {
      if (!startRef.current) startRef.current = timestamp;
      const progress = Math.min((timestamp - startRef.current) / duration, 1);
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const current = fromRef.current + (target - fromRef.current) * easeOut;
      
      if (Number.isInteger(target)) {
        setDisplay(Math.round(current) + suffix);
      } else {
        setDisplay(current.toFixed(2) + suffix);
      }
      
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    };
    
    requestAnimationFrame(step);
  }, [target, duration, suffix]);

  return display;
}

export function useApiHealth() {
  const [status, setStatus] = useState<"checking" | "online" | "offline">("checking");
  const [version, setVersion] = useState<string>("-");

  useEffect(() => {
    const check = async () => {
      try {
        const apiBase = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
        const res = await fetch(`${apiBase}/health`, { signal: AbortSignal.timeout(3000) });
        if (res.ok) {
          const data = await res.json();
          setStatus("online");
          setVersion(data.active_model_version || "v1.0");
        } else {
          setStatus("offline");
        }
      } catch {
        setStatus("offline");
      }
    };
    
    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, []);

  return { status, version };
}

export function useCountUp(end: number, duration: number = 1500): number {
  const [count, setCount] = useState(0);
  const countRef = useRef(0);
  const frameRef = useRef<number>(0); // Fix initialization

  useEffect(() => {
    const startTime = performance.now();
    countRef.current = 0;

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeOutQuart = 1 - Math.pow(1 - progress, 4);
      const current = Math.floor(easeOutQuart * end);
      
      if (current !== countRef.current) {
        countRef.current = current;
        setCount(current);
      }
      
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      }
    };

    frameRef.current = requestAnimationFrame(animate);
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [end, duration]);

  return count;
}