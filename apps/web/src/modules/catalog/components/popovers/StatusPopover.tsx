import type { ReactNode } from "react";

import type { ModelStatus } from "@/lib/api-types";
import { useUpdateModel } from "@/modules/catalog/hooks/mutations/useUpdateModel";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/ui/dropdown-menu";

const STATUSES: ModelStatus[] = ["not_printed", "printed", "in_progress", "broken"];

interface Props {
  modelId: string;
  current: ModelStatus;
  children: ReactNode;
}

export function StatusPopover({ modelId, current, children }: Props) {
  const update = useUpdateModel(modelId);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger nativeButton={false} render={<span />}>
        {children}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        {STATUSES.map((s) => (
          <DropdownMenuItem
            key={s}
            disabled={s === current || update.isPending}
            onClick={() => update.mutate({ status: s })}
          >
            {s.replace("_", " ")}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
