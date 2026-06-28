// Bundle-side preview providers. Shipped INTO the DS bundle via cfg.extraEntries
// so it shares the bundle's @tanstack/react-router instance — that shared
// context identity is what lets a component's internal <Link> resolve when an
// authored preview wraps it in <DsProviders>. (A provider imported fresh in a
// preview .tsx would be a different module instance and the context would not
// match — see .design-sync/NOTES.md.)
import {
  createMemoryHistory,
  createRootRoute,
  createRouter,
  RouterContextProvider,
} from "@tanstack/react-router";
import type { ReactNode } from "react";

const rootRoute = createRootRoute();
const router = createRouter({
  routeTree: rootRoute,
  history: createMemoryHistory({ initialEntries: ["/"] }),
});

/** Wrap a preview in router context so components using <Link> render. */
export function DsProviders({ children }: { children?: ReactNode }) {
  return (
    <RouterContextProvider router={router}>{children}</RouterContextProvider>
  );
}
