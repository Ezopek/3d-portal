import { Info } from "lucide-react";
import {
  Button,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "portal-web";

export function Hint() {
  return (
    <TooltipProvider>
      <Tooltip defaultOpen>
        <TooltipTrigger
          render={<Button variant="outline" size="icon" aria-label="Pomoc" />}
        >
          <Info />
        </TooltipTrigger>
        <TooltipContent side="bottom">
          Wysokość warstwy w milimetrach
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
