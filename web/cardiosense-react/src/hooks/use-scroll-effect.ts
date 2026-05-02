import { useEffect } from "react";

export function useScrollEffect() {
  useEffect(() => {
    const nav = document.querySelector(".cs-navbar");
    if (!nav) return;

    const handleScroll = () => {
      if (window.scrollY > 16) {
        nav.classList.add("is-scrolled");
      } else {
        nav.classList.remove("is-scrolled");
      }
    };

    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);
}
