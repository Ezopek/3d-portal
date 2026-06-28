import {
  Badge,
  Button,
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "portal-web";

export function ModelSummary() {
  return (
    <Card className="w-72">
      <CardHeader>
        <CardTitle>Wspornik kątowy 30°</CardTitle>
        <CardDescription>Angle bracket 30°</CardDescription>
        <CardAction>
          <Badge variant="outline">PETG</Badge>
        </CardAction>
      </CardHeader>
      <CardContent className="text-muted-foreground">
        Lekki wspornik konstrukcyjny do druku 3D. Zalecane wypełnienie 40%,
        wysokość warstwy 0,2 mm.
      </CardContent>
      <CardFooter>
        <Button size="sm">Otwórz model</Button>
      </CardFooter>
    </Card>
  );
}

export function Compact() {
  return (
    <Card size="sm" className="w-64">
      <CardHeader>
        <CardTitle>Kompaktowa karta</CardTitle>
        <CardDescription>Wariant „sm" — gęstszy układ</CardDescription>
      </CardHeader>
      <CardContent className="text-muted-foreground">
        Mniejsze odstępy i typografia dla gęstych widoków listy.
      </CardContent>
    </Card>
  );
}
