import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "@/pages/Dashboard";
import ProjectBuilder from "@/pages/ProjectBuilder";
import { Toaster } from "@/components/ui/sonner";

function App() {
  return (
    <div className="min-h-screen bg-[var(--zap-bg)]">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/project/:id" element={<ProjectBuilder />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="bottom-right" />
    </div>
  );
}

export default App;
