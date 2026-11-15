# Climate Sentinel

Explore desertification susceptibility evidence and subscribe to an email newsletter when the territory changes.

## Product surface

| Route | Purpose |
|---|---|
| `/` | Landing / about — audience, technology, objective |
| `/explore` | Map, actions, rankings, carbon financial impact |
| `/newsletter` | Email newsletter for media, government, and business |

Legacy paths (`/explorar`, `/entrar`, `/preferencias`, `/onboarding`, `/fluxos`, `/compare`, `/persona/…`) redirect into the surface above.

## Brand and logo

- Name: **Climate Sentinel**
- Dynamic header logo (stacked DESERT SENTINEL wordmark):
  - **Mel** on dark backgrounds
  - **Barro** on light backgrounds
- The header detects background contrast and cross-fades between variants
- Palette: **CLIMA / Terra e luz** (Café · Barro · Sol · Ocre · Mel) — already applied in tokens/CSS

## Exploration (`/explore`)

- **Above the fold:** desertification susceptibility map + evidence chat
- **Below the fold:** impact type beside what-to-do-now actions, then rankings
- Filters: analyzed territory · impact type · risk · sort
- Highlights: **Transition risks (SDG 13)** + **carbon credits if the area is restored**
- CTA carries pre-selected filters to `/newsletter`

## Newsletter (`/newsletter`)

- Tone for **media, government, and business** — newsletter, not a generic sign-up
- Work email, role profile, and monitoring scope
- Trigger criteria + filters aligned with exploration
- CTA: **Subscribe to the newsletter**

## Run locally

```bash
npm install
npm run dev
```

Opens at [http://localhost:3847](http://localhost:3847).

## Design system

Palette aligned with the Design System — NASA Space App Challenge (**CLIMA / Terra e luz**):

- Brand: **Café** `#220F08` · **Barro** `#642F07` · **Sol** `#FFEA7F` · **Ocre** `#A2510F` · **Mel** `#DAA849`
- Neutrals: Canvas `#FBF7EF` · Surface `#FFFDF8` · Subtle `#F3EBD9`
- Tokens in `src/data/design-tokens.ts` and CSS in `src/app/globals.css`
- Visual reference: [`docs/brand/color-palette.png`](docs/brand/color-palette.png) · [`docs/brand/IDENTIDADE_VISUAL.md`](docs/brand/IDENTIDADE_VISUAL.md)

## Notes

- Preferences use `localStorage` in this browser (no backend).
- Email alerts are modeled; real sending is out of scope for this cut.
