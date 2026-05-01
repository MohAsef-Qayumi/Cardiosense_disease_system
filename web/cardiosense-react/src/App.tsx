import { useEffect } from "react";
import { Routes, Route, useLocation } from "react-router-dom";
import { AuthProvider } from "@/context/auth-context";
import { SiteHeader, DashboardLayout } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { RevealAnimation } from "@/components/reveal-animation";
import Home from "@/pages/Home";
import About from "@/pages/About";
import Contact from "@/pages/Contact";
import Login from "@/pages/Login";
import Signup from "@/pages/Signup";
import Dashboard from "@/pages/Dashboard";
import DashboardPredict from "@/pages/DashboardPredict";
import DashboardHistory from "@/pages/DashboardHistory";
import DashboardAnalytics from "@/pages/DashboardAnalytics";
import DashboardModels from "@/pages/DashboardModels";

function ScrollHandler() {
  const location = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

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
  }, [location.pathname]);

  return null;
}

export default function App() {
  const location = useLocation();
  const isDashboard = location.pathname.startsWith("/dashboard");

  return (
    <AuthProvider>
      <ScrollHandler />
      <div className="site-shell">
        {!isDashboard && <SiteHeader />}
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/about" element={<About />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/dashboard" element={<DashboardLayout><Dashboard /></DashboardLayout>} />
            <Route path="/dashboard/predict" element={<DashboardLayout><DashboardPredict /></DashboardLayout>} />
            <Route path="/dashboard/history" element={<DashboardLayout><DashboardHistory /></DashboardLayout>} />
            <Route path="/dashboard/analytics" element={<DashboardLayout><DashboardAnalytics /></DashboardLayout>} />
            <Route path="/dashboard/models" element={<DashboardLayout><DashboardModels /></DashboardLayout>} />
          </Routes>
        </main>
        {!isDashboard && <SiteFooter />}
      </div>
      <RevealAnimation />
    </AuthProvider>
  );
}