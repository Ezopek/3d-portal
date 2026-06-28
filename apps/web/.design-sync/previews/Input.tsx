import { Input } from "portal-web";

export function WithLabel() {
  return (
    <div className="flex w-72 flex-col gap-1.5">
      <label className="text-sm font-medium" htmlFor="model-name">
        Nazwa modelu
      </label>
      <Input id="model-name" placeholder="np. Wspornik kątowy 30°" />
    </div>
  );
}

export function States() {
  return (
    <div className="flex w-72 flex-col gap-3">
      <Input placeholder="Domyślny" defaultValue="PETG 1,75 mm" />
      <Input placeholder="Wyłączony" disabled defaultValue="Pole zablokowane" />
      <Input placeholder="Błąd walidacji" aria-invalid defaultValue="—" />
    </div>
  );
}
