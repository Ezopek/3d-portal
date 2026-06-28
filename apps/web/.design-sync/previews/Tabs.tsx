import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "portal-web";

export function Default() {
  return (
    <Tabs defaultValue="opis" className="w-96">
      <TabsList>
        <TabsTrigger value="opis">Opis</TabsTrigger>
        <TabsTrigger value="pliki">Pliki</TabsTrigger>
        <TabsTrigger value="wydruki">Wydruki</TabsTrigger>
      </TabsList>
      <TabsContent value="opis" className="p-3 text-muted-foreground">
        Lekki wspornik konstrukcyjny do druku 3D. Zalecane wypełnienie 40%.
      </TabsContent>
      <TabsContent value="pliki" className="p-3 text-muted-foreground">
        model.stl · wspornik.3mf
      </TabsContent>
    </Tabs>
  );
}

export function LineVariant() {
  return (
    <Tabs defaultValue="wszystkie" className="w-96">
      <TabsList variant="line">
        <TabsTrigger value="wszystkie">Wszystkie</TabsTrigger>
        <TabsTrigger value="wydrukowane">Wydrukowane</TabsTrigger>
        <TabsTrigger value="w-trakcie">W trakcie</TabsTrigger>
      </TabsList>
      <TabsContent value="wszystkie" className="p-3 text-muted-foreground">
        128 modeli w katalogu.
      </TabsContent>
    </Tabs>
  );
}
