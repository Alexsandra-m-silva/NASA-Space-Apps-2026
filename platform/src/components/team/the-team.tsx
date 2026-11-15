import Link from "next/link";
import { Button } from "@/components/ui/button";
import { TEAM } from "@/data/team";

const TOP = TEAM.slice(0, 3);
const BOTTOM = TEAM.slice(3);
const SITE_URL = "https://climate-sentinel.hefestotech.com.br";
const SITE_LABEL = "climate-sentinel.hefestotech.com.br";

function Avatar({
  name,
  photo,
  initials,
}: {
  name: string;
  photo: string | null;
  initials: string;
}) {
  if (photo) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={photo}
        alt={name}
        width={140}
        height={140}
        className="h-24 w-24 rounded-full object-cover object-center ring-2 ring-[#E5D4A8] sm:h-28 sm:w-28"
        draggable={false}
      />
    );
  }

  return (
    <div
      className="flex h-24 w-24 items-center justify-center rounded-full bg-[#642F07] text-base font-medium tracking-wide text-[#FBF7EF] ring-2 ring-[#E5D4A8] sm:h-28 sm:w-28 sm:text-lg"
      aria-label={`${name} — photo coming soon`}
      title="Photo coming soon"
    >
      {initials}
    </div>
  );
}

function Member({
  name,
  photo,
  initials,
  line,
}: {
  name: string;
  photo: string | null;
  initials: string;
  line: string;
}) {
  return (
    <li className="flex w-[9.5rem] flex-col items-center text-center sm:w-[12rem] md:w-[13.5rem]">
      <Avatar name={name} photo={photo} initials={initials} />
      <h2 className="mt-4 font-display text-base leading-snug text-olive sm:text-lg">
        {name}
      </h2>
      <p className="mt-1.5 text-xs leading-snug text-muted-foreground sm:text-sm">
        {line}
      </p>
    </li>
  );
}

export function TheTeam() {
  return (
    <div
      data-header-contrast="light"
      className="flex min-h-[calc(100vh-3.75rem)] flex-col justify-center px-4 py-10 sm:px-6 sm:py-12"
    >
      <div className="mx-auto w-full max-w-5xl">
        <header className="text-center">
          <p className="text-[0.7rem] uppercase tracking-[0.2em] text-signal">
            Climate Sentinel
          </p>
          <h1 className="mt-2 whitespace-nowrap font-display text-4xl text-olive sm:text-5xl">
            The&nbsp;Team
          </h1>
          <p className="mx-auto mt-3 max-w-xl text-sm text-muted-foreground">
            Design, geospatial intelligence, software, and delivery — one team
            for the NASA Space Apps Challenge.
          </p>
        </header>

        <div className="mt-10 flex flex-col items-center gap-8 sm:mt-12 sm:gap-10">
          <ul className="flex flex-wrap justify-center gap-x-6 gap-y-8 sm:gap-x-10 md:gap-x-12">
            {TOP.map((member) => (
              <Member
                key={member.id}
                name={member.name}
                photo={member.photo}
                initials={member.initials}
                line={member.line}
              />
            ))}
          </ul>
          <ul className="flex flex-wrap justify-center gap-x-6 gap-y-8 sm:gap-x-10 md:gap-x-12">
            {BOTTOM.map((member) => (
              <Member
                key={member.id}
                name={member.name}
                photo={member.photo}
                initials={member.initials}
                line={member.line}
              />
            ))}
          </ul>
        </div>

        <div className="mt-10 flex flex-col items-center gap-3 sm:mt-12">
          <Button
            asChild
            size="lg"
            variant="accent"
            className="border-transparent bg-[#FFEA7F] text-[#220F08] shadow hover:bg-[#F5DE6E]"
          >
            <Link href="/about#partners">Become a partner</Link>
          </Button>
          <a
            href={SITE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-muted-foreground transition-colors hover:text-olive"
          >
            {SITE_LABEL}
          </a>
        </div>
      </div>
    </div>
  );
}
