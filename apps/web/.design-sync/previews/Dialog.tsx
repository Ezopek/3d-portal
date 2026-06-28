import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "portal-web";

export function DestructiveConfirm() {
  return (
    <Dialog defaultOpen>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Usunąć model?</DialogTitle>
          <DialogDescription>
            Tej operacji nie można cofnąć. Model „Wspornik kątowy 30°"
            zostanie trwale usunięty z katalogu wraz ze zdjęciami.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline">Anuluj</Button>
          <Button variant="destructive">Usuń model</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
