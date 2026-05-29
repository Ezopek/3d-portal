import { Link } from "@tanstack/react-router";
import { BookOpen, Boxes } from "lucide-react";
import { useTranslation } from "react-i18next";

import { LowStockCard } from "@/modules/spools/components/LowStockCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/ui/card";

interface TileProps {
  to: string;
  labelKey: string;
  descriptionKey: string;
  icon: React.ReactNode;
}

function Tile({ to, labelKey, descriptionKey, icon }: TileProps) {
  const { t } = useTranslation();
  return (
    <Link to={to} className="block transition-shadow hover:shadow-md focus:outline-none">
      <Card className="h-full">
        <CardHeader className="flex flex-row items-center gap-3">
          <span className="text-muted-foreground">{icon}</span>
          <CardTitle>{t(labelKey)}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{t(descriptionKey)}</p>
        </CardContent>
      </Card>
    </Link>
  );
}

export function LandingPage() {
  const { t } = useTranslation();
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 px-6 py-10">
      <div>
        <h1 className="text-2xl font-semibold">{t("landing.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("landing.subtitle")}</p>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Tile
          to="/catalog"
          labelKey="landing.tile.catalog.label"
          descriptionKey="landing.tile.catalog.description"
          icon={<BookOpen className="size-5" />}
        />
        <Tile
          to="/spools"
          labelKey="landing.tile.spools.label"
          descriptionKey="landing.tile.spools.description"
          icon={<Boxes className="size-5" />}
        />
      </div>
      <LowStockCard />
    </div>
  );
}
