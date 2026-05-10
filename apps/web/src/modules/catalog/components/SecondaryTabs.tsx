import { Pencil } from "lucide-react";
import { useTranslation } from "react-i18next";

import type { ModelDetail } from "@/lib/api-types";
import { useAuth } from "@/shell/AuthContext";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/ui/tabs";

import { ActivityTab } from "./tabs/ActivityTab";
import { FilesTab } from "./tabs/FilesTab";
import { OperationalNotesTab } from "./tabs/OperationalNotesTab";
import { PhotosTab } from "./tabs/PhotosTab";
import { PrintsTab } from "./tabs/PrintsTab";

function EditableHint() {
  const { t } = useTranslation();
  return (
    <>
      <Pencil className="size-3" aria-hidden />
      <span className="sr-only">{t("a11y.editable")}</span>
    </>
  );
}

export function SecondaryTabs({ detail }: { detail: ModelDetail }) {
  const { t } = useTranslation();
  const { isAdmin } = useAuth();
  const filesCount = detail.files.filter(
    (f) => f.kind === "stl" || f.kind === "source" || f.kind === "archive_3mf",
  ).length;
  const photosCount = detail.files.filter(
    (f) => f.kind === "image" || f.kind === "print",
  ).length;
  const opsCount = detail.notes.filter((n) => n.kind !== "description").length;
  return (
    <Tabs defaultValue="files" className="w-full min-w-0">
      {/*
       * Mobile tabs row: the outer div MUST have `min-w-0` so it can shrink
       * inside the parent flex/grid layout (otherwise the inline-grid TabsList
       * grows to its intrinsic content width and forces the whole page to
       * scroll horizontally on 375px viewports). Inner TabsList uses `w-max`
       * so its own children render without wrapping, and the div scrolls.
       */}
      <div className="min-w-0 max-w-full overflow-x-auto">
        <TabsList className="flex w-max flex-nowrap">
          <TabsTrigger value="files">
            {t("catalog.tabs.files")} ({filesCount})
          </TabsTrigger>
          {isAdmin && (
            <TabsTrigger value="photos" className="gap-1">
              {t("catalog.tabs.photos")} ({photosCount})
              <EditableHint />
            </TabsTrigger>
          )}
          <TabsTrigger value="prints">
            {t("catalog.tabs.prints")} ({detail.prints.length})
          </TabsTrigger>
          <TabsTrigger value="ops">
            {t("catalog.tabs.opsNotes")} ({opsCount})
          </TabsTrigger>
          {isAdmin && (
            <TabsTrigger value="activity" className="gap-1">
              {t("catalog.tabs.activity")}
              <EditableHint />
            </TabsTrigger>
          )}
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
