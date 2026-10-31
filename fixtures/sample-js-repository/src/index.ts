import { usedHelper } from "./utils";
import { processServiceA } from "./serviceA";

export function main(): void {
  const result = usedHelper("CodeImpact");
  console.log("Main result:", result);
  processServiceA();
}

main();
