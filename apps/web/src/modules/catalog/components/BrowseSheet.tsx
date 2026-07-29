import { LayoutGrid } from "lucide-react";
import { useTranslation } from "react-i18next";

import type { BrowseCategoryRead } from "@/lib/api-types";
import { BrowseCategoryList } from "@/modules/catalog/components/BrowseCategoryList";
import type { CatalogListSearch } from "@/routes/catalog/index";
import { Button } from "@/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/ui/sheet";

interface Props {
  categories: BrowseCategoryRead[];
  activeSlug: string | undefined;
  search: CatalogListSearch;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// Story 51.3 D-1/D-3 — the below-`lg` counterpart to `BrowseRail`: same left
// `Sheet` geometry the "Tagi" sheet already occupies (`w-80 max-w-[85vw]`,
// DESIGN.md:272), same row vocabulary via `BrowseCategoryList` (D-2), reached
// through a trigger distinct in both label and icon from the Tagi/Filters
// triggers (EXPERIENCE.md:333). `lg:hidden` on the trigger because the rail
// already covers `lg`+.
export function BrowseSheet({
  categories,
  activeSlug,
  search,
  isLoading,
  isError,
  onRetry,
  open,
  onOpenChange,
}: Props) {
  const { t } = useTranslation();

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetTrigger
        render={
          <Button
            variant="outline"
            size="sm"
            className="shrink-0 lg:hidden"
            aria-label={t("catalog.browse.openBrowse")}
          >
            <LayoutGrid className="size-3.5" aria-hidden />
            <span className="ml-1.5">{t("catalog.browse.openBrowse")}</span>
          </Button>
        }
      />
      <SheetContent side="left" className="w-80 max-w-[85vw] overflow-y-auto p-0">
        <SheetHeader>
          <SheetTitle>{t("catalog.browse.railLabel")}</SheetTitle>
        </SheetHeader>
        <BrowseCategoryList
          categories={categories}
          activeSlug={activeSlug}
          search={search}
          isLoading={isLoading}
          isError={isError}
          onRetry={onRetry}
          onNavigate={() => onOpenChange(false)}
        />
      </SheetContent>
    </Sheet>
  );
}
