import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "portal-web";

export function MaterialPicker() {
  return (
    <Select defaultValue="PETG" defaultOpen>
      <SelectTrigger className="w-52">
        <SelectValue placeholder="Wybierz materiał" />
      </SelectTrigger>
      <SelectContent alignItemWithTrigger={false}>
        <SelectGroup>
          <SelectLabel>Materiał</SelectLabel>
          <SelectItem value="PLA">PLA</SelectItem>
          <SelectItem value="PETG">PETG</SelectItem>
          <SelectItem value="ABS">ABS</SelectItem>
          <SelectItem value="TPU">TPU (elastyczny)</SelectItem>
        </SelectGroup>
      </SelectContent>
    </Select>
  );
}
