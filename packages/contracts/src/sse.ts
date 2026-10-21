import type { SseEvent } from "./generated/contracts";

/** Serialises one chat event in SSE wire format (`event:` + `data:` lines). */
export function encodeSseEvent(event: SseEvent): string {
  return `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`;
}

/**
 * Incremental SSE parser for fetch() streams (EventSource cannot POST).
 * Feed it decoded text chunks; it returns the complete events seen so far.
 */
export class SseParser {
  private buffer = "";

  push(chunk: string): SseEvent[] {
    this.buffer += chunk.replace(/\r\n/g, "\n");
    const events: SseEvent[] = [];
    let boundary = this.buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const block = this.buffer.slice(0, boundary);
      this.buffer = this.buffer.slice(boundary + 2);
      const data = block
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).replace(/^ /, ""))
        .join("\n");
      if (data) {
        try {
          events.push(JSON.parse(data) as SseEvent);
        } catch {
          // Ignore malformed frames; the stream continues.
        }
      }
      boundary = this.buffer.indexOf("\n\n");
    }
    return events;
  }
}
