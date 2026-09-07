import { PendingEdit } from "@/types/staffReview";

function unescapeSegment(segment: string): string {
  return segment.replace(/~1/g, "/").replace(/~0/g, "~");
}

function parsePath(path: string): string[] {
  if (!path.startsWith("/")) return [];
  if (path === "/") return [];
  return path.split("/").slice(1).map(unescapeSegment);
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export function applyEdits<T>(document: T, edits: PendingEdit[]): T {
  const result = clone(document) as unknown;
  for (const edit of edits) {
    const parts = parsePath(edit.path);
    if (parts.length === 0) continue;
    let parent: unknown = result;
    for (const part of parts.slice(0, -1)) {
      if (parent === null || typeof parent !== "object") {
        parent = undefined;
        break;
      }
      const key = Array.isArray(parent) && /^\d+$/.test(part) ? Number(part) : part;
      parent = (parent as Record<string | number, unknown>)[key as string | number];
    }
    if (parent === null || typeof parent !== "object") continue;
    const last = parts[parts.length - 1];
    if (Array.isArray(parent)) {
      const index = last === "-" ? parent.length : Number(last);
      if (edit.op === "remove" && Number.isInteger(index)) {
        parent.splice(index, 1);
      } else if (edit.op === "add") {
        if (last === "-" || index === parent.length) parent.push(clone(edit.value));
        else if (Number.isInteger(index)) parent.splice(index, 0, clone(edit.value));
      } else if (edit.op === "replace" && Number.isInteger(index) && index < parent.length) {
        parent[index] = clone(edit.value);
      }
    } else {
      const record = parent as Record<string, unknown>;
      if (edit.op === "remove") delete record[last];
      else record[last] = clone(edit.value);
    }
  }
  return result as T;
}
