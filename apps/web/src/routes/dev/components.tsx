import { createFileRoute } from "@tanstack/react-router";

import { Badge } from "@/ui/badge";
import { Button } from "@/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/ui/card";
import { ComingSoonStub } from "@/ui/custom/ComingSoonStub";
import { EmptyState } from "@/ui/custom/EmptyState";
import { Gallery } from "@/ui/custom/Gallery";
import { ModelCard } from "@/ui/custom/ModelCard";
import { SourceBadge } from "@/ui/custom/SourceBadge";
import { StatusBadge } from "@/ui/custom/StatusBadge";
import { Input } from "@/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/ui/tabs";

import type { ModelSummary } from "@/lib/api-types";

const FAKE_MODEL: ModelSummary = {
  id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  legacy_id: "001",
  slug: "dragon",
  name_en: "Dragon",
  name_pl: "Smok",
  category_id: "11111111-1111-1111-1111-111111111111",
  source: "printables",
  status: "printed",
  rating: 5,
  thumbnail_file_id: null,
  date_added: "2026-04-12",
  deleted_at: null,
  created_at: "2026-04-12T00:00:00Z",
  updated_at: "2026-04-12T00:00:00Z",
  tags: [
    { id: "tag-1", slug: "dragon", name_en: "Dragon", name_pl: "Smok" },
    { id: "tag-2", slug: "smok", name_en: "Smok", name_pl: null },
  ],
};

const FAKE_MODEL_2: ModelSummary = {
  ...FAKE_MODEL,
  id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  legacy_id: "002",
  slug: "vase",
  name_en: "Vase",
  name_pl: "Wazon",
  status: "not_printed",
  source: "unknown",
};

function DevComponents() {
  return (
    <div className="space-y-8 p-6">
      <Section title="Buttons">
        <div className="flex flex-wrap gap-2">
          <Button>Default</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="destructive">Destructive</Button>
          <Button size="sm">Small</Button>
          <Button size="icon" aria-label="icon">+</Button>
        </div>
      </Section>
      <Section title="Badges">
        <div className="flex flex-wrap gap-2">
          <Badge>Default</Badge>
          <Badge variant="outline">Outline</Badge>
          <Badge variant="secondary">Secondary</Badge>
          <StatusBadge status="printed" />
          <StatusBadge status="not_printed" />
          <StatusBadge status="in_progress" />
          <StatusBadge status="broken" />
          <SourceBadge source="printables" />
          <SourceBadge source="thangs" />
        </div>
      </Section>
      <Section title="Card">
        <Card>
          <CardHeader>
            <CardTitle>Title</CardTitle>
          </CardHeader>
          <CardContent>Body content goes here.</CardContent>
        </Card>
      </Section>
      <Section title="Input">
        <Input placeholder="Type here…" />
      </Section>
      <Section title="Tabs">
        <Tabs defaultValue="a">
          <TabsList>
            <TabsTrigger value="a">A</TabsTrigger>
            <TabsTrigger value="b">B</TabsTrigger>
          </TabsList>
          <TabsContent value="a">Content A</TabsContent>
          <TabsContent value="b">Content B</TabsContent>
        </Tabs>
      </Section>
      <Section title="ModelCard">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
          <ModelCard model={FAKE_MODEL} />
          <ModelCard model={FAKE_MODEL_2} />
        </div>
      </Section>
      <Section title="EmptyState">
        <EmptyState messageKey="catalog.empty" />
      </Section>
      <Section title="ComingSoonStub">
        <ComingSoonStub moduleKey="queue" />
      </Section>
      <Section title="Gallery">
        <Gallery images={[]} />
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h2>
      {children}
    </section>
  );
}

export const Route = createFileRoute("/dev/components")({ component: DevComponents });
