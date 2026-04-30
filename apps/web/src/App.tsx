import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, createRouter } from "@tanstack/react-router";

import { queryClient } from "@/lib/queryClient";
import { LangProvider } from "@/shell/LangProvider";
import { ThemeProvider } from "@/shell/ThemeProvider";

import { Sentry } from "./instrument";
import { routeTree } from "./routeTree.gen";

const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export function App() {
  return (
    <Sentry.ErrorBoundary fallback={<div className="p-4 text-destructive">Something went wrong</div>}>
      <QueryClientProvider client={queryClient}>
        <LangProvider>
          <ThemeProvider>
            <RouterProvider router={router} />
          </ThemeProvider>
        </LangProvider>
      </QueryClientProvider>
    </Sentry.ErrorBoundary>
  );
}
