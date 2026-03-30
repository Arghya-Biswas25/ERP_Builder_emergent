import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

const STAGES = [
  { key: "requirement_analysis", label: "Analysis", short: "AN" },
  { key: "requirement_gathering", label: "Gathering", short: "GA" },
  { key: "architecture", label: "Architecture", short: "AR" },
  { key: "json_transform", label: "Transform", short: "TR" },
  { key: "frontend_generation", label: "Frontend", short: "FE" },
  { key: "backend_generation", label: "Backend", short: "BE" },
  { key: "code_review", label: "Review", short: "RE" },
];

function StageIcon({ status }) {
  if (status === "complete") return <CheckCircle2 className="w-3.5 h-3.5 text-[var(--zap-success)]" />;
  if (status === "running") return <Loader2 className="w-3.5 h-3.5 text-[var(--zap-accent)] animate-spin" />;
  if (status === "failed") return <XCircle className="w-3.5 h-3.5 text-[var(--zap-danger)]" />;
  return <Circle className="w-3.5 h-3.5 text-gray-300" />;
}

export default function PipelineProgress({ pipeline, status }) {
  if (!pipeline) return null;

  const completedCount = STAGES.filter(s => pipeline[s.key]?.status === "complete").length;
  const progress = (completedCount / STAGES.length) * 100;

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex items-center gap-1" data-testid="pipeline-progress">
        {/* Progress bar background */}
        <div className="relative flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden mr-2">
          <div
            className="absolute left-0 top-0 h-full bg-[var(--zap-accent)] transition-all duration-700 ease-out rounded-full"
            style={{ width: `${progress}%` }}
          />
          {STAGES.some(s => pipeline[s.key]?.status === "running") && (
            <div
              className="absolute top-0 h-full tracing-beam rounded-full"
              style={{ left: `${progress}%`, width: "30%", opacity: 0.5 }}
            />
          )}
        </div>

        {/* Stage dots */}
        <div className="flex items-center gap-0.5">
          {STAGES.map((stage, i) => {
            const stageStatus = pipeline[stage.key]?.status || "pending";
            return (
              <Tooltip key={stage.key}>
                <TooltipTrigger asChild>
                  <div
                    data-testid={`pipeline-stage-${stage.key}`}
                    className={`pipeline-stage flex items-center justify-center w-6 h-6 rounded-sm cursor-default
                      ${stageStatus === "running" ? "active pulse-glow" : ""}
                      ${stageStatus === "complete" ? "complete" : ""}
                      ${stageStatus === "failed" ? "failed" : ""}`}
                  >
                    <StageIcon status={stageStatus} />
                  </div>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="text-xs rounded-sm">
                  <p className="font-medium">{stage.label}</p>
                  <p className="text-[var(--zap-text-muted)] capitalize">{stageStatus}</p>
                </TooltipContent>
              </Tooltip>
            );
          })}
        </div>

        {/* Status label */}
        <span className="text-[10px] uppercase tracking-widest font-medium text-[var(--zap-text-muted)] ml-2 whitespace-nowrap">
          {status === "COMPLETE" ? "Done" : status === "ERROR" ? "Error" : `${completedCount}/${STAGES.length}`}
        </span>
      </div>
    </TooltipProvider>
  );
}
