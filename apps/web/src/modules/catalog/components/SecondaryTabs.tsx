import type { ModelDetail } from "@/lib/api-types";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/ui/tabs";

import { FilesTab } from "./tabs/FilesTab";
import { OperationalNotesTab } from "./tabs/OperationalNotesTab";
import { PrintsTab } from "./tabs/PrintsTab";

export function SecondaryTabs({ detail }: { detail: ModelDetail }) {
  const filesCount = detail.files.filter(
    (f) => f.kind === "stl" || f.kind === "source" || f.kind === "archive_3mf",
  ).length;
  const opsCount = detail.notes.filter((n) => n.kind !== "description").length;
  return (
    <Tabs defaultValue="files" className="w-full">
      <TabsList>
        <TabsTrigger value="files">Files ({filesCount})</TabsTrigger>
        <TabsTrigger value="prints">Prints ({detail.prints.length})</TabsTrigger>
        <TabsTrigger value="ops">Operational notes ({opsCount})</TabsTrigger>
      </TabsList>
      <TabsContent value="files">
        <FilesTab modelId={detail.id} files={detail.files} />
      </TabsContent>
      <TabsContent value="prints">
        <PrintsTab modelId={detail.id} prints={detail.prints} />
      </TabsContent>
      <TabsContent value="ops">
        <OperationalNotesTab notes={detail.notes} />
      </TabsContent>
    </Tabs>
  );
}
