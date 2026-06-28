import { DsProviders, ModelCard } from "portal-web";

// ModelCard renders a <Link> (TanStack Router) and reads i18n. DsProviders
// (shipped in the bundle via cfg.extraEntries) supplies the shared router
// context so <Link> resolves. thumbnail_file_id=null + image_count=0 renders
// the themed "no preview" placeholder — a clean state with no API images.
const model = {
  id: "demo-1",
  slug: "wspornik-katowy-30",
  name_en: "Angle bracket 30°",
  name_pl: "Wspornik kątowy 30°",
  category_id: "c1",
  source: "printables",
  status: "printed",
  rating: null,
  thumbnail_file_id: null,
  date_added: "2026-01-01",
  deleted_at: null,
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
  tags: [
    { id: "t1", slug: "wsporniki" },
    { id: "t2", slug: "petg" },
  ],
  gallery_file_ids: [],
  image_count: 0,
};

export function CatalogCard() {
  return (
    <DsProviders>
      <div className="w-72">
        <ModelCard model={model as never} />
      </div>
    </DsProviders>
  );
}
