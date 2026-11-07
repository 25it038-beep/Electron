/**
 * Aria Unified Memory Coordinator.
 * Consolidates Conversation, Knowledge, Computer Actions, Procedural Workflows, and Working Memory.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

export interface MemoryRecord {
  id: string;
  category: 'conversation' | 'personal_knowledge' | 'computer_action' | 'procedural' | 'working';
  key: string;
  value: string;
  metadata?: Record<string, unknown>;
  timestamp: number;
}

export class MemoryCoordinator {
  private storagePath: string;
  private memories: Map<string, MemoryRecord> = new Map();

  constructor(customStorageDir?: string) {
    const dir = customStorageDir || path.join(os.homedir(), '.electorn');
    if (!fs.existsSync(dir)) {
      try { fs.mkdirSync(dir, { recursive: true }); } catch (e) {}
    }
    this.storagePath = path.join(dir, 'aria_unified_memory.json');
    this.load();
  }

  public store(category: MemoryRecord['category'], key: string, value: string, metadata?: Record<string, unknown>): MemoryRecord {
    const id = `mem_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    const record: MemoryRecord = {
      id,
      category,
      key,
      value,
      metadata,
      timestamp: Date.now(),
    };
    this.memories.set(id, record);
    this.save();
    return record;
  }

  public query(term: string, category?: MemoryRecord['category'], limit: number = 5): MemoryRecord[] {
    const clean = term.toLowerCase().trim();
    const results: MemoryRecord[] = [];

    for (const mem of this.memories.values()) {
      if (category && mem.category !== category) continue;
      if (mem.key.toLowerCase().includes(clean) || mem.value.toLowerCase().includes(clean)) {
        results.push(mem);
        if (results.length >= limit) break;
      }
    }
    return results;
  }

  public getRecentActions(limit: number = 5): MemoryRecord[] {
    const actions = Array.from(this.memories.values())
      .filter(m => m.category === 'computer_action')
      .sort((a, b) => b.timestamp - a.timestamp);
    return actions.slice(0, limit);
  }

  public getRecentConversations(limit: number = 5): MemoryRecord[] {
    const convs = Array.from(this.memories.values())
      .filter(m => m.category === 'conversation')
      .sort((a, b) => b.timestamp - a.timestamp);
    return convs.slice(0, limit);
  }

  public getProceduralWorkflows(): MemoryRecord[] {
    return Array.from(this.memories.values()).filter(m => m.category === 'procedural');
  }

  private load(): void {
    try {
      if (fs.existsSync(this.storagePath)) {
        const raw = fs.readFileSync(this.storagePath, 'utf-8');
        const arr = JSON.parse(raw);
        for (const item of arr) {
          this.memories.set(item.id, item);
        }
      }
    } catch (e) {}
  }

  private save(): void {
    try {
      const arr = Array.from(this.memories.values());
      fs.writeFileSync(this.storagePath, JSON.stringify(arr, null, 2), 'utf-8');
    } catch (e) {}
  }
}
