"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type * as Leaflet from "leaflet";
import "leaflet/dist/leaflet.css";
import { ds } from "@/data/design-tokens";
import { RISK_LABELS, type RiskLevel, type Territory } from "@/data/explore/types";
import { cn } from "@/lib/utils";

/**
 * First fold, full width: everything the old model map (modelo.html) showed,
 * now inside the platform. Map of the 18 analysed municipalities (by risk) with
 * the model layers, the model KPIs, the per-municipality diagnosis (index
 * contributions, detector SHAP, MODIS × NISAR visual comparison) and the global
 * SHAP explanation. All results are precomputed: static GeoJSON in /public/geo
 * and the FastAPI (/api) published by the worker.
 */

const API = "/api";

// ---------- API types (subset of what /api returns) ----------
type ShapItem = { rotulo: string; efeito: number; familia?: string };
type FocusProps = {
  municipio: string;
  uf: string;
  modis?: { pct_degradado?: number; pct_melhora?: number; pct_estavel?: number };
  nisar?: { AUC?: number; "sensibilidade_%"?: number; "especificidade_%"?: number };
  clima?: {
    temp_c_tend_decada?: number;
    temp_c_p?: number;
    chuva_media_1991_2007?: number;
    chuva_media_2008_2024?: number;
    aridez_1991_2007?: number;
    aridez_2008_2024?: number;
  };
  suscetibilidade?: { indice_medio?: number; pct_alta?: number; pct_muito_alta?: number };
  contribuicoes_suscetibilidade?: Record<string, number>;
  shap_detector?: { principais?: ShapItem[]; pontos?: number };
};
type Meta = {
  fontes: string[];
  metricas: Record<string, number>;
  publicado_em: string;
};
type ShapGlobal = {
  importancia_familia: Record<string, number>;
  participacao_nisar_pct: number;
};
type CompareStats = {
  south: number;
  west: number;
  north: number;
  east: number;
  modis_years: number[];
  nisar_dates: string[];
  orbit: string;
  modis_falling_pct: number;
  nisar_falling_pct: number;
};
type ClassCounts = {
  modis_only: number;
  nisar_only: number;
  both: number;
  observed_without_decline: number;
};

// ---------- helpers ----------
const fmt = (v: number | null | undefined, d = 1) =>
  v == null || Number.isNaN(v)
    ? "—"
    : Number(v).toLocaleString("en-US", {
        maximumFractionDigits: d,
        minimumFractionDigits: d,
      });

const norm = (s: string) =>
  s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
const slugify = (s: string) => norm(s).replace(/\s+/g, "-");

async function getJson<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json() as Promise<T>;
}

function riskColor(risk: RiskLevel | undefined): string {
  if (risk === "critico") return ds.divergent.low;
  if (risk === "alto") return ds.brand.terra;
  if (risk === "moderado") return ds.divergent.lowMid;
  return ds.neutrals.border;
}

const HEX: Record<string, string> = {
  alta: "#d9772f",
  muito_alta: "#b0301f",
  degradado: "#b0301f",
  melhora: "#6f9b6a",
  controle_estavel: "#d9b45a",
};
const CLASS_EN: Record<string, string> = {
  baixa: "Low",
  media: "Medium",
  alta: "High",
  muito_alta: "Very high",
  degradado: "Degrading",
  melhora: "Improving",
  controle_estavel: "Stable control",
};
const FAM_EN: Record<string, string> = {
  "NISAR (radar 2026)": "NISAR (2026 radar)",
  "Clima (CHIRPS/ERA5)": "Climate (CHIRPS/ERA5)",
  "Histórico 2001–2014 (MODIS/MapBiomas)": "2001–2014 record (MODIS/MapBiomas)",
};
const CONTRIB_EN: Record<string, string> = {
  aquecimento: "Warming 1991–2024",
  aridez: "Aridity",
  vegetacao: "Vegetation loss (MODIS)",
  pressao_uso: "Land-use pressure (MapBiomas)",
  solo_arenoso: "Sandy soil",
};
const nisarColor = (p: number) =>
  p >= 0.6 ? "#b0301f" : p >= 0.4 ? "#d9772f" : p >= 0.25 ? "#d9b45a" : "#6f9b6a";

type LayerId = "suscetibilidade" | "degradacao" | "nisar";
const LAYERS: { id: LayerId; label: string; legend: [string, string][] }[] = [
  {
    id: "suscetibilidade",
    label: "High / very high susceptibility",
    legend: [
      ["High", HEX.alta],
      ["Very high", HEX.muito_alta],
    ],
  },
  {
    id: "degradacao",
    label: "MODIS degradation 2001–2024",
    legend: [
      ["Degrading", HEX.degradado],
      ["Improving", HEX.melhora],
      ["Stable control", HEX.controle_estavel],
    ],
  },
  {
    id: "nisar",
    label: "NISAR probability of degradation",
    legend: [
      ["≥ 60%", "#b0301f"],
      ["40–60%", "#d9772f"],
      ["25–40%", "#d9b45a"],
      ["< 25%", "#6f9b6a"],
    ],
  },
];

// ---------- small UI pieces ----------
function Kpi({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-md border border-border bg-background/60 px-2 py-2 sm:px-3">
      <p className="whitespace-nowrap font-display text-[0.95rem] leading-tight text-foreground sm:text-lg">{value}</p>
      <p className="mt-0.5 text-[0.62rem] leading-snug sm:text-[0.68rem] text-muted-foreground">{label}</p>
    </div>
  );
}

function Bars({
  items,
  max,
  digits = 2,
}: {
  items: [string, number][];
  max: number;
  digits?: number;
}) {
  return (
    <ul className="space-y-1">
      {items.map(([label, v]) => (
        <li
          key={label}
          className="grid grid-cols-[minmax(0,10rem)_1fr_3rem] items-center gap-2 text-[0.72rem]"
        >
          <span className="truncate text-muted-foreground" title={label}>
            {label}
          </span>
          <span className="h-2 rounded-full bg-secondary">
            <span
              className="block h-2 rounded-full"
              style={{
                width: `${Math.min(100, (Math.abs(v) / (max || 1)) * 100)}%`,
                background: v < 0 ? "#6f9b6a" : ds.brand.terra,
              }}
            />
          </span>
          <span className="text-right tabular-nums text-foreground">{fmt(v, digits)}</span>
        </li>
      ))}
    </ul>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <tr className="border-b border-border/60 last:border-0">
      <td className="py-1 pr-2 text-muted-foreground">{k}</td>
      <td className="whitespace-nowrap py-1 pl-2 text-right tabular-nums text-foreground">{v}</td>
    </tr>
  );
}

function H3({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="mb-1.5 mt-4 text-[0.7rem] font-semibold uppercase tracking-[0.12em] text-signal first:mt-0">
      {children}
    </h3>
  );
}

// ---------- main component ----------
export function ExploreMap({
  municipalities,
  selectedId,
  onSelect,
  onClear,
}: {
  municipalities: Territory[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onClear: () => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Leaflet.Map | null>(null);
  const LRef = useRef<typeof Leaflet | null>(null);
  const munLayerRef = useRef<Leaflet.GeoJSON | null>(null);
  const layerCache = useRef<Partial<Record<LayerId, Leaflet.GeoJSON>>>({});
  const cmpOverlayRef = useRef<Leaflet.ImageOverlay | null>(null);
  const cmpBoxRef = useRef<Leaflet.Rectangle | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  const [mapReady, setMapReady] = useState(false);
  const [layersOn, setLayersOn] = useState<Record<LayerId, boolean>>({
    suscetibilidade: true,
    degradacao: false,
    nisar: false,
  });
  const [meta, setMeta] = useState<Meta | null>(null);
  const [shapGlobal, setShapGlobal] = useState<ShapGlobal | null>(null);
  const [focus, setFocus] = useState<Map<string, FocusProps>>(new Map());
  const [apiError, setApiError] = useState<string | null>(null);

  const [cmpStats, setCmpStats] = useState<CompareStats | null>(null);
  const [cmpCounts, setCmpCounts] = useState<ClassCounts | null>(null);
  const [cmpState, setCmpState] = useState<"idle" | "loading" | "none" | "ok">("idle");
  const [cmpStep, setCmpStep] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);

  const byId = useMemo(
    () => new Map(municipalities.map((t) => [t.id, t])),
    [municipalities]
  );
  const byIdRef = useRef(byId);
  byIdRef.current = byId;

  const selected = selectedId ? byId.get(selectedId) ?? null : null;
  const focusData = selected ? focus.get(norm(selected.name)) ?? null : null;
  const focusNames = useMemo(
    () => municipalities.filter((t) => focus.has(norm(t.name))),
    [municipalities, focus]
  );

  // ---- model data from the API ----
  useEffect(() => {
    Promise.all([
      getJson<Meta>(`${API}/meta`),
      getJson<ShapGlobal>(`${API}/shap/detector`),
      getJson<{ features: { properties: FocusProps }[] }>(`${API}/municipios`),
    ])
      .then(([m, s, muns]) => {
        setMeta(m);
        setShapGlobal(s);
        setFocus(new Map(muns.features.map((f) => [norm(f.properties.municipio), f.properties])));
      })
      .catch((e: Error) => setApiError(e.message));
  }, []);

  // ---- map + 18 municipalities ----
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const L = (await import("leaflet")).default;
      if (cancelled || !containerRef.current || mapRef.current) return;
      LRef.current = L;
      const map = L.map(containerRef.current, {
        zoomControl: false,
        scrollWheelZoom: false,
      }).setView([-8.2, -38.6], 6);
      L.control.zoom({ position: "topright" }).addTo(map);
      // Comparison images above the vector layers (overlayPane = 400)
      map.createPane("cmp").style.zIndex = "450";
      L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        {
          maxZoom: 18,
          attribution: "Esri, Maxar · IBGE · MODIS · NISAR · MapBiomas · CHIRPS · ERA5-Land",
        }
      ).addTo(map);
      mapRef.current = map;
      try {
        const gj = await getJson<GeoJSON.FeatureCollection>("/geo/municipios-analisados.geojson");
        if (cancelled) return;
        const layer = L.geoJSON(gj, {
          onEachFeature: (f, l) => {
            const p = f.properties as { id: string; name: string; uf: string };
            const t = byIdRef.current.get(p.id);
            l.bindTooltip(
              `${p.name}/${p.uf}${t ? ` · ${RISK_LABELS[t.risk]} risk · ${fmt(t.tendenciaPp)}% degrading` : ""}`,
              { sticky: true }
            );
            l.on("click", () => onSelectRef.current(p.id));
          },
        }).addTo(map);
        munLayerRef.current = layer;
        map.fitBounds(layer.getBounds(), { padding: [16, 16] });
      } catch {
        /* municipality limits missing: map still shows layers */
      }
      setMapReady(true);
    })();
    return () => {
      cancelled = true;
      mapRef.current?.remove();
      mapRef.current = null;
      munLayerRef.current = null;
      layerCache.current = {};
      cmpOverlayRef.current = null;
      cmpBoxRef.current = null;
    };
  }, []);

  // ---- style municipalities (risk + selection) ----
  useEffect(() => {
    const layer = munLayerRef.current;
    if (!mapReady || !layer) return;
    layer.eachLayer((l) => {
      const path = l as Leaflet.Path & { feature?: GeoJSON.Feature };
      const id = (path.feature?.properties as { id?: string } | undefined)?.id;
      const t = id ? byId.get(id) : undefined;
      const active = id === selectedId;
      path.setStyle({
        color: active ? "#fff4d6" : riskColor(t?.risk),
        weight: active ? 3.5 : 2.2,
        fillColor: riskColor(t?.risk),
        fillOpacity: active ? 0.12 : 0.06,
      });
      if (active) path.bringToFront();
    });
  }, [mapReady, selectedId, byId]);

  // ---- zoom: selected municipality, or all of them when cleared ----
  useEffect(() => {
    const map = mapRef.current;
    const layer = munLayerRef.current;
    if (!mapReady || !map || !layer) return;
    if (!selectedId) {
      map.fitBounds(layer.getBounds(), { padding: [16, 16] });
      return;
    }
    layer.eachLayer((l) => {
      const path = l as Leaflet.Polygon & { feature?: GeoJSON.Feature };
      if ((path.feature?.properties as { id?: string } | undefined)?.id === selectedId)
        map.fitBounds(path.getBounds(), { padding: [24, 24], maxZoom: 11 });
    });
  }, [mapReady, selectedId]);

  // ---- model layers ----
  const loadLayer = useCallback(async (id: LayerId) => {
    const L = LRef.current;
    if (!L) return null;
    if (layerCache.current[id]) return layerCache.current[id]!;
    let layer: Leaflet.GeoJSON;
    if (id === "nisar") {
      const gj = await getJson<GeoJSON.FeatureCollection>(`${API}/camadas/pontos_nisar`);
      layer = L.geoJSON(gj, {
        pointToLayer: (f, ll) => {
          const p = Number(f.properties?.prob_degradacao_nisar ?? 0);
          return L.circleMarker(ll, {
            radius: 3,
            weight: 0,
            fillOpacity: 0.85,
            fillColor: nisarColor(p),
          }).bindTooltip(`NISAR: ${fmt(100 * p, 0)}% probability of degradation`);
        },
      });
    } else {
      const url =
        id === "degradacao"
          ? "/geo/degradacao-modis.geojson"
          : `${API}/camadas/suscetibilidade`;
      const gj = await getJson<GeoJSON.FeatureCollection>(url);
      layer = L.geoJSON(gj, {
        style: (f) => {
          const k = f?.properties?.suscetibilidade ?? f?.properties?.classe;
          const c = HEX[k] ?? "#999";
          return { color: c, weight: 0.4, fillColor: c, fillOpacity: 0.5 };
        },
        onEachFeature: (f, l) => {
          const k = f.properties?.suscetibilidade ?? f.properties?.classe;
          l.bindTooltip(
            `${CLASS_EN[k] ?? k} · ${Number(f.properties?.area_ha ?? 0).toLocaleString("en-US", { maximumFractionDigits: 0 })} ha`
          );
        },
      });
    }
    layerCache.current[id] = layer;
    return layer;
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    let cancelled = false;
    (async () => {
      for (const { id } of LAYERS) {
        const cached = layerCache.current[id];
        if (!layersOn[id]) {
          if (cached && map.hasLayer(cached)) map.removeLayer(cached);
          continue;
        }
        try {
          const layer = await loadLayer(id);
          if (cancelled || !layer) return;
          if (!map.hasLayer(layer)) layer.addTo(map);
        } catch {
          setApiError(`layer ${id} unavailable`);
        }
      }
      munLayerRef.current?.bringToFront();
    })();
    return () => {
      cancelled = true;
    };
  }, [mapReady, layersOn, loadLayer]);

  // ---- MODIS × NISAR visual comparison (team assets in /municipios/<slug>/) ----
  useEffect(() => {
    const map = mapRef.current;
    if (cmpBoxRef.current && map) map.removeLayer(cmpBoxRef.current);
    if (cmpOverlayRef.current && map) map.removeLayer(cmpOverlayRef.current);
    cmpBoxRef.current = null;
    cmpOverlayRef.current = null;
    setCmpStats(null);
    setCmpCounts(null);
    setCmpStep(null);
    setPlaying(false);
    if (!selected || !mapReady || !map) {
      setCmpState("idle");
      return;
    }
    const slug = slugify(selected.name);
    let cancelled = false;
    setCmpState("loading");
    (async () => {
      try {
        const stats = await getJson<CompareStats>(`/municipios/${slug}/stats.json?v=1`);
        if (cancelled) return;
        let counts: ClassCounts | null = null;
        try {
          const man = await getJson<{ places?: { slug: string; class_counts?: ClassCounts }[] }>(
            "/products/manifest.json"
          );
          counts = man.places?.find((p) => p.slug === slug)?.class_counts ?? null;
        } catch {
          /* optional */
        }
        if (cancelled) return;
        const L = LRef.current!;
        cmpBoxRef.current = L.rectangle(
          [
            [stats.south, stats.west],
            [stats.north, stats.east],
          ],
          { color: "#fff4d6", weight: 2, fill: false, dashArray: "4 4" }
        )
          .bindTooltip("MODIS × NISAR visual-comparison box")
          .addTo(map);
        map.fitBounds(cmpBoxRef.current.getBounds(), { padding: [40, 40], maxZoom: 13, animate: false });
        setCmpStats(stats);
        setCmpCounts(counts);
        setCmpState("ok");
        setCmpStep("modis-trend");
      } catch {
        if (!cancelled) setCmpState("none");
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected?.id, mapReady]);

  useEffect(() => {
    const map = mapRef.current;
    const L = LRef.current;
    if (!map || !L) return;
    if (cmpOverlayRef.current) map.removeLayer(cmpOverlayRef.current);
    cmpOverlayRef.current = null;
    if (!cmpStep || !cmpStats || !selected) return;
    cmpOverlayRef.current = L.imageOverlay(
      `/municipios/${slugify(selected.name)}/${cmpStep}.png?v=1`,
      [
        [cmpStats.south, cmpStats.west],
        [cmpStats.north, cmpStats.east],
      ],
      { opacity: 0.92, pane: "cmp" }
    ).addTo(map);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cmpStep, cmpStats]);

  const cmpSteps: [string, string][] = cmpStats
    ? [
        ["modis-trend", "MODIS trend"],
        ["nisar-trend", "NISAR trend"],
        ...cmpStats.modis_years.map((y) => [`modis-${y}`, `MODIS ${y}`] as [string, string]),
        ...cmpStats.nisar_dates.map(
          (d) => [`nisar-${d}`, `NISAR ${d.slice(5).split("-").reverse().join("/")}`] as [string, string]
        ),
      ]
    : [];
  // Time-lapse: MODIS years, then NISAR passes
  const timeline = cmpSteps.slice(2).map(([id]) => id);

  useEffect(() => {
    if (!playing || timeline.length === 0) return;
    const t = window.setInterval(() => {
      setCmpStep((cur) => {
        const i = cur ? timeline.indexOf(cur) : -1;
        return timeline[(i + 1) % timeline.length];
      });
    }, 1200);
    return () => window.clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, cmpStats]);

  const ensureBoxInView = () => {
    const map = mapRef.current;
    const box = cmpBoxRef.current;
    if (map && box && (map.getZoom() < 12 || !map.getBounds().contains(box.getBounds())))
      map.fitBounds(box.getBounds(), { padding: [40, 40], maxZoom: 13 });
  };

  const zoomToBox = () => {
    if (cmpBoxRef.current && mapRef.current)
      mapRef.current.fitBounds(cmpBoxRef.current.getBounds(), {
        padding: [40, 40],
        maxZoom: 13,
      });
  };

  const k = meta?.metricas;
  const families: [string, number][] = shapGlobal
    ? Object.entries(shapGlobal.importancia_familia)
        .map(([f, v]) => [FAM_EN[f] ?? f, v] as [string, number])
        .sort((a, b) => b[1] - a[1])
    : [];
  const activeLegends = LAYERS.filter((l) => layersOn[l.id]);

  // ---------- render ----------
  return (
    <div className="rounded-md border border-border bg-card p-3 shadow-sm sm:p-4">
      {/* header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 max-w-3xl">
          <h2 className="font-display text-lg text-olive sm:text-xl">
            Desertification susceptibility under climate stress
          </h2>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground sm:text-sm">
            Historical degradation (MODIS 2001–2024), climate (CHIRPS, ERA5-Land), land use
            (MapBiomas) and NISAR radar (Jun–Oct 2026) that checks the degradation in the
            present. Click a municipality for its diagnosis.
          </p>
        </div>
        <div className="grid w-full grid-cols-3 gap-2 sm:w-auto sm:min-w-[420px]">
          <Kpi value={fmt(k?.validacao_poligonos_auc_5mun, 2)} label="AUC, NISAR confirms MODIS" />
          <Kpi
            value={k ? `${fmt(k.detector_auc_sem_nisar, 2)} → ${fmt(k.detector_auc_com_nisar, 2)}` : "—"}
            label="detector without → with NISAR"
          />
          <Kpi
            value={shapGlobal ? `${fmt(shapGlobal.participacao_nisar_pct, 0)}%` : "—"}
            label="of the explanation comes from NISAR"
          />
        </div>
      </div>

      {/* layer toggles + legend */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {LAYERS.map((l) => (
          <button
            key={l.id}
            type="button"
            aria-pressed={layersOn[l.id]}
            onClick={() => setLayersOn((s) => ({ ...s, [l.id]: !s[l.id] }))}
            className={cn(
              "rounded-full border px-3 py-1 text-xs transition-colors",
              layersOn[l.id]
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-card text-foreground hover:bg-secondary"
            )}
          >
            {l.label}
          </button>
        ))}
      </div>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[0.68rem] text-muted-foreground">
        <li className="font-medium text-foreground">Municipality outline (risk):</li>
        {(["critico", "alto", "moderado"] as const).map((r) => (
          <li key={r} className="flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-sm border-2" style={{ borderColor: riskColor(r) }} />
            {RISK_LABELS[r]}
          </li>
        ))}
        {activeLegends.map((l) => (
          <li key={l.id} className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-medium text-foreground">{l.label}:</span>
            {l.legend.map(([t, c]) => (
              <span key={t} className="flex items-center gap-1">
                <span className="h-2.5 w-2.5 rounded-sm" style={{ background: c }} />
                {t}
              </span>
            ))}
          </li>
        ))}
      </ul>

      {/* map + diagnosis */}
      <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr)_400px]">
        <div className="relative isolate h-[380px] overflow-hidden rounded-md sm:h-[480px] lg:h-[600px]">
          <div
            ref={containerRef}
            className="absolute inset-0"
            role="region"
            aria-label="Map of the analysed municipalities and model layers"
          />
        </div>

        <aside className="min-w-0 overflow-y-auto rounded-md border border-border bg-background/50 p-3 text-xs lg:h-[600px]">
          <div className="mb-3 flex items-center gap-2 border-b border-border pb-2">
            {selected && (
              <button
                type="button"
                onClick={onClear}
                className="shrink-0 rounded-full border border-border px-2.5 py-1 text-[0.7rem] hover:bg-secondary"
              >
                ← All municipalities
              </button>
            )}
            <label className="sr-only" htmlFor="mun-picker">
              Choose a municipality
            </label>
            <select
              id="mun-picker"
              value={selected?.id ?? ""}
              onChange={(e) => (e.target.value ? onSelect(e.target.value) : onClear())}
              className="min-w-0 flex-1 rounded-md border border-border bg-card px-2 py-1 text-[0.72rem]"
            >
              <option value="">Choose a municipality…</option>
              {[...municipalities]
                .sort((a, b) => a.name.localeCompare(b.name))
                .map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}/{t.dados?.uf}
                    {focus.has(norm(t.name)) ? " · full diagnosis" : ""}
                  </option>
                ))}
            </select>
          </div>
          {!selected ? (
            <div>
              <p className="italic text-muted-foreground">
                Click a municipality on the map (or in the rankings below) to see the diagnosis and
                what explains the risk.
              </p>
              {focusNames.length > 0 && (
                <>
                  <H3>Full model diagnosis</H3>
                  <div className="flex flex-wrap gap-1.5">
                    {focusNames.map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => onSelect(t.id)}
                        className="rounded-full border border-border px-2.5 py-1 text-[0.7rem] hover:bg-secondary"
                      >
                        {t.name}/{t.dados?.uf}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          ) : (
            <div>
              <div className="flex items-baseline justify-between gap-2">
                <h3 className="font-display text-lg text-olive">
                  {selected.name} / {selected.dados?.uf}
                </h3>
                <span
                  className="rounded px-1.5 py-0.5 text-[0.65rem] font-semibold text-white"
                  style={{ background: riskColor(selected.risk) }}
                >
                  {RISK_LABELS[selected.risk]} risk
                </span>
              </div>
              {selected.dados?.area_estudo && (
                <p className="text-[0.7rem] text-muted-foreground">{selected.dados.area_estudo}</p>
              )}

              {focusData ? (
                <>
                  <div className="mt-3 grid grid-cols-3 gap-2">
                    <Kpi value={fmt(focusData.suscetibilidade?.indice_medio, 2)} label="susceptibility index (0–1)" />
                    <Kpi
                      value={`${fmt((focusData.suscetibilidade?.pct_alta ?? 0) + (focusData.suscetibilidade?.pct_muito_alta ?? 0))}%`}
                      label="high + very high area"
                    />
                    <Kpi value={fmt(focusData.nisar?.AUC, 2)} label="AUC NISAR × MODIS" />
                  </div>
                  <table className="mt-3 w-full">
                    <tbody>
                      <Row k="Area with degrading vegetation (MODIS 2001–2024)" v={`${fmt(focusData.modis?.pct_degradado)}%`} />
                      <Row k="Area with improving vegetation" v={`${fmt(focusData.modis?.pct_melhora)}%`} />
                      <Row k="NISAR catches degraded areas (sensitivity)" v={`${fmt(focusData.nisar?.["sensibilidade_%"])}%`} />
                      <Row k="NISAR spares controls (specificity)" v={`${fmt(focusData.nisar?.["especificidade_%"])}%`} />
                      <Row
                        k="Warming (°C/decade, 1991–2024)"
                        v={`${fmt(focusData.clima?.temp_c_tend_decada, 2)}${(focusData.clima?.temp_c_p ?? 1) < 0.05 ? " ✱" : ""}`}
                      />
                      <Row
                        k="Rain 1991–2007 → 2008–2024 (mm/year)"
                        v={`${fmt(focusData.clima?.chuva_media_1991_2007, 0)} → ${fmt(focusData.clima?.chuva_media_2008_2024, 0)}`}
                      />
                      <Row
                        k="Aridity index 1991–2007 → 2008–2024"
                        v={`${fmt(focusData.clima?.aridez_1991_2007, 2)} → ${fmt(focusData.clima?.aridez_2008_2024, 2)}`}
                      />
                      <Row k="Disaster losses 2015–24 (R$ M)" v={fmt(selected.custoNaoAgirMi, 1)} />
                      <Row k="Recognised emergencies, 10 years" v={fmt(selected.dados?.emergencias_reconhecidas_10a, 0)} />
                      <Row k="Deforestation 2001–2024 (ha)" v={fmt(selected.dados?.desmatamento_ha_2001_2024, 0)} />
                    </tbody>
                  </table>
                  <p className="mt-1 text-[0.65rem] text-muted-foreground">
                    ✱ statistically significant trend (p &lt; 0.05).
                  </p>

                  {focusData.contribuicoes_suscetibilidade && (
                    <>
                      <H3>Where the index comes from</H3>
                      <Bars
                        items={Object.entries(focusData.contribuicoes_suscetibilidade).map(
                          ([key, v]) => [CONTRIB_EN[key] ?? key, v] as [string, number]
                        )}
                        max={0.2}
                      />
                    </>
                  )}

                  <H3>Why the detector does or does not flag degradation here</H3>
                  {focusData.shap_detector?.principais?.length ? (
                    <>
                      <Bars
                        items={focusData.shap_detector.principais.map(
                          (p) => [p.rotulo, p.efeito] as [string, number]
                        )}
                        max={Math.max(
                          0.1,
                          ...focusData.shap_detector.principais.map((p) => Math.abs(p.efeito))
                        )}
                      />
                      <p className="mt-1 text-[0.65rem] text-muted-foreground">
                        Brown bars raise the risk; green bars lower it (SHAP in log-odds).
                      </p>
                    </>
                  ) : (
                    <p className="text-muted-foreground">No detector points in this municipality.</p>
                  )}
                </>
              ) : (
                <>
                  <table className="mt-3 w-full">
                    <tbody>
                      <Row k="Area with degrading vegetation (MODIS 2001–2024)" v={`${fmt(selected.tendenciaPp)}%`} />
                      <Row k="Area with improving vegetation" v={`${fmt(selected.dados?.pct_melhora)}%`} />
                      <Row k="Susceptibility index (0–1)" v={fmt(selected.dados?.suscetibilidade_indice, 2)} />
                      <Row
                        k="NISAR × MODIS AUC (points)"
                        v={
                          selected.dados?.nisar
                            ? `${fmt(selected.dados.nisar.auc, 2)} (${selected.dados.nisar.pontos})`
                            : "—"
                        }
                      />
                      <Row
                        k="Mean NISAR probability of degradation"
                        v={selected.dados?.nisar ? `${fmt(100 * selected.dados.nisar.prob_media, 0)}%` : "—"}
                      />
                      <Row
                        k="Warming (°C/decade, 1991–2024)"
                        v={`${fmt(selected.dados?.aquecimento_c_decada, 2)}${selected.dados?.aquecimento_significativo ? " ✱" : ""}`}
                      />
                      <Row
                        k="Rain 1991–2007 → 2008–2024 (mm/year)"
                        v={`${fmt(selected.dados?.chuva_1991_2007_mm, 0)} → ${fmt(selected.dados?.chuva_2008_2024_mm, 0)}`}
                      />
                      <Row k="Disaster losses 2015–24 (R$ M)" v={fmt(selected.custoNaoAgirMi, 1)} />
                      <Row k="Recognised emergencies, 10 years" v={fmt(selected.dados?.emergencias_reconhecidas_10a, 0)} />
                      <Row k="Deforestation 2001–2024 (ha)" v={fmt(selected.dados?.desmatamento_ha_2001_2024, 0)} />
                    </tbody>
                  </table>
                  <p className="mt-2 text-[0.68rem] text-muted-foreground">
                    Index contributions and the per-municipality SHAP are computed for the focus
                    municipalities
                    {focusNames.length > 0 && `: ${focusNames.map((t) => t.name).join(", ")}`}.
                  </p>
                </>
              )}

              {/* MODIS × NISAR visual comparison */}
              {cmpState === "loading" && (
                <p className="mt-4 italic text-muted-foreground">Loading the MODIS × NISAR comparison…</p>
              )}
              {cmpState === "ok" && cmpStats && (
                <div className="mt-4 rounded-md border border-dashed border-border p-2.5">
                  <H3>MODIS × NISAR visual comparison (~13 km box)</H3>
                  <p className="text-[0.68rem] leading-relaxed text-muted-foreground">
                    The team&apos;s qualitative read of GIBS browse colour (MODIS in September{" "}
                    {cmpStats.modis_years[0]}–{cmpStats.modis_years.at(-1)}; NISAR HV from{" "}
                    {cmpStats.nisar_dates.length} passes in 2026). Not the index above.
                  </p>
                  <table className="mt-2 w-full">
                    <tbody>
                      <tr className="text-muted-foreground">
                        <td />
                        <td className="text-right">MODIS</td>
                        <td className="text-right">NISAR</td>
                      </tr>
                      <tr>
                        <td className="py-1 text-muted-foreground">Box area in decline</td>
                        <td className="text-right tabular-nums">{fmt(cmpStats.modis_falling_pct)}%</td>
                        <td className="text-right tabular-nums">{fmt(cmpStats.nisar_falling_pct)}%</td>
                      </tr>
                    </tbody>
                  </table>
                  {cmpCounts && (() => {
                    const tot =
                      cmpCounts.modis_only + cmpCounts.nisar_only + cmpCounts.both + cmpCounts.observed_without_decline;
                    return (
                      <p className="mt-1 text-[0.68rem] text-muted-foreground">
                        Agreement (pixels): both {fmt((100 * cmpCounts.both) / tot, 0)}% · MODIS only{" "}
                        {fmt((100 * cmpCounts.modis_only) / tot, 0)}% · NISAR only{" "}
                        {fmt((100 * cmpCounts.nisar_only) / tot, 0)}%
                      </p>
                    );
                  })()}
                  <div className="mt-2 flex flex-wrap gap-1">
                    {cmpSteps.map(([id, label]) => (
                      <button
                        key={id}
                        type="button"
                        onClick={() => {
                          setPlaying(false);
                          setCmpStep(id);
                          ensureBoxInView();
                        }}
                        className={cn(
                          "rounded-full border px-2 py-0.5 text-[0.66rem]",
                          cmpStep === id
                            ? "border-primary bg-primary text-primary-foreground"
                            : "border-border hover:bg-secondary"
                        )}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  {cmpStep && (
                    <p className="mt-2 text-[0.7rem] font-medium text-foreground">
                      On the map: {cmpSteps.find(([id]) => id === cmpStep)?.[1]}
                    </p>
                  )}
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-[0.68rem]">
                    <button
                      type="button"
                      onClick={() => {
                        ensureBoxInView();
                        setPlaying((v) => !v);
                      }}
                      className={cn(
                        "rounded-full border px-2 py-0.5",
                        playing ? "border-primary bg-primary text-primary-foreground" : "border-border hover:bg-secondary"
                      )}
                    >
                      {playing ? "❚❚ Pause" : "▶ Play time-lapse"}
                    </button>
                    <button type="button" onClick={zoomToBox} className="rounded-full border border-border px-2 py-0.5 hover:bg-secondary">
                      Zoom to the box
                    </button>
                    <button type="button" onClick={() => { setPlaying(false); setCmpStep(null); }} className="rounded-full border border-border px-2 py-0.5 hover:bg-secondary">
                      Hide image
                    </button>
                    <a href="/municipios.html" className="text-primary underline-offset-2 hover:underline">
                      full comparison →
                    </a>
                    <a href="/comparar/" className="text-primary underline-offset-2 hover:underline">
                      draw an area and explain →
                    </a>
                  </div>
                </div>
              )}
            </div>
          )}
        </aside>
      </div>

      {/* global SHAP */}
      <div className="mt-4 grid grid-cols-1 gap-4 border-t border-border pt-4 lg:grid-cols-2">
        <div>
          <h3 className="font-display text-base text-olive">What the model uses to decide (SHAP)</h3>
          <p className="mb-2 mt-1 text-[0.7rem] text-muted-foreground">
            Detector of degraded or converted Caatinga (record through 2014 + climate + NISAR 2026).
            Mean |SHAP| importance by family.
          </p>
          {families.length ? (
            <Bars items={families} max={Math.max(...families.map(([, v]) => v))} />
          ) : (
            <p className="text-xs text-muted-foreground">{apiError ? "Model results unavailable." : "Loading…"}</p>
          )}
          <p className="mt-3 text-[0.68rem] leading-relaxed text-muted-foreground">
            {meta && (
              <>
                Sources: {meta.fontes.map((f) => f.replace("provisório, jun–out/2026", "provisional, Jun–Oct 2026")).join(" · ")}.
                Published {new Date(meta.publicado_em).toLocaleString("en-US")}.{" "}
              </>
            )}
            NISAR is provisional and covers only the 2026 dry season. Vegetation degradation is not
            field-confirmed desertification.
          </p>
          <div className="mt-2 flex flex-wrap gap-3 text-[0.72rem]">
            <a href="/municipios.html" className="text-primary hover:underline">MODIS × NISAR by municipality</a>
            <a href="/produto.html" className="text-primary hover:underline">GeoTIFF product</a>
            <a href="/comparar/" className="text-primary hover:underline">Compare and explain</a>
            <a href="/docs" className="text-primary hover:underline">API</a>
          </div>
        </div>
        <div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`${API}/figuras/shap_detector_beeswarm.png`}
            alt="SHAP beeswarm for the detector: each dot is an area; colour is the variable value"
            loading="lazy"
            className="w-full rounded-md border border-border bg-white"
          />
        </div>
      </div>
    </div>
  );
}
