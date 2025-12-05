import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import * as React from "react";

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock framer-motion to avoid animation issues in tests
vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    motion: {
      div: (props: React.HTMLProps<HTMLDivElement>) => 
        React.createElement("div", props),
      span: (props: React.HTMLProps<HTMLSpanElement>) => 
        React.createElement("span", props),
      button: (props: React.HTMLProps<HTMLButtonElement>) => 
        React.createElement("button", props),
      ul: (props: React.HTMLProps<HTMLUListElement>) => 
        React.createElement("ul", props),
      li: (props: React.HTMLProps<HTMLLIElement>) => 
        React.createElement("li", props),
      header: (props: React.HTMLProps<HTMLElement>) => 
        React.createElement("header", props),
      section: (props: React.HTMLProps<HTMLElement>) => 
        React.createElement("section", props),
    },
    AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  };
});

// Mock IndexedDB for session storage tests
const mockIndexedDB = {
  open: vi.fn(() => ({
    result: {
      transaction: vi.fn(() => ({
        objectStore: vi.fn(() => ({
          put: vi.fn(() => ({ onsuccess: null, onerror: null })),
          get: vi.fn(() => ({ onsuccess: null, onerror: null })),
          delete: vi.fn(() => ({ onsuccess: null, onerror: null })),
          clear: vi.fn(() => ({ onsuccess: null, onerror: null })),
          index: vi.fn(() => ({
            openCursor: vi.fn(() => ({ onsuccess: null, onerror: null })),
          })),
        })),
      })),
      objectStoreNames: {
        contains: vi.fn(() => false),
      },
      createObjectStore: vi.fn(() => ({
        createIndex: vi.fn(),
      })),
    },
    onsuccess: null,
    onerror: null,
    onupgradeneeded: null,
  })),
};

Object.defineProperty(global, "indexedDB", {
  value: mockIndexedDB,
  writable: true,
});

// Mock window.matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));
