export type Status = "not_printed" | "in_progress" | "printed" | "needs_revision";
export type Source =
  | "printables" | "thangs" | "thingiverse" | "makerworld"
  | "creality_cloud" | "own" | "premium" | "unknown";
export type Category =
  | "decorations" | "printer_3d" | "gridfinity" | "multiboard"
  | "tools" | "practical" | "premium" | "own_models" | "other";

export interface Print {
  path: string;
  date: string;
  notes_en: string;
  notes_pl: string;
}

export interface Model {
  id: string;
  name_en: string;
  name_pl: string;
  path: string;
  category: Category;
  subcategory: string;
  tags: string[];
  source: Source;
  printables_id: string | null;
  thangs_id: string | null;
  makerworld_id: string | null;
  source_url: string | null;
  rating: number | null;
  status: Status;
  notes: string;
  thumbnail: string | null;
  thumbnail_url: string | null;
  date_added: string;
  prints: Print[];
}

export interface ModelListItem {
  id: string;
  name_en: string;
  name_pl: string;
  category: Category;
  tags: string[];
  source: Source;
  status: Status;
  rating: number | null;
  thumbnail_url: string | null;
  has_3d: boolean;
  date_added: string;
}

export interface ModelListResponse {
  models: ModelListItem[];
  total: number;
}
