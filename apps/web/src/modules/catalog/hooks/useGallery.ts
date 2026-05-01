import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/lib/api";
import {
  type GalleryImage,
  type ModelLike,
  pickGalleryCandidates,
} from "@/lib/galleryCandidates";

interface FilesResponse {
  files: string[];
}

export interface UseGalleryResult {
  images: GalleryImage[] | undefined;
  isFetching: boolean;
  activate: () => void;
}

export function useGallery(model: ModelLike): UseGalleryResult {
  // `enabled` is a stateful gate so React Query owns the fetch lifecycle:
  // after activate() flips it true, react-query honours staleTime (5 min) and
  // skips subsequent refetches within that window. With `enabled: false` and
  // manual refetch() the staleTime would not apply.
  const [enabled, setEnabled] = useState(false);

  const query = useQuery<GalleryImage[]>({
    queryKey: ["catalog", "gallery", model.id],
    queryFn: async () => {
      const res = await api<FilesResponse>(`/catalog/models/${model.id}/files`);
      return pickGalleryCandidates(model, res.files);
    },
    enabled,
    staleTime: 5 * 60 * 1000,
  });

  return {
    images: query.data,
    isFetching: query.isFetching,
    activate: () => setEnabled(true),
  };
}
