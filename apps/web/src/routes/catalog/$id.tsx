import { createFileRoute } from "@tanstack/react-router";

import { CatalogDetail } from "@/modules/catalog/routes/CatalogDetail";

export const Route = createFileRoute("/catalog/$id")({ component: CatalogDetail });
