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
    photo: null, // photo file not uploaded yet (initials avatar)
    initials: "AM",
  },
  {
    id: "gabriela",
    name: "Gabriela Slovac",
    line: "Shapes Climate Sentinel’s product experience across different use cases",
    photo: null, // photo file not uploaded yet (initials avatar)
    initials: "GS",
  },
  {
    id: "jose",
    name: "José Fronza",
    line: "Grounds the platform in remote sensing, GIS, and territorial intelligence",
    photo: null, // photo file not uploaded yet (initials avatar)
    initials: "JF",
  },
  {
    id: "matheus",
    name: "Matheus P. Pedroso",
    line: "Builds the software and AI layer behind Climate Sentinel’s evidence",
    photo: null, // photo file not uploaded yet (initials avatar)
    initials: "MP",
  },
  {
    id: "yasmin",
    name: "Yasmin Bondan Nicolodi",
    line: "Contributes to connecting NISAR data to partners and action plans",
    photo: null, // photo file not uploaded yet (initials avatar)
    initials: "YN",
  },
];
