import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { AuditLogResponse } from "@/lib/api-types";

export function useAuditLog(opts: {
  entity_type?: string;
  entity_id?: string;
  limit?: number;
}) {
  const params = new URLSearchParams();
  if (opts.entity_type !== undefined) params.set("entity_type", opts.entity_type);
  if (opts.entity_id !== undefined) params.set("entity_id", opts.entity_id);
  params.set("limit", String(opts.limit ?? 50));
  const path = `/admin/audit-log?${params.toString()}`;
  return useQuery<AuditLogResponse>({
    queryKey: [
      "sot",
      "audit-log",
      opts.entity_type ?? null,
      opts.entity_id ?? null,
      opts.limit ?? 50,
    ],
    queryFn: () => api<AuditLogResponse>(path, {}, { authenticated: true }),
    staleTime: 10 * 1000,
  });
}
