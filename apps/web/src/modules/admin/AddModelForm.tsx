// Initiative 13 Story 20.2 — extracted reusable form component for the
// admin "Add Model" flow. Originally lived inline in
// routes/admin/models/new.tsx; pulled out so AddModelModal (this story)
// and the existing route both consume the same form shape with no copy-paste.

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { api, ApiError } from "@/lib/api";
import type { ModelDetail } from "@/lib/api-types";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

const SOURCES = [
  "unknown",
  "own",
  "printables",
  "thingiverse",
  "thangs",
  "makerworld",
  "cults3d",
  "crealitycloud",
  "other",
] as const;

const STATUSES = ["not_printed", "printed", "in_progress", "broken"] as const;

interface FormState {
  name_en: string;
  name_pl: string;
  source: (typeof SOURCES)[number];
  status: (typeof STATUSES)[number];
  rating: string;
  description_pl: string;
  description_en: string;
}

const EMPTY_FORM: FormState = {
  name_en: "",
  name_pl: "",
  source: "unknown",
  status: "not_printed",
  rating: "",
  description_pl: "",
  description_en: "",
};

export interface AddModelFormProps {
  onSuccess: (model: ModelDetail) => void;
  onCancel: () => void;
  /** Optional compact mode — strips outer page-style padding so the form
   *  drops cleanly into a modal body. Default behaviour matches the
   *  /admin/models/new route's spacing. */
  compact?: boolean;
}

export function AddModelForm({ onSuccess, onCancel, compact = false }: AddModelFormProps) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async (): Promise<ModelDetail> => {
      const payload: Record<string, unknown> = {
        name_en: form.name_en.trim(),
        source: form.source,
        status: form.status,
      };
      if (form.name_pl.trim() !== "") payload.name_pl = form.name_pl.trim();
      if (form.rating.trim() !== "") {
        const r = Number(form.rating);
        if (!Number.isNaN(r) && r >= 1 && r <= 5) payload.rating = r;
      }

      const model = await api<ModelDetail>("/admin/models", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      // If a description was provided, create the description note in a
      // follow-up call. Errors here are surfaced but do NOT block model
      // creation — the model row is already persisted.
      const hasDesc =
        form.description_pl.trim() !== "" || form.description_en.trim() !== "";
      if (hasDesc) {
        try {
          await api(`/admin/models/${model.id}/notes`, {
            method: "POST",
            body: JSON.stringify({
              kind: "description",
              body: form.description_en.trim() || form.description_pl.trim(),
              body_pl: form.description_pl.trim() || null,
              body_en: form.description_en.trim() || null,
            }),
          });
        } catch {
          toast.error(t("admin.models.new.errors.description_create_failed"));
        }
      }
      return model;
    },
    onSuccess: (model) => {
      toast.success(t("admin.models.new.created"));
      void qc.invalidateQueries({ queryKey: ["sot", "models"] });
      onSuccess(model);
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        if (err.status === 409) setError(t("admin.models.new.errors.slug_conflict"));
        else if (err.status === 422) setError(t("admin.models.new.errors.validation"));
        else setError(t("admin.models.new.errors.generic"));
      } else {
        setError(t("admin.models.new.errors.generic"));
      }
    },
  });

  const canSubmit = form.name_en.trim().length > 0 && !mutation.isPending;

  return (
    <form
      className={compact ? "space-y-4" : "mx-auto max-w-3xl space-y-4 p-6"}
      onSubmit={(e) => {
        e.preventDefault();
        setError(null);
        mutation.mutate();
      }}
    >
      {!compact && (
        <header className="space-y-2 pb-2">
          <h1 className="text-xl font-semibold">{t("admin.models.new.title")}</h1>
          <p className="text-sm text-muted-foreground">
            {t("admin.models.new.description")}
          </p>
        </header>
      )}

      <fieldset className="space-y-3" disabled={mutation.isPending}>
        <label className="block space-y-1">
          <span className="text-sm font-medium">
            {t("admin.models.new.field.name_en")}{" "}
            <span className="text-destructive">*</span>
          </span>
          <Input
            value={form.name_en}
            onChange={(e) => setForm({ ...form, name_en: e.currentTarget.value })}
            required
            autoComplete="off"
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium">{t("admin.models.new.field.name_pl")}</span>
          <Input
            value={form.name_pl}
            onChange={(e) => setForm({ ...form, name_pl: e.currentTarget.value })}
            autoComplete="off"
          />
        </label>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="block space-y-1">
            <span className="text-sm font-medium">{t("admin.models.new.field.source")}</span>
            <select
              value={form.source}
              onChange={(e) =>
                setForm({ ...form, source: e.currentTarget.value as FormState["source"] })
              }
              className="block w-full rounded border border-border bg-background px-3 py-2 text-sm"
            >
              {SOURCES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>

          <label className="block space-y-1">
            <span className="text-sm font-medium">{t("admin.models.new.field.status")}</span>
            <select
              value={form.status}
              onChange={(e) =>
                setForm({ ...form, status: e.currentTarget.value as FormState["status"] })
              }
              className="block w-full rounded border border-border bg-background px-3 py-2 text-sm"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="block space-y-1">
          <span className="text-sm font-medium">{t("admin.models.new.field.rating")}</span>
          <Input
            type="number"
            min={1}
            max={5}
            step={0.5}
            value={form.rating}
            onChange={(e) => setForm({ ...form, rating: e.currentTarget.value })}
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium">{t("admin.models.new.field.description_en")}</span>
          <textarea
            value={form.description_en}
            onChange={(e) => setForm({ ...form, description_en: e.currentTarget.value })}
            rows={3}
            className="block w-full rounded border border-border bg-background px-3 py-2 text-sm"
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium">{t("admin.models.new.field.description_pl")}</span>
          <textarea
            value={form.description_pl}
            onChange={(e) => setForm({ ...form, description_pl: e.currentTarget.value })}
            rows={3}
            className="block w-full rounded border border-border bg-background px-3 py-2 text-sm"
          />
        </label>
      </fieldset>

      {error !== null && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      <div className="flex gap-2">
        <Button type="submit" disabled={!canSubmit}>
          {mutation.isPending
            ? t("admin.models.new.creating")
            : t("admin.models.new.submit")}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
      </div>

      {!compact && (
        <p className="text-xs text-muted-foreground">
          {t("admin.models.new.files_note")}
        </p>
      )}
    </form>
  );
}
