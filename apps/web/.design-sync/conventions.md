# 3D Portal Web UI — how to build with this design system

A React + **Tailwind CSS v4** component library (shadcn-style wrappers over Base UI
primitives) for the 3D Portal app. Style everything with **Tailwind utility classes** that
read the design tokens below — there is no CSS-in-JS and no per-component style props.

## Setup & wrapping

- Most components render standalone — **no provider needed**. Import and use them directly.
- **Dark mode**: add the `dark` class to an ancestor (`<div class="dark">…`). Every color
  token has a dark value; components adapt automatically.
- **Router**: a few components render a TanStack Router `<Link>` (e.g. `ModelCard`). Use them
  inside your app's `RouterProvider` as usual.
- **Font**: the base font is **Inter** (`--font-sans`), applied globally on `html`.

## Styling idiom — Tailwind utilities over CSS-variable tokens

Compose layout with standard Tailwind utilities and color with the **semantic token classes**
below (each maps to a `--color-*` CSS variable, so it is theme- and dark-mode-aware). Prefer
these over raw colors like `bg-blue-500`.

| Surface / text | Class |
|---|---|
| Page background / text | `bg-background` / `text-foreground` |
| Card surface | `bg-card` / `text-card-foreground` |
| Popover/menu surface | `bg-popover` / `text-popover-foreground` |
| Muted fill / muted text | `bg-muted` / `text-muted-foreground` |
| Primary (brand action) | `bg-primary` / `text-primary-foreground` |
| Accent (subtle hover) | `bg-accent` / `text-accent-foreground` |
| Border / input border | `border-border` / `border-input` |
| Focus ring | `ring-ring` (with `focus-visible:ring-3`) |
| Overlay scrim | `bg-overlay/30` |

Status colors (use the `/NN` opacity modifier for soft fills): `text-success bg-success/10
border-success/40`, and the same pattern for `warning` and `destructive`.

Radii: `rounded-sm|md|lg` (`--radius-sm|md|lg`). Spacing/typography: standard Tailwind scale.

**Variants** — `Button` and `Badge` take a `variant` prop: `default`, `secondary`, `outline`,
`destructive`, `ghost`, `link`. `secondary` maps to the `--color-secondary` /
`--color-secondary-foreground` tokens (a muted neutral fill, with dark-mode values), so
`bg-secondary text-secondary-foreground` renders accessibly in both themes. `Button` also takes
`size`: `xs | sm | default | lg | icon | icon-sm | icon-lg`.

## Where the truth lives

- Tokens + dark-mode values: **`_ds/3d-portal-web-ui/styles.css`** and its `@import`s
  (the `@theme` / `.dark` blocks define every `--color-*`, `--radius-*`, `--font-*`).
- Each component ships a `<Name>.d.ts` (its prop contract) and `<Name>.prompt.md` (usage) —
  read those before composing a component.

## Idiomatic example

```tsx
import { Card, CardHeader, CardTitle, CardContent, CardFooter, Badge, Button } from "<lib>";

function ModelTile() {
  return (
    <Card className="w-72">
      <CardHeader>
        <CardTitle>Wspornik kątowy 30°</CardTitle>
        <Badge variant="outline">PETG</Badge>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        Lekki wspornik konstrukcyjny do druku 3D.
      </CardContent>
      <CardFooter>
        <Button size="sm">Otwórz model</Button>
      </CardFooter>
    </Card>
  );
}
```

The library is built for a Polish-language product — prefer Polish copy in examples.
