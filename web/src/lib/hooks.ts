/**
 * Shared hook utilities for state management and API interactions.
 * 
 * Provides reusable patterns for:
 * - Async state management (loading, error, data)
 * - Local storage persistence
 * - Event handling utilities
 */

import { useState, useCallback, useEffect, useRef } from "react";

// =============================================================================
// ASYNC STATE HOOK
// =============================================================================

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function useAsyncState<T>(initialData: T | null = null) {
  const [state, setState] = useState<AsyncState<T>>({
    data: initialData,
    loading: false,
    error: null,
  });

  const setLoading = useCallback(() => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
  }, []);

  const setData = useCallback((data: T) => {
    setState({ data, loading: false, error: null });
  }, []);

  const setError = useCallback((error: string) => {
    setState((prev) => ({ ...prev, loading: false, error }));
  }, []);

  const reset = useCallback(() => {
    setState({ data: initialData, loading: false, error: null });
  }, [initialData]);

  return { state, setLoading, setData, setError, reset };
}

// =============================================================================
// LOCAL STORAGE HOOK
// =============================================================================

export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((prev: T) => T)) => void] {
  // Get initial value from localStorage or use provided initial value
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === "undefined") {
      return initialValue;
    }
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  // Update localStorage when value changes
  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      try {
        const valueToStore =
          value instanceof Function ? value(storedValue) : value;
        setStoredValue(valueToStore);
        if (typeof window !== "undefined") {
          window.localStorage.setItem(key, JSON.stringify(valueToStore));
        }
      } catch (error) {
        console.warn(`Error setting localStorage key "${key}":`, error);
      }
    },
    [key, storedValue]
  );

  return [storedValue, setValue];
}

// =============================================================================
// DEBOUNCE HOOK
// =============================================================================

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// =============================================================================
// FETCH HOOK
// =============================================================================

export interface UseFetchOptions {
  immediate?: boolean;
}

export function useFetch<T>(
  url: string,
  options?: UseFetchOptions
) {
  const { state, setLoading, setData, setError } = useAsyncState<T>();
  
  const fetchData = useCallback(async () => {
    setLoading();
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setData(data);
      return data;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setError(message);
      return null;
    }
  }, [url, setLoading, setData, setError]);

  useEffect(() => {
    if (options?.immediate !== false) {
      fetchData();
    }
  }, [url]); // eslint-disable-line react-hooks/exhaustive-deps

  return { ...state, refetch: fetchData };
}

// =============================================================================
// EVENT SOURCE HOOK (for SSE)
// =============================================================================

export interface UseEventSourceOptions {
  onOpen?: () => void;
  onError?: (error: Event) => void;
  onMessage?: (data: unknown) => void;
}

export function useEventSource(
  url: string | null,
  eventHandlers: Record<string, (data: unknown) => void>,
  options?: UseEventSourceOptions
) {
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!url) return;

    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    if (options?.onOpen) {
      eventSource.onopen = options.onOpen;
    }

    if (options?.onError) {
      eventSource.onerror = options.onError;
    }

    // Register all event handlers
    Object.entries(eventHandlers).forEach(([eventType, handler]) => {
      eventSource.addEventListener(eventType, (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          handler(data);
        } catch (err) {
          console.error(`Failed to parse SSE event ${eventType}:`, err);
        }
      });
    });

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [url]); // eslint-disable-line react-hooks/exhaustive-deps

  const close = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  }, []);

  return { close };
}

// =============================================================================
// INTERVAL HOOK
// =============================================================================

export function useInterval(callback: () => void, delay: number | null) {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (delay === null) return;

    const id = setInterval(() => savedCallback.current(), delay);
    return () => clearInterval(id);
  }, [delay]);
}

// =============================================================================
// PREVIOUS VALUE HOOK
// =============================================================================

export function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T | undefined>(undefined);

  useEffect(() => {
    ref.current = value;
  }, [value]);

  return ref.current;
}

