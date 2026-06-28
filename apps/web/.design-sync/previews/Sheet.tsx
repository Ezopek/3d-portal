import {
  Button,
  Input,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "portal-web";

export function FilterPanel() {
  return (
    <Sheet defaultOpen>
      <SheetContent side="right" className="w-80 p-4">
        <SheetHeader className="px-0">
          <SheetTitle>Filtry katalogu</SheetTitle>
          <SheetDescription>
            Zawęź listę modeli po materiale i statusie.
          </SheetDescription>
        </SheetHeader>
        <div className="flex flex-col gap-3 py-2">
          <label className="text-sm font-medium">Szukaj</label>
          <Input placeholder="np. wspornik" />
          <label className="text-sm font-medium">Materiał</label>
          <Input placeholder="PETG" />
        </div>
        <SheetFooter className="px-0">
          <Button variant="outline">Wyczyść</Button>
          <Button>Zastosuj</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
