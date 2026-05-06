import { useMemo } from "react";

import type { StlFile } from "../types";

export type FileIndex = {
  sorted: readonly StlFile[];
  positionOf: (id: string) => number; // 1-based, 0 if unknown
};

export function useFileIndex(files: readonly StlFile[]): FileIndex {
  return useMemo(() => {
    const sorted = [...files].sort((a, b) => {
      const cmp = a.name.toLowerCase().localeCompare(b.name.toLowerCase());
      if (cmp !== 0) return cmp;
      // Tiebreak by codepoint order (deterministic regardless of locale).
      if (a.name < b.name) return -1;
      if (a.name > b.name) return 1;
      return 0;
    });
    const positions = new Map<string, number>();
    sorted.forEach((f, i) => positions.set(f.id, i + 1));
    const positionOf = (id: string) => positions.get(id) ?? 0;
    return { sorted, positionOf };
  }, [files]);
}
