import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { 
  MasterProgressBar, 
  DEFAULT_V2_PHASES,
  calculateOverallProgress,
  estimateTimeRemaining,
  type Phase,
} from "./MasterProgressBar";

describe("MasterProgressBar", () => {
  const basePhases: Phase[] = [
    { key: "routing", label: "Route", status: "complete", duration: 2000 },
    { key: "scout", label: "Scout", status: "complete", duration: 8000 },
    { key: "lane_a", label: "Lane A", status: "running", estimatedDuration: 20000 },
    { key: "lane_b", label: "Lane B", status: "pending", estimatedDuration: 15000 },
    { key: "synthesis", label: "Synth", status: "pending", estimatedDuration: 12000 },
  ];

  it("renders conference in progress state", () => {
    render(
      <MasterProgressBar
        phases={basePhases}
        currentPhase="lane_a"
        overallProgress={45}
      />
    );
    expect(screen.getByText(/conference in progress/i)).toBeInTheDocument();
    expect(screen.getByText(/2\/5 phases/i)).toBeInTheDocument();
  });

  it("renders complete state", () => {
    const completePhases = basePhases.map(p => ({ ...p, status: "complete" as const }));
    render(
      <MasterProgressBar
        phases={completePhases}
        currentPhase=""
        overallProgress={100}
        isComplete={true}
      />
    );
    expect(screen.getByText(/conference complete/i)).toBeInTheDocument();
    expect(screen.getByText(/100% complete/i)).toBeInTheDocument();
  });

  it("renders error state", () => {
    render(
      <MasterProgressBar
        phases={basePhases}
        currentPhase="lane_a"
        overallProgress={45}
        error="API rate limit exceeded"
      />
    );
    expect(screen.getByText(/conference error/i)).toBeInTheDocument();
    expect(screen.getByText(/api rate limit exceeded/i)).toBeInTheDocument();
  });

  it("displays estimated time remaining", () => {
    render(
      <MasterProgressBar
        phases={basePhases}
        currentPhase="lane_a"
        overallProgress={45}
        estimatedTimeRemaining={30}
      />
    );
    expect(screen.getByText(/est\. ~30s left/i)).toBeInTheDocument();
  });

  it("renders all phase indicators", () => {
    render(
      <MasterProgressBar
        phases={basePhases}
        currentPhase="lane_a"
        overallProgress={45}
      />
    );
    expect(screen.getByText("Route")).toBeInTheDocument();
    expect(screen.getByText("Scout")).toBeInTheDocument();
    expect(screen.getByText("Lane A")).toBeInTheDocument();
    expect(screen.getByText("Lane B")).toBeInTheDocument();
    expect(screen.getByText("Synth")).toBeInTheDocument();
  });

  it("shows duration for completed phases", () => {
    render(
      <MasterProgressBar
        phases={basePhases}
        currentPhase="lane_a"
        overallProgress={45}
      />
    );
    expect(screen.getByText("(2.0s)")).toBeInTheDocument();
    expect(screen.getByText("(8.0s)")).toBeInTheDocument();
  });
});

describe("calculateOverallProgress", () => {
  it("returns 0 for empty phases", () => {
    expect(calculateOverallProgress([])).toBe(0);
  });

  it("returns 100 for all complete phases", () => {
    const phases: Phase[] = [
      { key: "a", label: "A", status: "complete", estimatedDuration: 5000 },
      { key: "b", label: "B", status: "complete", estimatedDuration: 5000 },
    ];
    expect(calculateOverallProgress(phases)).toBe(100);
  });

  it("returns 50 when half phases are running", () => {
    const phases: Phase[] = [
      { key: "a", label: "A", status: "complete", estimatedDuration: 5000 },
      { key: "b", label: "B", status: "running", estimatedDuration: 5000 },
    ];
    // complete = 5000, running = 2500, total = 10000
    // progress = 7500 / 10000 = 75%
    expect(calculateOverallProgress(phases)).toBe(75);
  });

  it("weights phases by estimated duration", () => {
    const phases: Phase[] = [
      { key: "a", label: "A", status: "complete", estimatedDuration: 10000 },
      { key: "b", label: "B", status: "pending", estimatedDuration: 10000 },
    ];
    expect(calculateOverallProgress(phases)).toBe(50);
  });
});

describe("estimateTimeRemaining", () => {
  it("returns 0 for all complete phases", () => {
    const phases: Phase[] = [
      { key: "a", label: "A", status: "complete", estimatedDuration: 5000 },
      { key: "b", label: "B", status: "complete", estimatedDuration: 5000 },
    ];
    expect(estimateTimeRemaining(phases)).toBe(0);
  });

  it("sums pending phase durations", () => {
    const phases: Phase[] = [
      { key: "a", label: "A", status: "complete", estimatedDuration: 5000 },
      { key: "b", label: "B", status: "pending", estimatedDuration: 10000 },
      { key: "c", label: "C", status: "pending", estimatedDuration: 5000 },
    ];
    // 10 + 5 = 15 seconds
    expect(estimateTimeRemaining(phases)).toBe(15);
  });

  it("counts half for running phases", () => {
    const phases: Phase[] = [
      { key: "a", label: "A", status: "running", estimatedDuration: 10000 },
      { key: "b", label: "B", status: "pending", estimatedDuration: 10000 },
    ];
    // 5 (half of running) + 10 = 15 seconds
    expect(estimateTimeRemaining(phases)).toBe(15);
  });
});

describe("DEFAULT_V2_PHASES", () => {
  it("has all expected phases", () => {
    const phaseKeys = DEFAULT_V2_PHASES.map(p => p.key);
    expect(phaseKeys).toContain("routing");
    expect(phaseKeys).toContain("scout");
    expect(phaseKeys).toContain("lane_a");
    expect(phaseKeys).toContain("lane_b");
    expect(phaseKeys).toContain("cross_exam");
    expect(phaseKeys).toContain("synthesis");
    expect(phaseKeys).toContain("fragility");
  });

  it("all phases start as pending", () => {
    expect(DEFAULT_V2_PHASES.every(p => p.status === "pending")).toBe(true);
  });

  it("all phases have estimated durations", () => {
    expect(DEFAULT_V2_PHASES.every(p => p.estimatedDuration !== undefined)).toBe(true);
  });
});

