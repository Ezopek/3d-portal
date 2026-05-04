import { useTranslation } from "react-i18next";

import { clearToken } from "@/lib/auth";
import { useAuth } from "@/shell/AuthContext";
import { Button } from "@/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/ui/dropdown-menu";

export function UserMenu() {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
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
