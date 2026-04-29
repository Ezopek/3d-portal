import { createFileRoute } from "@tanstack/react-router";

import { CatalogList } from "@/modules/catalog/routes/CatalogList";

export const Route = createFileRoute("/catalog/")({ component: CatalogList });
