import { TEAM } from "@/data/team";

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
        width={160}
        height={160}
        className="h-28 w-28 rounded-full object-cover object-center ring-2 ring-[#E5D4A8] sm:h-32 sm:w-32"
        draggable={false}
      />
    );
  }

  return (
    <div
      className="flex h-28 w-28 items-center justify-center rounded-full bg-[#341C10] text-lg font-medium tracking-wide text-[#FBF7EF] ring-2 ring-[#E5D4A8]/60 sm:h-32 sm:w-32 sm:text-xl"
      aria-label={`${name} — photo coming soon`}
      title="Photo coming soon"
    >
      {initials}
    </div>
  );
}

export function AboutTeam() {
  return (
    <section
      id="team"
      data-header-contrast="dark"
      className="scroll-mt-24 border-y border-[#341C10] bg-[#642F07] px-4 py-16 sm:px-6 sm:py-20"
    >
      <div className="mx-auto max-w-6xl">
        <p className="text-[0.7rem] uppercase tracking-[0.2em] text-[#FFEA7F]">
          Team
        </p>
        <h2 className="mt-2 font-display text-3xl text-[#FBF7EF] sm:text-4xl">
          Who builds Climate Sentinel
        </h2>
        <p className="mt-3 max-w-2xl text-sm text-[#F3EBD9]">
          Design, geospatial intelligence, software, and delivery — one team for
          the NASA Space Apps Challenge.
        </p>

        <ul className="mt-12 grid gap-10 sm:grid-cols-2 lg:grid-cols-3">
          {TEAM.map((member) => (
            <li key={member.id} className="flex flex-col items-start">
              <Avatar
                name={member.name}
                photo={member.photo}
                initials={member.initials}
              />
              <h3 className="mt-5 font-display text-xl text-[#FBF7EF]">
                {member.name}
              </h3>
              <p className="mt-1.5 text-sm leading-snug text-[#DDD5BA]">
                {member.line}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
