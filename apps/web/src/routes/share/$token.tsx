import { createFileRoute } from "@tanstack/react-router";

import { ShareView } from "@/modules/catalog/routes/ShareView";

export const Route = createFileRoute("/share/$token")({ component: ShareView });
