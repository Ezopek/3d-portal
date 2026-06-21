import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ProfileLibraryListResponse, ProfileType } from "@/lib/api-types";

/**
 * PROFILE-LIB-1 (AC-17) — the operator profile-block inventory list.
 *
 * Cache topology: `staleTime: 0` + `refetchOnMount: "always"` because the
 * admin must see the TRUE current inventory state on entry. The query key namespace is
 * `["admin", "profile-library", …]`, independent from Profile Offers.
 */
export function useProfileLibrary(profileType?: ProfileType) {
  return useQuery<ProfileLibraryListResponse>({
    queryKey: ["admin", "profile-library", profileType ?? "all"],
    queryFn: () => {
      const qs = profileType ? `?profile_type=${profileType}` : "";
      return api<ProfileLibraryListResponse>(`/admin/profiles/library${qs}`);
    },
    staleTime: 0,
    refetchOnMount: "always",
  });
}
