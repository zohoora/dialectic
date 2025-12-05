import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { 
  ActivityFeed, 
  ActivityEventRow, 
  createActivityEvent, 
  type ActivityEvent 
} from "./ActivityFeed";

describe("ActivityFeed", () => {
  const mockEvents: ActivityEvent[] = [
    createActivityEvent("conference_start", "start", "complete", { message: "Started" }),
    createActivityEvent("routing_complete", "routing", "complete", { mode: "COMPLEX_DILEMMA" }),
    createActivityEvent("agent_start", "generation", "running", { 
      agentRole: "empiricist", 
      tokensGenerated: 100, 
      tokensEstimated: 500 
    }),
  ];

  it("renders empty state when no events", () => {
    render(<ActivityFeed events={[]} />);
    expect(screen.getByText(/no activity yet/i)).toBeInTheDocument();
  });

  it("renders events when provided", () => {
    render(<ActivityFeed events={mockEvents} />);
    expect(screen.getByText(/conference started/i)).toBeInTheDocument();
    expect(screen.getByText(/COMPLEX_DILEMMA/i)).toBeInTheDocument();
  });

  it("displays event count in header", () => {
    render(<ActivityFeed events={mockEvents} />);
    expect(screen.getByText(/3 events/i)).toBeInTheDocument();
  });

  it("toggles auto-scroll checkbox", () => {
    render(<ActivityFeed events={mockEvents} />);
    const checkbox = screen.getByRole("checkbox");
    expect(checkbox).toBeChecked();
    fireEvent.click(checkbox);
    expect(checkbox).not.toBeChecked();
  });

  it("can collapse and expand", () => {
    const onToggle = vi.fn();
    render(<ActivityFeed events={mockEvents} collapsed={false} onToggle={onToggle} />);
    
    // Click header to collapse
    const header = screen.getByText(/activity feed/i).closest("div");
    fireEvent.click(header!);
    expect(onToggle).toHaveBeenCalled();
  });

  it("respects collapsed state", () => {
    render(<ActivityFeed events={mockEvents} collapsed={true} />);
    // Events should not be visible when collapsed
    expect(screen.queryByText(/conference started/i)).not.toBeInTheDocument();
  });
});

describe("ActivityEventRow", () => {
  it("displays timestamp correctly", () => {
    const event = createActivityEvent("conference_start", "start", "complete", {});
    render(<ActivityEventRow event={event} />);
    // Should show time in some format
    expect(screen.getByText(/\d{1,2}:\d{2}:\d{2}/)).toBeInTheDocument();
  });

  it("shows running status indicator", () => {
    const event = createActivityEvent("agent_progress", "generation", "running", {
      agentRole: "empiricist",
      tokensGenerated: 100,
    });
    render(<ActivityEventRow event={event} />);
    expect(screen.getByText(/empiricist/i)).toBeInTheDocument();
  });

  it("shows error status styling", () => {
    const event = createActivityEvent("agent_error", "generation", "error", {
      agentRole: "skeptic",
      message: "Rate limit exceeded",
    });
    render(<ActivityEventRow event={event} />);
    expect(screen.getByText(/skeptic error/i)).toBeInTheDocument();
  });

  it("highlights latest event", () => {
    const event = createActivityEvent("conference_start", "start", "complete", {});
    const { container } = render(<ActivityEventRow event={event} isLatest={true} />);
    // Should have special styling for latest
    expect(container.firstChild).toHaveClass("bg-slate-800/50");
  });
});

describe("createActivityEvent", () => {
  it("creates event with unique id", () => {
    const event1 = createActivityEvent("conference_start", "start", "complete", {});
    const event2 = createActivityEvent("conference_start", "start", "complete", {});
    expect(event1.id).not.toBe(event2.id);
  });

  it("sets timestamp to current time", () => {
    const before = new Date();
    const event = createActivityEvent("conference_start", "start", "complete", {});
    const after = new Date();
    
    expect(event.timestamp.getTime()).toBeGreaterThanOrEqual(before.getTime());
    expect(event.timestamp.getTime()).toBeLessThanOrEqual(after.getTime());
  });

  it("includes all provided details", () => {
    const details = {
      agentRole: "empiricist",
      tokensGenerated: 100,
      message: "Test message",
    };
    const event = createActivityEvent("agent_progress", "generation", "running", details);
    expect(event.details).toEqual(details);
  });
});

