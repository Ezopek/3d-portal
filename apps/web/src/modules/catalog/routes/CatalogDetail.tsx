import { useParams } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useFiles } from "@/modules/catalog/hooks/useFiles";
import { useModel } from "@/modules/catalog/hooks/useModel";
import { Gallery } from "@/ui/custom/Gallery";
import { ModelViewer } from "@/ui/custom/ModelViewer";

import { ModelDetailTabs } from "@/modules/catalog/components/ModelDetailTabs";
import { ShareDialog } from "@/modules/catalog/components/ShareDialog";
import { StickyActionBar } from "@/modules/catalog/components/StickyActionBar";

export function CatalogDetail() {
  const { id } = useParams({ from: "/catalog/$id" });
  const { i18n } = useTranslation();
  const { data: model } = useModel(id);
  const { data: files } = useFiles(id);
  const [view3d, setView3d] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);

  if (model === undefined) return <div className="p-4 text-sm text-muted-foreground">…</div>;

  const primary = i18n.language.startsWith("pl") ? model.name_pl : model.name_en;
  const secondary = i18n.language.startsWith("pl") ? model.name_en : model.name_pl;

  // Build gallery: catalog images/* + own prints/* (computed renders fallback if nothing else).
  const images: string[] = [];
  const fileList = files?.files ?? [];
  for (const f of fileList) {
    if (f.startsWith("images/") && /\.(png|jpg|jpeg|webp)$/i.test(f)) {
      images.push(`/api/files/${id}/${f}`);
    }
  }
  for (const p of model.prints) {
    const rel = p.path.split("/").slice(2).join("/");
    images.push(`/api/files/${id}/${rel}`);
  }
  // Fallback to computed renders if no images at all.
  if (images.length === 0) {
    for (const view of ["front", "iso", "side", "top"]) {
      images.push(`/api/files/${id}/${view}.png`);
    }
  }

  const firstStl = fileList.find((f) => f.toLowerCase().endsWith(".stl"));
  const stlHref = firstStl !== undefined ? `/api/files/${id}/${firstStl}` : null;

  return (
    <div className="grid gap-4 p-4 md:grid-cols-[1fr_1fr]">
      <div>
        {view3d && stlHref !== null ? <ModelViewer src={stlHref} /> : <Gallery images={images.map((url) => ({ url, path: url }))} />}
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
