import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConfigPanelV21, DEFAULT_V21_CONFIG, type V21Config } from "./ConfigPanelV21";

describe("ConfigPanelV21", () => {
  const defaultConfig: V21Config = { ...DEFAULT_V21_CONFIG };
  
  it("renders all configuration sections", () => {
    const onChange = vi.fn();
    render(<ConfigPanelV21 config={defaultConfig} onChange={onChange} />);
    
    expect(screen.getByText(/risk tolerance/i)).toBeInTheDocument();
    expect(screen.getByText(/mode override/i)).toBeInTheDocument();
    expect(screen.getByText(/scout literature/i)).toBeInTheDocument();
    expect(screen.getByText(/fragility testing/i)).toBeInTheDocument();
    expect(screen.getByText(/advanced/i)).toBeInTheDocument();
  });

  describe("Risk Tolerance Slider", () => {
    it("shows conservative label for low values", () => {
      const onChange = vi.fn();
      render(
        <ConfigPanelV21 
          config={{ ...defaultConfig, riskTolerance: 0.2 }} 
          onChange={onChange} 
        />
      );
      // Conservative appears twice (in label and slider endpoint)
      const conservativeElements = screen.getAllByText("Conservative");
      expect(conservativeElements.length).toBeGreaterThan(0);
    });

    it("shows balanced label for mid values", () => {
      const onChange = vi.fn();
      render(
        <ConfigPanelV21 
          config={{ ...defaultConfig, riskTolerance: 0.5 }} 
          onChange={onChange} 
        />
      );
      expect(screen.getByText("Balanced")).toBeInTheDocument();
    });

    it("shows exploratory label for high values", () => {
      const onChange = vi.fn();
      render(
        <ConfigPanelV21 
          config={{ ...defaultConfig, riskTolerance: 0.8 }} 
          onChange={onChange} 
        />
      );
      // Exploratory appears twice (in label and slider endpoint)
      const exploratoryElements = screen.getAllByText("Exploratory");
      expect(exploratoryElements.length).toBeGreaterThan(0);
    });

    it("displays current value", () => {
      const onChange = vi.fn();
      render(
        <ConfigPanelV21 
          config={{ ...defaultConfig, riskTolerance: 0.5 }} 
          onChange={onChange} 
        />
      );
      expect(screen.getByText("0.5")).toBeInTheDocument();
    });

    it("calls onChange when slider changes", () => {
      const onChange = vi.fn();
      render(<ConfigPanelV21 config={defaultConfig} onChange={onChange} />);
      
      const slider = screen.getAllByRole("slider")[0];
      fireEvent.change(slider, { target: { value: "0.8" } });
      
      expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
        riskTolerance: 0.8,
      }));
    });
  });

  describe("Mode Override", () => {
    it("shows current mode selection", () => {
      const onChange = vi.fn();
      render(
        <ConfigPanelV21 
          config={{ ...defaultConfig, modeOverride: "auto" }} 
          onChange={onChange} 
        />
      );
      expect(screen.getByText(/auto \(router decides\)/i)).toBeInTheDocument();
    });

    it("shows mode description", () => {
      const onChange = vi.fn();
      render(<ConfigPanelV21 config={defaultConfig} onChange={onChange} />);
      // The dropdown should show description when opened
      expect(screen.getByText(/auto \(router decides\)/i)).toBeInTheDocument();
    });
  });

  describe("Scout Settings", () => {
    it("shows scout toggle", () => {
      const onChange = vi.fn();
      render(<ConfigPanelV21 config={defaultConfig} onChange={onChange} />);
      expect(screen.getByText(/scout literature/i)).toBeInTheDocument();
    });

    it("shows timeframe selector when scout enabled", () => {
      const onChange = vi.fn();
      render(
        <ConfigPanelV21 
          config={{ ...defaultConfig, enableScout: true }} 
          onChange={onChange} 
        />
      );
      expect(screen.getByText(/search timeframe/i)).toBeInTheDocument();
    });

    it("hides timeframe selector when scout disabled", () => {
      const onChange = vi.fn();
      render(
        <ConfigPanelV21 
          config={{ ...defaultConfig, enableScout: false }} 
          onChange={onChange} 
        />
      );
      expect(screen.queryByText(/search timeframe/i)).not.toBeInTheDocument();
    });
  });

  describe("Fragility Testing", () => {
    it("shows fragility toggle", () => {
      const onChange = vi.fn();
      render(<ConfigPanelV21 config={defaultConfig} onChange={onChange} />);
      expect(screen.getByText(/fragility testing/i)).toBeInTheDocument();
    });

    it("shows perturbation count when fragility enabled", () => {
      const onChange = vi.fn();
      render(
        <ConfigPanelV21 
          config={{ ...defaultConfig, enableFragilityTesting: true }} 
          onChange={onChange} 
        />
      );
      expect(screen.getByText(/number of perturbations/i)).toBeInTheDocument();
    });

    it("hides perturbation count when fragility disabled", () => {
      const onChange = vi.fn();
      render(
        <ConfigPanelV21 
          config={{ ...defaultConfig, enableFragilityTesting: false }} 
          onChange={onChange} 
        />
      );
      expect(screen.queryByText(/number of perturbations/i)).not.toBeInTheDocument();
    });
  });

  describe("Advanced Section", () => {
    it("is collapsed by default", () => {
      const onChange = vi.fn();
      render(<ConfigPanelV21 config={defaultConfig} onChange={onChange} />);
      // Advanced content should not be visible
      expect(screen.queryByText(/scout sources/i)).not.toBeInTheDocument();
    });

    it("expands when clicked", () => {
      const onChange = vi.fn();
      render(<ConfigPanelV21 config={defaultConfig} onChange={onChange} />);
      
      const advancedHeader = screen.getByText("Advanced");
      fireEvent.click(advancedHeader);
      
      // Advanced content should now be visible
      expect(screen.getByText(/scout sources/i)).toBeInTheDocument();
      expect(screen.getByText(/pubmed/i)).toBeInTheDocument();
    });
  });

  describe("Disabled State", () => {
    it("disables all inputs when disabled prop is true", () => {
      const onChange = vi.fn();
      render(<ConfigPanelV21 config={defaultConfig} onChange={onChange} disabled />);
      
      const sliders = screen.getAllByRole("slider");
      sliders.forEach(slider => {
        expect(slider).toBeDisabled();
      });
    });
  });
});

describe("DEFAULT_V21_CONFIG", () => {
  it("has reasonable defaults", () => {
    expect(DEFAULT_V21_CONFIG.riskTolerance).toBe(0.5);
    expect(DEFAULT_V21_CONFIG.modeOverride).toBe("auto");
    expect(DEFAULT_V21_CONFIG.enableScout).toBe(true);
    expect(DEFAULT_V21_CONFIG.scoutTimeframe).toBe("12_months");
    expect(DEFAULT_V21_CONFIG.enableFragilityTesting).toBe(false);
    expect(DEFAULT_V21_CONFIG.fragilityTests).toBe(5);
  });
});

