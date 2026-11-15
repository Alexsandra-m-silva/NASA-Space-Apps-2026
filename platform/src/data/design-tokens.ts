/**
 * Design System — NASA Space App Challenge
 * CLIMA / Terra e luz — “A connected, regenerative future.”
 * Source: Color palette.png (uploaded Design System zip)
 */
export const ds = {
  brand: {
    /** Confidence, permanence, sustainability */
    cafe: "#220F08",
    /** Earth connection, collective action */
    barro: "#642F07",
    /** Energy and regeneration — accent */
    sol: "#FFEA7F",
    /** Soil, matter, heat — support */
    ocre: "#A2510F",
    /** Light and warmth — use with dark text */
    mel: "#DAA849",
    /** Legacy aliases → new Terra e luz tokens */
    floresta: "#220F08",
    conexao: "#642F07",
    broto: "#FFEA7F",
    terra: "#A2510F",
    /** Warm canvas / light on dark */
    areia: "#FBF7EF",
  },
  neutrals: {
    canvas: "#FBF7EF",
    surface: "#FFFDF8",
    subtle: "#F3EBD9",
    border: "#DDD5BA",
    controlBorder: "#927C60",
    textSecondary: "#6B5545",
    text: "#220F08",
  },
  semantic: {
    success: "#52633D",
    warning: "#B9500E",
    error: "#963B2F",
    info: "#435D6A",
  },
  categorical: {
    /** Cacau */
    A: "#341C10",
    /** Âmbar */
    B: "#B67523",
    /** Palha */
    C: "#C4AE58",
    /** Castanha */
    D: "#471C09",
    /** Ouro */
    E: "#F3D867",
  },
  /** Volume / magnitude — light → dark (sol → cacau) */
  sequential: {
    1: "#FFEA7F",
    2: "#DAA849",
    3: "#B67523",
    4: "#642F07",
    5: "#341C10",
  },
  /** Desvio de referência — barro/mel ↔ neutro ↔ palha/olive */
  divergent: {
    low: "#642F07",
    lowMid: "#DAA849",
    mid: "#F3EBD9",
    highMid: "#C4AE58",
    high: "#62602D",
  },
  /** Hover / foco de interface */
  interaction: {
    hover: "#471C09",
    focus: "#435D6A",
  },
} as const;
