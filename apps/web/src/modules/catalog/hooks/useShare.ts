import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

import type { ShareModelView } from "../types-share";

export function useShare(token: string) {
  return useQuery<ShareModelView>({
    queryKey: ["share", token],
    queryFn: () => api<ShareModelView>(`/share/${token}`),
    retry: 0,
  });
}
