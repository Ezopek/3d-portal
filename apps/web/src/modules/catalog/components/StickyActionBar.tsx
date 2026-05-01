import { Box, Download, Share2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { AuthGate } from "@/shell/AuthGate";
import { Button } from "@/ui/button";

interface Props {
  downloadHref: string | null;
  on3DOpen: () => void;
  onShareOpen: () => void;
}

export function StickyActionBar({ downloadHref, on3DOpen, onShareOpen }: Props) {
  const { t } = useTranslation();
  return (
    <div className="sticky bottom-0 z-20 flex gap-2 border-t border-border bg-background/95 p-3 backdrop-blur md:static md:border-0 md:bg-transparent md:p-0">
      {downloadHref !== null && (
        <Button variant="default" size="sm" className="flex-1" render={<a href={downloadHref} />}>
          <Download className="mr-2 size-4" /> {t("catalog.actions.download_all")}
        </Button>
      )}
      <Button variant="outline" size="sm" className="flex-1" onClick={on3DOpen}>
        <Box className="mr-2 size-4" /> {t("catalog.actions.view_3d")}
      </Button>
      <AuthGate>
        <Button variant="outline" size="sm" className="flex-1" onClick={onShareOpen}>
          <Share2 className="mr-2 size-4" /> {t("catalog.actions.share")}
        </Button>
      </AuthGate>
    </div>
  );
}
