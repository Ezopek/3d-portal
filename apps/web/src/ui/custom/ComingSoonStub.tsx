import { useTranslation } from "react-i18next";

import { Card, CardContent, CardHeader, CardTitle } from "@/ui/card";

export function ComingSoonStub({ moduleKey }: { moduleKey: string }) {
  const { t } = useTranslation();
  return (
    <div className="grid place-items-center p-8">
      <Card className="max-w-md">
        <CardHeader>
          <CardTitle>{t(`modules.${moduleKey}`)}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{t("common.coming_soon")}</p>
        </CardContent>
      </Card>
    </div>
  );
}
