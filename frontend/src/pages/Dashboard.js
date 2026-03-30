import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { listProjects, createProject, deleteProject } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Plus, Zap, Trash2, ArrowRight, LayoutDashboard, Database, Code2, GitBranch } from "lucide-react";

const STATUS_COLORS = {
  INIT: "bg-gray-200 text-gray-700",
  ANALYZING: "bg-blue-100 text-blue-700",
  GATHERING: "bg-amber-100 text-amber-700",
  ARCHITECTING: "bg-indigo-100 text-indigo-700",
  TRANSFORMING: "bg-purple-100 text-purple-700",
  GENERATING_FRONTEND: "bg-cyan-100 text-cyan-700",
  GENERATING_BACKEND: "bg-teal-100 text-teal-700",
  REVIEWING: "bg-orange-100 text-orange-700",
  COMPLETE: "bg-emerald-100 text-emerald-700",
  ERROR: "bg-red-100 text-red-700",
};

const EXAMPLES = [
  "I want an ERP for a manufacturing company with inventory, production planning, and sales management",
  "Build me a retail ERP with POS, inventory tracking, CRM, and supplier management",
  "Create an ERP for a healthcare clinic with patient management, appointments, billing, and pharmacy",
  "Design an ERP for a construction company with project management, procurement, and HR",
];

export default function Dashboard() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => { loadProjects(); }, []);

  async function loadProjects() {
    try {
      const data = await listProjects();
      setProjects(data);
    } catch { /* ignore */ }
  }

  async function handleCreate() {
    if (!name.trim() || !prompt.trim()) { toast.error("Fill in all fields"); return; }
    setCreating(true);
    try {
      const project = await createProject(name.trim(), prompt.trim());
      navigate(`/project/${project.id}`);
    } catch (e) {
      toast.error("Failed to create project");
      setCreating(false);
    }
  }

  async function handleDelete(e, id) {
    e.stopPropagation();
    try {
      await deleteProject(id);
      setProjects(prev => prev.filter(p => p.id !== id));
      toast.success("Project deleted");
    } catch { toast.error("Delete failed"); }
  }

  function selectExample(ex) {
    setPrompt(ex);
    setName(ex.split(" for ")[1]?.split(" with")[0] || "My ERP Project");
  }

  return (
    <div className="min-h-screen" data-testid="dashboard-page">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/70 backdrop-blur-xl border-b border-black/5">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-[var(--zap-accent)] rounded-sm flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold tracking-tight" style={{ fontFamily: 'var(--font-heading)' }}>
              Zappizo
            </span>
          </div>
          <Button
            data-testid="new-project-btn"
            onClick={() => setOpen(true)}
            className="bg-[var(--zap-primary)] text-white hover:bg-black/80 rounded-sm h-8 px-4 text-sm"
          >
            <Plus className="w-4 h-4 mr-1" /> New Project
          </Button>
        </div>
      </header>

      {/* Hero */}
      <div className="max-w-7xl mx-auto px-6 pt-16 pb-10">
        <div className="max-w-2xl">
          <p className="text-xs uppercase tracking-[0.2em] font-medium text-[var(--zap-text-muted)] mb-4">
            AI-Powered ERP Builder
          </p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl tracking-tighter font-black leading-[1.05] mb-5"
              style={{ fontFamily: 'var(--font-heading)' }}>
            Transform ideas into<br />enterprise systems
          </h1>
          <p className="text-base text-[var(--zap-text-body)] leading-relaxed max-w-lg mb-8">
            Describe your business in plain language. Zappizo's AI agents will design the architecture,
            generate the database schema, API endpoints, and production-ready code.
          </p>
          <Button
            data-testid="hero-get-started-btn"
            onClick={() => setOpen(true)}
            className="bg-[var(--zap-accent)] text-white hover:opacity-90 rounded-sm h-10 px-6 text-sm font-medium"
          >
            Get Started <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>

        {/* Feature Chips */}
        <div className="flex flex-wrap gap-3 mt-12 mb-16">
          {[
            { icon: LayoutDashboard, label: "Architecture Design" },
            { icon: Database, label: "Schema Generation" },
            { icon: Code2, label: "Code Generation" },
            { icon: GitBranch, label: "Version Control" },
          ].map(({ icon: Icon, label }) => (
            <div key={label} className="flex items-center gap-2 px-3 py-1.5 border border-[var(--zap-border)] rounded-sm text-sm text-[var(--zap-text-body)]">
              <Icon className="w-3.5 h-3.5 text-[var(--zap-text-muted)]" />
              {label}
            </div>
          ))}
        </div>

        {/* Projects Grid */}
        {projects.length > 0 && (
          <div>
            <h2 className="text-2xl sm:text-3xl tracking-tight font-bold mb-6"
                style={{ fontFamily: 'var(--font-heading)' }}>
              Your Projects
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {projects.map((p) => (
                <div
                  key={p.id}
                  data-testid={`project-card-${p.id}`}
                  onClick={() => navigate(`/project/${p.id}`)}
                  className="module-card p-5 bg-white cursor-pointer group"
                >
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="font-semibold text-[var(--zap-text-heading)] tracking-tight truncate pr-2"
                        style={{ fontFamily: 'var(--font-heading)' }}>
                      {p.name}
                    </h3>
                    <button
                      data-testid={`delete-project-${p.id}`}
                      onClick={(e) => handleDelete(e, p.id)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-red-50 rounded-sm"
                    >
                      <Trash2 className="w-3.5 h-3.5 text-red-500" />
                    </button>
                  </div>
                  <p className="text-sm text-[var(--zap-text-muted)] line-clamp-2 mb-4">{p.prompt}</p>
                  <div className="flex items-center justify-between">
                    <Badge className={`${STATUS_COLORS[p.status] || STATUS_COLORS.INIT} text-xs uppercase tracking-widest rounded-sm border-0`}>
                      {p.status}
                    </Badge>
                    <span className="text-xs text-[var(--zap-text-muted)]">
                      {new Date(p.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Create Dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg rounded-sm border-[var(--zap-border)]" data-testid="create-project-dialog">
          <DialogHeader>
            <DialogTitle className="text-xl tracking-tight font-bold" style={{ fontFamily: 'var(--font-heading)' }}>
              Create New ERP Project
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="text-sm font-medium text-[var(--zap-text-heading)] mb-1.5 block">Project Name</label>
              <Input
                data-testid="project-name-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Manufacturing ERP"
                className="rounded-sm border-[var(--zap-border)] focus-visible:ring-[var(--zap-accent)]"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-[var(--zap-text-heading)] mb-1.5 block">
                Describe Your ERP
              </label>
              <Textarea
                data-testid="project-prompt-input"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe the ERP system you want to build..."
                rows={4}
                className="rounded-sm border-[var(--zap-border)] focus-visible:ring-[var(--zap-accent)] resize-none"
              />
            </div>
            <div>
              <p className="text-xs text-[var(--zap-text-muted)] mb-2">Quick examples:</p>
              <div className="flex flex-wrap gap-2">
                {EXAMPLES.map((ex, i) => (
                  <button
                    key={i}
                    data-testid={`example-prompt-${i}`}
                    onClick={() => selectExample(ex)}
                    className="text-xs text-left px-2.5 py-1.5 border border-[var(--zap-border)] rounded-sm text-[var(--zap-text-muted)] hover:border-[var(--zap-accent)] hover:text-[var(--zap-accent)] transition-colors"
                  >
                    {ex.length > 60 ? ex.slice(0, 60) + "..." : ex}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button
              data-testid="cancel-create-btn"
              variant="outline"
              onClick={() => setOpen(false)}
              className="rounded-sm border-[var(--zap-border)]"
            >
              Cancel
            </Button>
            <Button
              data-testid="create-project-submit-btn"
              onClick={handleCreate}
              disabled={creating}
              className="bg-[var(--zap-accent)] text-white hover:opacity-90 rounded-sm"
            >
              {creating ? "Creating..." : "Create Project"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
