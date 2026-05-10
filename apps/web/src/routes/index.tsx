import { createFileRoute, redirect } from "@tanstack/react-router";

// V1 ships with one working module (catalog); the other module slots are
// "Coming soon" stubs. A landing grid linking to four stubs and one real
// module is a confusing first impression, so / hands off straight to the
// catalog. Replace with a proper landing once a second module ships.
export const Route = createFileRoute("/")({
  beforeLoad: () => {
    throw redirect({ to: "/catalog" });
  },
});
