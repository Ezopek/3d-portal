import { ConfirmDialog } from "portal-web";

export function DeleteProfile() {
  return (
    <ConfirmDialog
      open
      onOpenChange={() => {}}
      title="Usunąć profil druku?"
      description={'Profil „Creality K1 Max · PETG" zostanie usunięty. Powiązane wyceny zachowają swoje wartości.'}
      confirmLabel="Usuń profil"
      cancelLabel="Anuluj"
      destructive
      onConfirm={() => {}}
    />
  );
}
