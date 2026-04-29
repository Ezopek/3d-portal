import { Link, createFileRoute } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

const MODULES = ["catalog", "queue", "spools", "printer", "requests"] as const;

function Landing() {
  const { t } = useTranslation();
  return (
    <div className="grid gap-4 p-4 md:grid-cols-2 lg:grid-cols-3">
      {MODULES.map((m) => (
        <Link
          key={m}
          to={`/${m}`}
          className="rounded-md border border-border bg-card p-6 text-card-foreground hover:border-ring"
        >
          <h2 className="text-lg font-semibold">{t(`modules.${m}`)}</h2>
        </Link>
      ))}
    </div>
  );
}

export const Route = createFileRoute("/")({ component: Landing });
