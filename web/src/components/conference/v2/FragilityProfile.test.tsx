import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FragilityProfile, DEMO_FRAGILITY_ENTRIES, type FragilityEntry } from "./FragilityProfile";

describe("FragilityProfile", () => {
  const testEntries: FragilityEntry[] = [
    {
      perturbation: "Renal impairment",
      description: "What if the patient has CKD?",
      result: "holds",
    },
    {
      perturbation: "Pregnancy",
      description: "What if the patient is pregnant?",
      result: "changes",
      alternativeRecommendation: "Defer treatment until postpartum",
    },
    {
      perturbation: "Anticoagulation",
      description: "What if the patient is on blood thinners?",
      result: "modified",
      modification: "Adjust timing",
    },
  ];

  it("renders component header", () => {
    render(<FragilityProfile entries={testEntries} />);
    expect(screen.getByText(/fragility profile/i)).toBeInTheDocument();
    expect(screen.getByText(/how robust is this recommendation/i)).toBeInTheDocument();
  });

  it("displays survival rate correctly", () => {
    render(<FragilityProfile entries={testEntries} />);
    // 2 survived (holds + modified) out of 3
    expect(screen.getByText(/67%/)).toBeInTheDocument();
    expect(screen.getByText(/2\/3 perturbations/i)).toBeInTheDocument();
  });

  it("shows all perturbation entries", () => {
    render(<FragilityProfile entries={testEntries} />);
    expect(screen.getByText("Renal impairment")).toBeInTheDocument();
    // Pregnancy appears in both the entry and the warning
    expect(screen.getAllByText("Pregnancy").length).toBeGreaterThan(0);
    expect(screen.getByText("Anticoagulation")).toBeInTheDocument();
  });

  it("shows correct status badges", () => {
    render(<FragilityProfile entries={testEntries} />);
    expect(screen.getByText("HOLDS")).toBeInTheDocument();
    expect(screen.getByText("CHANGES")).toBeInTheDocument();
    expect(screen.getByText("MODIFIED")).toBeInTheDocument();
  });

  it("displays fragile conditions warning", () => {
    render(<FragilityProfile entries={testEntries} />);
    expect(screen.getByText(/1 fragile condition/i)).toBeInTheDocument();
    // Pregnancy appears multiple times
    expect(screen.getAllByText(/pregnancy/i).length).toBeGreaterThan(0);
  });

  it("expands entry to show details", () => {
    render(<FragilityProfile entries={testEntries} />);
    
    // Find and click the Anticoagulation entry
    const anticoagEntry = screen.getByText("Anticoagulation").closest("button");
    fireEvent.click(anticoagEntry!);
    
    // Should show modification details
    expect(screen.getByText(/adjust timing/i)).toBeInTheDocument();
  });

  it("can collapse and expand main panel", () => {
    const onToggle = vi.fn();
    render(
      <FragilityProfile 
        entries={testEntries} 
        collapsed={false} 
        onToggle={onToggle} 
      />
    );
    
    // Click the header title text to collapse (CardHeader wraps it)
    const headerTitle = screen.getByText(/fragility profile/i);
    fireEvent.click(headerTitle);
    
    expect(onToggle).toHaveBeenCalled();
  });

  it("hides content when collapsed", () => {
    render(
      <FragilityProfile 
        entries={testEntries} 
        collapsed={true}
      />
    );
    
    // Entries should not be visible
    expect(screen.queryByText("Renal impairment")).not.toBeInTheDocument();
  });

  it("shows fragile badge in header when there are fragile conditions", () => {
    render(<FragilityProfile entries={testEntries} />);
    // There's a badge and a warning, so use getAllByText
    const fragileElements = screen.getAllByText(/1 fragile/i);
    expect(fragileElements.length).toBeGreaterThan(0);
  });

  it("handles empty entries array", () => {
    render(<FragilityProfile entries={[]} />);
    expect(screen.getByText(/fragility profile/i)).toBeInTheDocument();
    // Should show 0% survival rate
    expect(screen.getByText(/0%/)).toBeInTheDocument();
  });

  it("handles all entries holding", () => {
    const allHoldEntries: FragilityEntry[] = [
      { perturbation: "Test 1", description: "", result: "holds" },
      { perturbation: "Test 2", description: "", result: "holds" },
    ];
    
    render(<FragilityProfile entries={allHoldEntries} />);
    expect(screen.getByText(/100%/)).toBeInTheDocument();
    // Should not show fragile warning
    expect(screen.queryByText(/fragile condition/i)).not.toBeInTheDocument();
  });

  it("handles all entries changing", () => {
    const allChangeEntries: FragilityEntry[] = [
      { 
        perturbation: "Test 1", 
        description: "", 
        result: "changes",
        alternativeRecommendation: "Alt 1" 
      },
      { 
        perturbation: "Test 2", 
        description: "", 
        result: "changes",
        alternativeRecommendation: "Alt 2" 
      },
    ];
    
    render(<FragilityProfile entries={allChangeEntries} />);
    expect(screen.getByText(/0%/)).toBeInTheDocument();
    expect(screen.getByText(/2 fragile conditions/i)).toBeInTheDocument();
  });
});

describe("DEMO_FRAGILITY_ENTRIES", () => {
  it("has expected number of entries", () => {
    expect(DEMO_FRAGILITY_ENTRIES.length).toBe(8);
  });

  it("includes various result types", () => {
    const results = DEMO_FRAGILITY_ENTRIES.map(e => e.result);
    expect(results).toContain("holds");
    expect(results).toContain("modified");
    expect(results).toContain("changes");
  });

  it("includes common perturbation scenarios", () => {
    const perturbations = DEMO_FRAGILITY_ENTRIES.map(e => e.perturbation.toLowerCase());
    expect(perturbations.some(p => p.includes("renal"))).toBe(true);
    expect(perturbations.some(p => p.includes("pregnancy"))).toBe(true);
    expect(perturbations.some(p => p.includes("elderly"))).toBe(true);
  });

  it("all entries have required fields", () => {
    DEMO_FRAGILITY_ENTRIES.forEach(entry => {
      expect(entry.perturbation).toBeDefined();
      expect(entry.result).toBeDefined();
      expect(["holds", "modified", "changes"]).toContain(entry.result);
    });
  });
});

