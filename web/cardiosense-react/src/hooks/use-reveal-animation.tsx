import { useEffect, useRef, ReactNode } from "react";
import { useLocation } from "react-router-dom";

export function useRevealAnimation() {
  const location = useLocation();
  const observerRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const setupObserver = () => {
      const revealElements = document.querySelectorAll("[data-reveal]:not(.is-visible)");
      if (!revealElements.length) return;

      if (observerRef.current) {
        observerRef.current.disconnect();
      }

      observerRef.current = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add("is-visible");
              observerRef.current?.unobserve(entry.target);
            }
          });
        },
        { 
          threshold: 0.05,
          rootMargin: "0px 0px -100px 0px"
        }
      );

      revealElements.forEach((el) => observerRef.current?.observe(el));
    };

    setupObserver();
    
    const timeoutId = setTimeout(setupObserver, 200);
    return () => {
      clearTimeout(timeoutId);
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [location.pathname]);
}

export function Reveal({ children, className = "" }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const location = useLocation();

  useEffect(() => {
    if (!ref.current) return;
    ref.current.classList.remove("is-visible");

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { 
        threshold: 0.05,
        rootMargin: "0px 0px -100px 0px"
      }
    );

    observer.observe(ref.current);

    return () => {
      observer.disconnect();
    };
  }, [location.pathname]);

  return (
    <div ref={ref} className={className} data-reveal>
      {children}
    </div>
  );
}