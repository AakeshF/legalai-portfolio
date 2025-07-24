// Cache management utilities for offline support and performance

const CACHE_PREFIX = 'legal-ai';
const CACHE_VERSION = 'v1';
const CACHE_NAME = `${CACHE_PREFIX}-${CACHE_VERSION}`;

// Cache duration in milliseconds
const CACHE_DURATIONS = {
  documents: 24 * 60 * 60 * 1000, // 24 hours
  chat: 1 * 60 * 60 * 1000, // 1 hour
  metadata: 7 * 24 * 60 * 60 * 1000, // 7 days
};

export interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expires: number;
}

// Local storage cache wrapper
export class LocalCache {
  private prefix: string;

  constructor(prefix = 'legal-ai-cache') {
    this.prefix = prefix;
  }

  // Set item with expiration
  set<T>(key: string, data: T, duration?: number): void {
    const expires = Date.now() + (duration || CACHE_DURATIONS.documents);
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      expires,
    };

    try {
      localStorage.setItem(`${this.prefix}-${key}`, JSON.stringify(entry));
    } catch (error) {
      console.error('Failed to cache data:', error);
      // Clear old entries if storage is full
      this.clearExpired();
    }
  }

  // Get item if not expired
  get<T>(key: string): T | null {
    try {
      const item = localStorage.getItem(`${this.prefix}-${key}`);
      if (!item) return null;

      const entry: CacheEntry<T> = JSON.parse(item);
      
      // Check if expired
      if (Date.now() > entry.expires) {
        this.remove(key);
        return null;
      }

      return entry.data;
    } catch (error) {
      console.error('Failed to get cached data:', error);
      return null;
    }
  }

  // Remove specific item
  remove(key: string): void {
    localStorage.removeItem(`${this.prefix}-${key}`);
  }

  // Clear all expired entries
  clearExpired(): void {
    const keys = Object.keys(localStorage);
    const now = Date.now();

    keys.forEach(key => {
      if (key.startsWith(this.prefix)) {
        try {
          const item = localStorage.getItem(key);
          if (item) {
            const entry: CacheEntry<any> = JSON.parse(item);
            if (now > entry.expires) {
              localStorage.removeItem(key);
            }
          }
        } catch (error) {
          // Remove corrupted entries
          localStorage.removeItem(key);
        }
      }
    });
  }

  // Clear all cache
  clearAll(): void {
    const keys = Object.keys(localStorage);
    keys.forEach(key => {
      if (key.startsWith(this.prefix)) {
        localStorage.removeItem(key);
      }
    });
  }

  // Get cache size
  getSize(): { count: number; bytes: number } {
    let count = 0;
    let bytes = 0;

    Object.keys(localStorage).forEach(key => {
      if (key.startsWith(this.prefix)) {
        count++;
        const item = localStorage.getItem(key);
        if (item) {
          bytes += item.length * 2; // Approximate bytes (UTF-16)
        }
      }
    });

    return { count, bytes };
  }
}

// IndexedDB cache for larger data
export class IndexedDBCache {
  private dbName: string;
  private storeName: string;
  private db: IDBDatabase | null = null;

  constructor(dbName = 'legal-ai-db', storeName = 'cache') {
    this.dbName = dbName;
    this.storeName = storeName;
  }

  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, 1);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          db.createObjectStore(this.storeName, { keyPath: 'key' });
        }
      };
    });
  }

  async set<T>(key: string, data: T, duration?: number): Promise<void> {
    if (!this.db) await this.init();
    
    const expires = Date.now() + (duration || CACHE_DURATIONS.documents);
    const entry = {
      key,
      data,
      timestamp: Date.now(),
      expires,
    };

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.put(entry);

      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async get<T>(key: string): Promise<T | null> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      const request = store.get(key);

      request.onsuccess = () => {
        const entry = request.result;
        if (!entry) {
          resolve(null);
          return;
        }

        // Check if expired
        if (Date.now() > entry.expires) {
          this.remove(key);
          resolve(null);
          return;
        }

        resolve(entry.data);
      };
      request.onerror = () => reject(request.error);
    });
  }

  async remove(key: string): Promise<void> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.delete(key);

      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async clearAll(): Promise<void> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.clear();

      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }
}

// Create singleton instances
export const localCache = new LocalCache();
export const indexedDBCache = new IndexedDBCache();

// Cache key generators
export const cacheKeys = {
  documents: () => 'documents-list',
  document: (id: string) => `document-${id}`,
  chatHistory: (sessionId: string) => `chat-${sessionId}`,
  userProfile: () => 'user-profile',
  organization: () => 'organization-data',
  securityStatus: () => 'security-status',
};