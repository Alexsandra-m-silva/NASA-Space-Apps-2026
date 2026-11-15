export type TeamMember = {
  id: string;
  name: string;
  line: string;
  /** Public path under /public; null = placeholder avatar */
  photo: string | null;
  /** Initials for placeholder avatar */
  initials: string;
};

export const TEAM: TeamMember[] = [
  {
    id: "alexsandra",
    name: "Alexsandra Meneses",
    line: "Turns complex ops into scalable Power Platform systems",
    photo: "/team/alexsandra-meneses.svg",
    initials: "AM",
  },
  {
    id: "gabriela",
    name: "Gabriela Slovac",
    line: "Shapes Climate Sentinel’s product experience across different use cases",
    photo: "/team/gabriela-slovac.svg",
    initials: "GS",
  },
  {
    id: "jose",
    name: "José Fronza",
    line: "Grounds the platform in remote sensing, GIS, and territorial intelligence",
    photo: "/team/jose-fronza.svg",
    initials: "JF",
  },
  {
    id: "matheus",
    name: "Matheus P. Pedroso",
    line: "Builds the software and AI layer behind Climate Sentinel’s evidence",
    photo: "/team/matheus-pedroso.svg",
    initials: "MP",
  },
  {
    id: "yasmin",
    name: "Yasmin Bondan Nicolodi",
    line: "Contributes to connecting NISAR data to partners and action plans",
    photo: "/team/yasmin.svg",
    initials: "YN",
  },
];
