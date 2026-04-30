export interface ShareModelView {
  id: string;
  name_en: string;
  name_pl: string;
  category: string;
  tags: string[];
  thumbnail_url: string | null;
  has_3d: boolean;
  images: string[];
  notes_en: string;
  notes_pl: string;
  stl_url: string | null;
}
