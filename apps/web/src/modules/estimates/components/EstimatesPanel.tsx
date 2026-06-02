import { useState } from "react";
import { useTranslation } from "react-i18next";

import { EstimateDisplay } from "@/modules/estimates/components/EstimateDisplay";
import { PrintIntentPresetSelector } from "@/modules/estimates/components/PrintIntentPresetSelector";
import { useEstimate } from "@/modules/estimates/hooks/useEstimate";
import {
  defaultPreset,
  type PrintIntentPresetInput,
} from "@/modules/estimates/lib/preset";

interface Props {
  /**
   * The content hash (64-hex) of the STL to estimate. Supplied by the mount surface — the
   * catalog↔STL ingestion that auto-derives this per part is OUT OF SCOPE (AC-9); 32.6
   * renders against a supplied/known hash.
   */
  stlHash: string;
  /**
   * The portal printer identity (a resolve input). The Init 20 MVP is single-printer, so the
   * mount surface supplies it rather than the operator selecting it — the selector emits only
   * material/tier/pin (AC-2).
   */
  printerRef: string;
}

/**
 * Story 32.6 — the self-contained estimates surface: the `PrintIntentPreset` selector wired
 * to the honest estimate display via `useEstimate`. Changing any selector field re-keys the
 * query (AC-2/AC-3), so the display always reflects the *current* preset's estimate.
 */
export function EstimatesPanel({ stlHash, printerRef }: Props) {
  const { t } = useTranslation();
  const [preset, setPreset] = useState<PrintIntentPresetInput>(defaultPreset);
  const query = useEstimate(stlHash, preset, printerRef);

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 p-4">
      <h1 className="text-lg font-semibold">{t("modules.estimates.title")}</h1>
      <PrintIntentPresetSelector value={preset} onChange={setPreset} />
      <EstimateDisplay
        isPending={query.isPending}
        isError={query.isError}
        data={query.data}
        onRetry={() => void query.refetch()}
      />
    </div>
  );
}
