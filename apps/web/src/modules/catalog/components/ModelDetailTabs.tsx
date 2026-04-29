import { useTranslation } from "react-i18next";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/ui/tabs";

import type { Model } from "@/modules/catalog/types";

import { FileList } from "./FileList";
import { InfoTab } from "./InfoTab";
import { PrintsTab } from "./PrintsTab";

export function ModelDetailTabs({ model }: { model: Model }) {
  const { t } = useTranslation();
  return (
    <Tabs defaultValue="info" className="w-full">
      <TabsList>
        <TabsTrigger value="info">{t("catalog.tabs.info")}</TabsTrigger>
        <TabsTrigger value="files">{t("catalog.tabs.files")}</TabsTrigger>
        <TabsTrigger value="prints">{t("catalog.tabs.prints")} ({model.prints.length})</TabsTrigger>
      </TabsList>
      <TabsContent value="info"><InfoTab model={model} /></TabsContent>
      <TabsContent value="files"><FileList modelId={model.id} /></TabsContent>
      <TabsContent value="prints"><PrintsTab modelId={model.id} prints={model.prints} /></TabsContent>
    </Tabs>
  );
}
