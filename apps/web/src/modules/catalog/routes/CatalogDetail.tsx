import { useParams } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { readToken } from "@/lib/auth";
import { useFiles } from "@/modules/catalog/hooks/useFiles";
import { useModel } from "@/modules/catalog/hooks/useModel";
import { useClearThumbnail, useSetThumbnail } from "@/modules/catalog/hooks/useThumbnail";
import { Gallery, type GalleryImage } from "@/ui/custom/Gallery";
import { ModelViewer } from "@/ui/custom/ModelViewer";

import { ModelDetailTabs } from "@/modules/catalog/components/ModelDetailTabs";
import { ShareDialog } from "@/modules/catalog/components/ShareDialog";
import { StickyActionBar } from "@/modules/catalog/components/StickyActionBar";

export function CatalogDetail() {
  const { id } = useParams({ from: "/catalog/$id" });
  const { i18n, t } = useTranslation();
  const { data: model } = useModel(id);
  const { data: files } = useFiles(id);
  const [view3d, setView3d] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);

  const setThumb = useSetThumbnail(id);
  const clearThumb = useClearThumbnail(id);
  const isAdmin = readToken() !== null;

  if (model === undefined) return <div className="p-4 text-sm text-muted-foreground">…</div>;

  const primary = i18n.language.startsWith("pl") ? model.name_pl : model.name_en;
  const secondary = i18n.language.startsWith("pl") ? model.name_en : model.name_pl;

  const fileList = files?.files ?? [];
  const candidates: GalleryImage[] = [];

  // 1. catalog images
  for (const f of fileList) {
    if (f.startsWith("images/") && /\.(png|jpe?g|webp)$/i.test(f)) {
      candidates.push({ url: `/api/files/${id}/${f}`, path: f });
    }
  }

  // 2. own prints, sorted desc by date
  const printsSorted = [...model.prints].sort((a, b) => b.date.localeCompare(a.date));
  for (const p of printsSorted) {
    const segments = p.path.split("/");
    const rel = segments.slice(model.path.split("/").length).join("/");
    if (/\.(png|jpe?g|webp)$/i.test(rel)) {
      candidates.push({ url: `/api/files/${id}/${rel}`, path: rel });
    }
  }

  // 3. computed renders (always offered; <img onError> hides 404s if any)
  for (const view of ["iso", "front", "side", "top"]) {
    candidates.push({ url: `/api/files/${id}/${view}.png`, path: `${view}.png` });
  }

  // dedupe by path (preserves order)
  const seen = new Set<string>();
  const uniq = candidates.filter((c) => (seen.has(c.path) ? false : seen.add(c.path)));

  // figure out which path the API has resolved as the current default
  const currentDefaultPath: string | null = (() => {
    if (model.thumbnail_url === null) return null;
    const prefix = `/api/files/${id}/`;
    return model.thumbnail_url.startsWith(prefix)
      ? model.thumbnail_url.slice(prefix.length)
      : null;
  })();

  const firstStl = fileList.find((f) => f.toLowerCase().endsWith(".stl"));
  const stlHref = firstStl !== undefined ? `/api/files/${id}/${firstStl}` : null;

  return (
    <div className="grid gap-4 p-4 md:grid-cols-[1fr_1fr]">
      <div>
        {view3d && stlHref !== null ? (
          <ModelViewer src={stlHref} />
        ) : (
          <Gallery
            images={uniq}
            currentDefaultPath={currentDefaultPath}
            onSetDefault={
              isAdmin
                ? (path) =>
                    setThumb.mutate(path, {
                      onSuccess: () => toast.success(t("toasts.thumbnail_updated")),
                    })
                : undefined
            }
            onClearDefault={
              isAdmin
                ? () =>
                    clearThumb.mutate(undefined, {
                      onSuccess: () => toast.success(t("toasts.thumbnail_cleared")),
                    })
                : undefined
            }
          />
        )}
      </div>
      <div>
        <h1 className="text-2xl font-semibold">{primary}</h1>
        <p className="text-sm text-muted-foreground">{secondary}</p>
        <div className="mt-2 flex flex-wrap gap-1">
          {model.tags.map((tag) => (
            <span key={tag} className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
              {tag}
            </span>
          ))}
        </div>
        <div className="mt-4">
          <ModelDetailTabs model={model} />
        </div>
        <div className="mt-4">
          <StickyActionBar
            stlHref={stlHref}
            on3DOpen={() => setView3d((v) => !v)}
            onShareOpen={() => setShareOpen(true)}
          />
        </div>
      </div>
      <ShareDialog modelId={id} open={shareOpen} onOpenChange={setShareOpen} />
    </div>
  );
}
