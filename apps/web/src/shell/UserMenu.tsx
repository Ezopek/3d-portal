import { useTranslation } from "react-i18next";

import { clearToken, readToken } from "@/lib/auth";
import { Button } from "@/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/ui/dropdown-menu";

export function UserMenu() {
  const { t } = useTranslation();
  const token = readToken();
  if (token === null) {
    return (
      <Button variant="outline" size="sm" render={<a href="/login" />}>
        {t("auth.login")}
      </Button>
    );
  }
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="outline" size="sm" />}>
        Admin
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem
          onClick={() => {
            clearToken();
            window.location.reload();
          }}
        >
          {t("auth.logout")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
