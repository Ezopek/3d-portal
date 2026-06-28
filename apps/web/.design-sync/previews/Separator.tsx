import { Separator } from "portal-web";

export function Horizontal() {
  return (
    <div className="w-72">
      <div className="text-sm font-medium">Ustawienia druku</div>
      <div className="text-sm text-muted-foreground">
        Profil materiału i jakości
      </div>
      <Separator className="my-3" />
      <div className="text-sm text-muted-foreground">
        Wysokość warstwy 0,2 mm · wypełnienie 40%
      </div>
    </div>
  );
}

export function Vertical() {
  return (
    <div className="flex h-5 items-center gap-3 text-sm">
      <span>Katalog</span>
      <Separator orientation="vertical" />
      <span>Kolejka</span>
      <Separator orientation="vertical" />
      <span className="text-muted-foreground">Ustawienia</span>
    </div>
  );
}
