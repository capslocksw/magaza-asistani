export interface ContractsBundle {
  $id: string;
  $defs: Record<string, unknown>;
  [key: string]: unknown;
}
export declare function buildBundle(): ContractsBundle;
