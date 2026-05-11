import { useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "@/lib/api";
import { AgentsInfoDialog } from "@/shell/AgentsInfoDialog";
import { useAuth } from "@/shell/AuthContext";
import { Button } from "@/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/ui/dropdown-menu";

export function UserMenu() {
  const { t } = useTranslation();
  const { isAuthenticated, user, isAdmin } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [agentsDialogOpen, setAgentsDialogOpen] = useState(false);

  async function logout(endpoint: "/auth/logout" | "/auth/logout-all") {
    try {
      await api(endpoint, { method: "POST" });
    } catch {
      /* ignore network errors — session is gone either way */
    }
    await qc.invalidateQueries({ queryKey: ["auth", "me"] });
    await navigate({ to: "/login" });
  }

  if (!isAuthenticated) {
    return (
      <Button variant="outline" size="sm" render={<a href="/login" />}>
        {t("auth.login")}
      </Button>
    );
  }

  const label = user?.display_name ?? user?.email ?? t("auth.account_label_fallback");

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger render={<Button variant="outline" size="sm" />}>
          {label}
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem render={<a href="/settings/sessions" />}>
            {t("auth.sessions.menu_link")}
          </DropdownMenuItem>
          {isAdmin && (
            <DropdownMenuItem onClick={() => setAgentsDialogOpen(true)}>
              {t("agents.menu_label")}
            </DropdownMenuItem>
          )}
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => void logout("/auth/logout")}>
            {t("auth.logout")}
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => void logout("/auth/logout-all")}>
            {t("auth.logout_everywhere")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      {isAdmin && (
        <AgentsInfoDialog open={agentsDialogOpen} onOpenChange={setAgentsDialogOpen} />
      )}
    </>
  );
}
