import type { ModelDetail } from "@/lib/api-types";
import { useAuth } from "@/shell/AuthContext";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/ui/tabs";

import { ActivityTab } from "./tabs/ActivityTab";
import { FilesTab } from "./tabs/FilesTab";
import { OperationalNotesTab } from "./tabs/OperationalNotesTab";
import { PhotosTab } from "./tabs/PhotosTab";
import { PrintsTab } from "./tabs/PrintsTab";

export function SecondaryTabs({ detail }: { detail: ModelDetail }) {
  const { isAdmin } = useAuth();
  const filesCount = detail.files.filter(
    (f) => f.kind === "stl" || f.kind === "source" || f.kind === "archive_3mf",
  ).length;
  const photosCount = detail.files.filter(
    (f) => f.kind === "image" || f.kind === "print",
  ).length;
  const opsCount = detail.notes.filter((n) => n.kind !== "description").length;
  return (
    <Tabs defaultValue="files" className="w-full">
      <div className="overflow-x-auto">
        <TabsList className="flex w-max flex-nowrap">
          <TabsTrigger value="files">Files ({filesCount})</TabsTrigger>
          {isAdmin && <TabsTrigger value="photos">Photos ({photosCount}) ✏</TabsTrigger>}
          <TabsTrigger value="prints">Prints ({detail.prints.length})</TabsTrigger>
          <TabsTrigger value="ops">Operational notes ({opsCount})</TabsTrigger>
          {isAdmin && <TabsTrigger value="activity">Activity ✏</TabsTrigger>}
        </TabsList>
      </div>
      <TabsContent value="files">
        <FilesTab modelId={detail.id} files={detail.files} />
      </TabsContent>
      {isAdmin && (
        <TabsContent value="photos">
          <PhotosTab detail={detail} />
        </TabsContent>
      )}
      <TabsContent value="prints">
        <PrintsTab modelId={detail.id} prints={detail.prints} />
      </TabsContent>
      <TabsContent value="ops">
        <OperationalNotesTab modelId={detail.id} notes={detail.notes} />
      </TabsContent>
      {isAdmin && (
        <TabsContent value="activity">
          <ActivityTab modelId={detail.id} />
        </TabsContent>
      )}
    </Tabs>
  );
}
