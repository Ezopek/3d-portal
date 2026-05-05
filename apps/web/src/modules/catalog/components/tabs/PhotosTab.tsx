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
import { useRef, useState } from "react";

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
    return <p className="p-4 text-sm text-muted-foreground">…</p>;
  }
  if (photos.length === 0 && !upload.isPending) {
    return (
      <div className="space-y-3 p-3">
        <p className="text-sm text-muted-foreground">no photos</p>
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
            if (confirm(`Delete ${selected.original_name}?`)) {
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
      <button
        type="button"
        aria-label="drag handle"
        className="cursor-grab text-muted-foreground"
        {...attributes}
        {...listeners}
      >
        ⋮⋮
      </button>
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
          <Button variant="outline" size="sm" disabled={isThumbnail} onClick={onSetThumbnail}>
            ★ Set as thumbnail
          </Button>
          <Button variant="destructive" size="sm" onClick={onDelete}>
            🗑
          </Button>
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

function UploadZone({
  onFiles,
  inputRef,
}: {
  onFiles: (files: FileList | null) => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
}) {
  return (
    <div className="rounded border-2 border-dashed border-border p-3 text-center text-xs text-muted-foreground">
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
