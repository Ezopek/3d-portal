import { Badge } from "portal-web";

export function Variants() {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Badge>Domyślny</Badge>
      <Badge variant="outline">PETG</Badge>
      <Badge variant="destructive">Błąd druku</Badge>
      <Badge variant="ghost">Szkic</Badge>
      <Badge variant="link">Szczegóły</Badge>
    </div>
  );
}

export function StatusTones() {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Badge
        variant="outline"
        className="border-success/40 bg-success/10 text-success"
      >
        Wydrukowano
      </Badge>
      <Badge
        variant="outline"
        className="border-warning/40 bg-warning/10 text-warning"
      >
        W trakcie
      </Badge>
      <Badge
        variant="outline"
        className="border-destructive/40 bg-destructive/10 text-destructive"
      >
        Uszkodzony
      </Badge>
    </div>
  );
}
