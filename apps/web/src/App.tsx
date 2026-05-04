import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, createRouter } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { Toaster } from "sonner";

import { queryClient } from "@/lib/queryClient";
import { AuthProvider } from "@/shell/AuthContext";
import { LangProvider } from "@/shell/LangProvider";
import { ThemeProvider } from "@/shell/ThemeProvider";

import { Sentry } from "./instrument";
import { routeTree } from "./routeTree.gen";

const router = createRouter({ routeTree, scrollRestoration: true });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <LangProvider>
          <ThemeProvider>
            <Toaster position="bottom-right" richColors />
            <Sentry.ErrorBoundary fallback={<ErrorFallback />}>
              <RouterProvider router={router} />
            </Sentry.ErrorBoundary>
          </ThemeProvider>
        </LangProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

function ErrorFallback() {
  const { t } = useTranslation();
  return (
    <div className="grid min-h-screen place-items-center bg-background p-6 text-foreground">
      <div className="space-y-4 text-center">
        <h1 className="text-xl font-semibold">{t("errors.boundary_title")}</h1>
        <button
          type="button"
          onClick={() => location.reload()}
          className="rounded-md bg-primary px-4 py-2 text-primary-foreground"
        >
          {t("errors.boundary_reload")}
        </button>
      </div>
    </div>
  );
}
