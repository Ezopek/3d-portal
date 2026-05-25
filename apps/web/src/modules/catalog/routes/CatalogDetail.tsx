import { useParams } from "@tanstack/react-router";

import { DescriptionPanel } from "@/modules/catalog/components/DescriptionPanel";
import { ExternalLinksPanel } from "@/modules/catalog/components/ExternalLinksPanel";
import { MetadataPanel } from "@/modules/catalog/components/MetadataPanel";
import { ModelGallery } from "@/modules/catalog/components/ModelGallery";
import { ModelHero } from "@/modules/catalog/components/ModelHero";
import { SecondaryTabs } from "@/modules/catalog/components/SecondaryTabs";
import { useModel } from "@/modules/catalog/hooks/useModel";
import { EmptyState } from "@/ui/custom/EmptyState";
import { LoadingState } from "@/ui/custom/LoadingState";

import type { ModelDetail } from "@/lib/api-types";

/**
 * Initiative 18 Story 30.2 round-4 — pure presentational layer. Takes a
 * fully-resolved ModelDetail and renders the canonical catalog detail
 * tree. Reusable from any context that already owns the ModelDetail
 * (MemberShareView passes the share-probe result here directly so the
 * post-resolve revocation race window stays atomic — validation +
 * rendering share the same response).
 */
export function CatalogDetailRender({ detail }: { detail: ModelDetail }) {
  return (
    <article className="space-y-4">
      <ModelHero detail={detail} />
      <div className="grid grid-cols-1 gap-4 px-4 md:grid-cols-[36%_1fr]">
        <ModelGallery
          modelId={detail.id}
          files={detail.files}
          thumbnailFileId={detail.thumbnail_file_id}
        />
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

/**
 * Initiative 18 Story 30.2 — fetches by id then delegates render to
 * `CatalogDetailRender`. Used by the `/catalog/$id` route wrapper.
 * MemberShareView does NOT use this helper — it owns its own fetch
 * (`useShareModelProbe`) and calls `CatalogDetailRender` directly so
 * validation + rendering stay atomic.
 */
export function CatalogDetailBody({ id }: { id: string }) {
  const { data: detail, isLoading, isError, refetch } = useModel(id);

  if (isLoading) {
    return <LoadingState variant="skeleton-detail" />;
  }
  if (isError || detail === undefined) {
    return (
      <EmptyState
        messageKey="errors.network"
        tone="error"
        action={{
          labelKey: "common.retry",
          onClick: () => void refetch(),
        }}
      />
    );
  }

  return <CatalogDetailRender detail={detail} />;
}

export function CatalogDetail() {
  const { id } = useParams({ from: "/catalog/$id" });
  return <CatalogDetailBody id={id} />;
}
