import {
  DndContext,
  type DragEndEvent,
  PointerSensor,
  TouchSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Star, Trash2 } from "lucide-react";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { LoadingState } from "@/ui/custom/LoadingState";
import type { ModelDetail, ModelFileRead } from "@/lib/api-types";
import { cn } from "@/lib/utils";
import { useDeleteFile } from "@/modules/catalog/hooks/mutations/useDeleteFile";
import { useReorderPhotos } from "@/modules/catalog/hooks/mutations/useReorderPhotos";
import { useSetThumbnail } from "@/modules/catalog/hooks/mutations/useSetThumbnail";
import { useUploadFile } from "@/modules/catalog/hooks/mutations/useUploadFile";
import { usePhotos } from "@/modules/catalog/hooks/usePhotos";
import { Button } from "@/ui/button";

interface Props {
  detail: ModelDetail;
}

export function PhotosTab({ detail }: Props) {
  const { t } = useTranslation();
  const photosQuery = usePhotos(detail.id);
  const reorder = useReorderPhotos(detail.id);
  const setThumb = useSetThumbnail(detail.id);
  const del = useDeleteFile(detail.id);
  const upload = useUploadFile(detail.id);
  const photos = photosQuery.data ?? [];
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 250, tolerance: 5 } }),
  );

  function onDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (over === null || active.id === over.id) return;
    const oldIndex = photos.findIndex((p) => p.id === active.id);
    const newIndex = photos.findIndex((p) => p.id === over.id);
    if (oldIndex === -1 || newIndex === -1) return;
    const next = arrayMove(photos, oldIndex, newIndex);
    reorder.mutate(next.map((p) => p.id));
  }

  function onUpload(files: FileList | null) {
    if (files === null) return;
    for (const f of Array.from(files)) {
      upload.mutate({ file: f, kind: "image" });
    }
  }

  if (photosQuery.isLoading) {
    return <LoadingState variant="spinner" />;
  }
  if (photos.length === 0 && !upload.isPending) {
    return (
      <div className="space-y-3 p-3">
        <p className="text-sm text-muted-foreground">{t("catalog.empty.photos")}</p>
        <UploadZone onFiles={onUpload} inputRef={fileInputRef} />
      </div>
    );
  }

  const selected = photos.find((p) => p.id === selectedId) ?? photos[0] ?? null;

  return (
    <div className="grid grid-cols-1 gap-4 p-3 md:grid-cols-[520px_1fr]">
      <div className="space-y-2">
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
          <SortableContext items={photos.map((p) => p.id)} strategy={verticalListSortingStrategy}>
            <ul className="space-y-1">
              {photos.map((p, i) => (
                <SortableRow
                  key={p.id}
                  photo={p}
                  position={i + 1}
                  modelId={detail.id}
                  isSelected={p.id === selected?.id}
                  isThumbnail={detail.thumbnail_file_id === p.id}
                  onSelect={() => setSelectedId(p.id)}
                />
              ))}
            </ul>
          </SortableContext>
        </DndContext>
        <UploadZone onFiles={onUpload} inputRef={fileInputRef} />
      </div>
      {selected !== null && (
        <PhotoDetail
          photo={selected}
          modelId={detail.id}
          isThumbnail={detail.thumbnail_file_id === selected.id}
          onSetThumbnail={() => setThumb.mutate(selected.id)}
          onDelete={() => {
            if (confirm(t("catalog.actions.confirmDeletePhoto", { name: selected.original_name }))) {
              del.mutate(selected.id);
              setSelectedId(null);
            }
          }}
        />
      )}
    </div>
  );
}

function SortableRow({
  photo,
  position,
  modelId,
  isSelected,
  isThumbnail,
  onSelect,
}: {
  photo: ModelFileRead;
  position: number;
  modelId: string;
  isSelected: boolean;
  isThumbnail: boolean;
  onSelect: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: photo.id,
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };
  return (
    <li
      ref={setNodeRef}
      style={style}
      data-testid="photo-row"
      className={cn(
        "flex items-center gap-2 rounded border border-border bg-card p-2 text-xs",
        isSelected && "ring-2 ring-ring",
      )}
    >
      <DragHandle attributes={attributes} listeners={listeners} />
      <button
        type="button"
        onClick={onSelect}
        className="flex flex-1 items-center gap-2 text-left"
      >
        <img
          src={`/api/models/${modelId}/files/${photo.id}/content`}
          alt=""
          className="h-10 w-10 rounded bg-muted object-cover"
        />
        <div className="flex-1 truncate">
          <div className="truncate">{photo.original_name}</div>
          <div className="text-muted-foreground">
            {photo.kind} {isThumbnail && "★"}
          </div>
        </div>
        <span className="text-muted-foreground">#{position}</span>
      </button>
    </li>
  );
}

function PhotoDetail({
  photo,
  modelId,
  isThumbnail,
  onSetThumbnail,
  onDelete,
}: {
  photo: ModelFileRead;
  modelId: string;
  isThumbnail: boolean;
  onSetThumbnail: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="space-y-2 rounded border border-border bg-card p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-medium">{photo.original_name}</div>
          <div className="text-xs text-muted-foreground">
            {photo.kind} · {(photo.size_bytes / 1024).toFixed(1)} KB
            {isThumbnail && " · ★ catalog thumbnail"}
          </div>
        </div>
        <div className="flex gap-2">
          <ThumbnailButton isThumbnail={isThumbnail} onClick={onSetThumbnail} />
          <DeletePhotoButton onClick={onDelete} />
        </div>
      </div>
      <img
        src={`/api/models/${modelId}/files/${photo.id}/content`}
        alt={photo.original_name}
        className="max-h-[600px] w-full rounded bg-muted object-contain"
      />
    </div>
  );
}

function DragHandle({
  attributes,
  listeners,
}: {
  attributes: ReturnType<typeof useSortable>["attributes"];
  listeners: ReturnType<typeof useSortable>["listeners"];
}) {
  const { t } = useTranslation();
  return (
    <button
      type="button"
      aria-label={t("catalog.actions.dragHandle")}
      className="cursor-grab text-muted-foreground"
      {...attributes}
      {...listeners}
    >
      <GripVertical className="size-4" aria-hidden />
    </button>
  );
}

function ThumbnailButton({
  isThumbnail,
  onClick,
}: {
  isThumbnail: boolean;
  onClick: () => void;
}) {
  const { t } = useTranslation();
  return (
    <Button variant="outline" size="sm" disabled={isThumbnail} onClick={onClick}>
      <Star className="mr-1 size-3" aria-hidden />
      {t("catalog.actions.setAsThumbnail")}
    </Button>
  );
}

function DeletePhotoButton({ onClick }: { onClick: () => void }) {
  const { t } = useTranslation();
  return (
    <Button
      variant="destructive"
      size="sm"
      onClick={onClick}
      aria-label={t("catalog.actions.deletePhoto")}
    >
      <Trash2 className="size-4" aria-hidden />
    </Button>
  );
}

function UploadZone({
  onFiles,
  inputRef,
}: {
  onFiles: (files: FileList | null) => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
}) {
  const [isDragging, setIsDragging] = useState(false);

  // The browser default for `drop` on a webpage is to navigate to the file —
  // so a missed `preventDefault` makes the photo open in the tab instead of
  // uploading. Stop the default on every step of the drag lifecycle.
  return (
    <div
      data-testid="photo-upload-zone"
      data-dragging={isDragging ? "true" : "false"}
      onDragOver={(e) => {
        e.preventDefault();
        if (!isDragging) setIsDragging(true);
      }}
      onDragEnter={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={(e) => {
        e.preventDefault();
        setIsDragging(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        onFiles(e.dataTransfer.files);
      }}
      className={cn(
        "rounded border-2 border-dashed p-3 text-center text-xs text-muted-foreground transition-colors",
        isDragging ? "border-accent bg-accent/10" : "border-border",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={(e) => onFiles(e.currentTarget.files)}
      />
      <button
        type="button"
        className="text-foreground underline"
        onClick={() => inputRef.current?.click()}
      >
        + Drop photos here, or click to browse
      </button>
    </div>
  );
}
