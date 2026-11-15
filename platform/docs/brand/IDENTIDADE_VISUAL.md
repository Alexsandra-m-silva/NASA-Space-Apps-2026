# CLIMA — Terra e luz

Fonte: Design System NASA Space App Challenge (CLIMA / Desert Sentinel).

Arquivo de referência: [`color-palette.png`](./color-palette.png)

## Conceito

> A connected, regenerative future.  
> A natural base for the brand. Clarity and precision for the data.

Palavras-chave: partnership, connection, climate, future, community, regeneration, sustainability, carbon credits, desertification.

## 01 — Marca e interface

| Nome | Hex | Uso |
|---|---|---|
| Café | `#220F08` | Marca principal — confiança, permanência, sustentabilidade |
| Barro | `#642F07` | Ação / conexão com a terra e ação coletiva |
| Sol | `#FFEA7F` | Destaque — energia e regeneração |
| Ocre | `#A2510F` | Apoio — solo, matéria, calor |
| Mel | `#DAA849` | Luz e calor — usar com texto escuro |

### Neutros quentes

| Token | Hex |
|---|---|
| Canvas | `#FBF7EF` |
| Surface | `#FFFDF8` |
| Subtle | `#F3EBD9` |
| Border | `#DDD5BA` |
| Control Border | `#927C60` |
| Text Secondary | `#6B5545` |
| Text Primary | `#220F08` |

### Semânticos

| Status | Hex |
|---|---|
| Success | `#52633D` |
| Warning | `#B9500E` |
| Error | `#963B2F` |
| Information | `#435D6A` |

## 02 — Cores de dados

- **Categórica (A–E):** Cacau `#341C10` · Âmbar `#B67523` · Palha `#C4AE58` · Castanha `#471C09` · Ouro `#F3D867`
- **Sequencial:** `#FFEA7F` → `#DAA849` → `#B67523` → `#642F07` → `#341C10`
- **Divergente:** `#642F07` → `#DAA849` · `#F3EBD9` · `#C4AE58` → `#62602D`
- **Sem dados (N/D):** neutro claro + símbolo/padrão (acessibilidade)

## 03 — Comportamento

- Estrutura e ações: Café e Barro  
- Destaques: Sol  
- Apoio: Ocre · Mel  
- Hover: `#471C09` (castanha) · Focus: `#435D6A` (informação)

Contraste (WCAG): superfície/café 18.14:1 · superfície/barro 10.60:1 · café/sol 15.20:1

Tokens no código: `src/data/design-tokens.ts` · CSS: `src/app/globals.css`
