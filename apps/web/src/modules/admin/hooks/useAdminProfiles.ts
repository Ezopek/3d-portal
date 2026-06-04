import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { AdminProfileInventoryResponse } from "@/lib/api-types";

/**
 * Story 33.1 (FR21-PROFILE-INVENTORY-1) — the read-only admin profile inventory.
 *
 * Cache topology (per the story's cache-topology enumeration): `staleTime: 0` +
 * `refetchOnMount: "always"` because the admin must see the TRUE current import/resolve
 * state on tab entry — this points to FR21-PROFILE-INVENTORY-1, NOT to any peer query's
 * value. A future Story 33.2 import success will `invalidateQueries(["admin","profiles"])`;
 * the key contract is reserved here.
 */
export function useAdminProfiles(printerRef: string) {
  return useQuery<AdminProfileInventoryResponse>({
    queryKey: ["admin", "profiles", printerRef],
    queryFn: () => {
      const params = new URLSearchParams({ printer_ref: printerRef });
      return api<AdminProfileInventoryResponse>(`/admin/profiles?${params}`);
    },
    enabled: printerRef.length > 0,
    staleTime: 0,
    refetchOnMount: "always",
  });
}
