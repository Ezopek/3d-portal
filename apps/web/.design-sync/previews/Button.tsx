import { Plus, Trash2, Download } from "lucide-react";
import { Button } from "portal-web";

export function Variants() {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button>Zapisz</Button>
      <Button variant="outline">Edytuj</Button>
      <Button variant="destructive">Usuń</Button>
      <Button variant="ghost">Anuluj</Button>
      <Button variant="link">Więcej</Button>
    </div>
  );
}

export function Sizes() {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button size="xs">XS</Button>
      <Button size="sm">SM</Button>
      <Button size="default">Domyślny</Button>
      <Button size="lg">LG</Button>
    </div>
  );
}

export function WithIcons() {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button>
        <Plus />
        Dodaj model
      </Button>
      <Button variant="outline">
        <Download />
        Pobierz STL
      </Button>
      <Button variant="destructive" size="icon" aria-label="Usuń">
        <Trash2 />
      </Button>
      <Button disabled>Niedostępny</Button>
    </div>
  );
}
