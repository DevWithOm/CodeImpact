export function usedHelper(input: string): string {
  return `Processed: ${input.trim().toLowerCase()}`;
}

export function unusedHelper(count: number): number {
  return count * 42;
}

export interface UnusedType {
  id: string;
  timestamp: number;
}
