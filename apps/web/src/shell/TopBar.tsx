import { LangToggle } from "./LangToggle";
import { ThemeToggle } from "./ThemeToggle";
import { UserMenu } from "./UserMenu";

export function TopBar() {
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-border bg-background/95 px-4 backdrop-blur">
      <div className="flex flex-1 items-center gap-3">
        {/* Module title + breadcrumb slot — Phase 8 will inject a portal here. */}
      </div>
      <ThemeToggle />
      <LangToggle />
      <UserMenu />
    </header>
  );
}
