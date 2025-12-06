// Session Storage with IndexedDB
// Persists conference sessions for history and replay

// ============================================================================
// TYPES
// ============================================================================

export interface ConferenceSession {
  id: string;
  timestamp: Date;
  query: string;
  mode?: string;
  agentCount: number;
  status: "complete" | "error" | "cancelled";
  duration?: number; // milliseconds
  tokensUsed?: number;
  cost?: number;
  // Store the full result for replay
  result?: unknown;
  // Summary for display
  summary?: string;
  // Patient context
  patientContext?: {
    age?: number;
    sex?: string;
    comorbidities?: string[];
  };
}

// ============================================================================
// INDEXEDDB SETUP
// ============================================================================

const DB_NAME = "dialectic-conference";
const DB_VERSION = 1;
const STORE_NAME = "sessions";

let db: IDBDatabase | null = null;

async function openDB(): Promise<IDBDatabase> {
  if (db) return db;

  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    
    request.onsuccess = () => {
      db = request.result;
      resolve(db);
    };

    request.onupgradeneeded = (event) => {
      const database = (event.target as IDBOpenDBRequest).result;
      
      if (!database.objectStoreNames.contains(STORE_NAME)) {
        const store = database.createObjectStore(STORE_NAME, { keyPath: "id" });
        store.createIndex("timestamp", "timestamp", { unique: false });
        store.createIndex("status", "status", { unique: false });
      }
    };
  });
}

// ============================================================================
// CRUD OPERATIONS
// ============================================================================

export async function saveSession(session: ConferenceSession): Promise<void> {
  const database = await openDB();
  
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    
    const request = store.put({
      ...session,
      timestamp: session.timestamp.toISOString(),
    });

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
}

export async function getSession(id: string): Promise<ConferenceSession | null> {
  const database = await openDB();
  
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readonly");
    const store = transaction.objectStore(STORE_NAME);
    const request = store.get(id);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      if (request.result) {
        resolve({
          ...request.result,
          timestamp: new Date(request.result.timestamp),
        });
      } else {
        resolve(null);
      }
    };
  });
}

export async function getAllSessions(limit = 50): Promise<ConferenceSession[]> {
  const database = await openDB();
  
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readonly");
    const store = transaction.objectStore(STORE_NAME);
    const index = store.index("timestamp");
    const request = index.openCursor(null, "prev");

    const sessions: ConferenceSession[] = [];
    let count = 0;

    request.onerror = () => reject(request.error);
    
    request.onsuccess = (event) => {
      const cursor = (event.target as IDBRequest<IDBCursorWithValue>).result;
      
      if (cursor && count < limit) {
        sessions.push({
          ...cursor.value,
          timestamp: new Date(cursor.value.timestamp),
        });
        count++;
        cursor.continue();
      } else {
        resolve(sessions);
      }
    };
  });
}

export async function deleteSession(id: string): Promise<void> {
  const database = await openDB();
  
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    const request = store.delete(id);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
}

export async function clearAllSessions(): Promise<void> {
  const database = await openDB();
  
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    const request = store.clear();

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

export function generateSessionId(): string {
  return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

export function groupSessionsByDate(sessions: ConferenceSession[]): Record<string, ConferenceSession[]> {
  const groups: Record<string, ConferenceSession[]> = {};
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  for (const session of sessions) {
    let key: string;
    const sessionDate = new Date(session.timestamp);

    if (isSameDay(sessionDate, today)) {
      key = "Today";
    } else if (isSameDay(sessionDate, yesterday)) {
      key = "Yesterday";
    } else if (isThisWeek(sessionDate)) {
      key = "This Week";
    } else if (isThisMonth(sessionDate)) {
      key = "This Month";
    } else {
      key = "Older";
    }

    if (!groups[key]) {
      groups[key] = [];
    }
    groups[key].push(session);
  }

  return groups;
}

function isSameDay(d1: Date, d2: Date): boolean {
  return (
    d1.getFullYear() === d2.getFullYear() &&
    d1.getMonth() === d2.getMonth() &&
    d1.getDate() === d2.getDate()
  );
}

function isThisWeek(date: Date): boolean {
  const now = new Date();
  const weekAgo = new Date(now);
  weekAgo.setDate(weekAgo.getDate() - 7);
  return date >= weekAgo && date <= now;
}

function isThisMonth(date: Date): boolean {
  const now = new Date();
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth()
  );
}

// ============================================================================
// HOOKS
// ============================================================================

import { useState, useEffect, useCallback } from "react";

export function useSessions() {
  const [sessions, setSessions] = useState<ConferenceSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadSessions = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getAllSessions();
      setSessions(data);
      setError(null);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const addSession = useCallback(async (session: ConferenceSession) => {
    await saveSession(session);
    await loadSessions();
  }, [loadSessions]);

  const removeSession = useCallback(async (id: string) => {
    await deleteSession(id);
    await loadSessions();
  }, [loadSessions]);

  const clearAll = useCallback(async () => {
    await clearAllSessions();
    await loadSessions();
  }, [loadSessions]);

  return {
    sessions,
    loading,
    error,
    addSession,
    removeSession,
    clearAll,
    refresh: loadSessions,
    grouped: groupSessionsByDate(sessions),
  };
}

