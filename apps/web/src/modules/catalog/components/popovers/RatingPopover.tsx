import type { ReactNode } from "react";

import { useUpdateModel } from "@/modules/catalog/hooks/mutations/useUpdateModel";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/ui/dropdown-menu";

interface Props {
  modelId: string;
  current: number | null;
  children: ReactNode;
}

export function RatingPopover({ modelId, current, children }: Props) {
  const update = useUpdateModel(modelId);
  const options: (number | null)[] = [null, 1, 2, 3, 4, 5];
  return (
    <DropdownMenu>
      <DropdownMenuTrigger nativeButton={false} render={<span />}>
        {children}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        {options.map((value) => (
          <DropdownMenuItem
            key={String(value)}
            disabled={value === current || update.isPending}
            onClick={() => update.mutate({ rating: value })}
          >
            {value === null ? "Clear" : "★".repeat(value)}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
