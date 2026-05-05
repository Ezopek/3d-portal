import { useParams } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { DescriptionPanel } from "@/modules/catalog/components/DescriptionPanel";
import { ExternalLinksPanel } from "@/modules/catalog/components/ExternalLinksPanel";
import { MetadataPanel } from "@/modules/catalog/components/MetadataPanel";
import { ModelGallery } from "@/modules/catalog/components/ModelGallery";
import { ModelHero } from "@/modules/catalog/components/ModelHero";
import { SecondaryTabs } from "@/modules/catalog/components/SecondaryTabs";
import { useModel } from "@/modules/catalog/hooks/useModel";

export function CatalogDetail() {
  const { id } = useParams({ from: "/catalog/$id" });
  const { t } = useTranslation();
  const { data: detail, isLoading, isError } = useModel(id);

  if (isLoading) {
    return <div className="p-4 text-sm text-muted-foreground">…</div>;
  }
  if (isError || detail === undefined) {
    return <div className="p-4 text-sm text-destructive">{t("errors.network")}</div>;
  }

  return (
    <article className="space-y-4">
      <ModelHero detail={detail} />
      <div className="grid grid-cols-1 gap-4 px-4 md:grid-cols-[36%_1fr]">
        <ModelGallery modelId={detail.id} files={detail.files} />
        <div className="space-y-3">
          <DescriptionPanel detail={detail} />
          <ExternalLinksPanel links={detail.external_links} />
          <MetadataPanel detail={detail} />
        </div>
      </div>
      <div className="px-4">
        <SecondaryTabs detail={detail} />
      </div>
    </article>
  );
}
