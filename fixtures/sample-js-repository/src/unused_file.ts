export function abandonedComputation(data: number[]): number {
  return data.reduce((acc, curr) => acc + curr, 0);
}

export const DEAD_CONSTANT = 9999;
