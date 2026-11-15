"""E-mail da recomendação do Climate Sentinel, enviado pelo Brevo (SMTP), como no Clinibud.

Variáveis (mesmos nomes do Clinibud):
  BREVO_SMTP_LOGIN     login SMTP do Brevo
  BREVO_SMTP           chave SMTP do Brevo
  DEFAULT_FROM_EMAIL   remetente (domínio validado no Brevo)
  FRONTEND_URL         endereço público do app (links no e-mail)
  EMAIL_ADMIN_TOKEN    token exigido pela API para disparar envios (sem ele, o envio pela API fica desligado)

Uso pela linha de comando (servidor):
  python -m app.notify.email "Petrolina/PE" --preview saida.html     # só gera o HTML
  python -m app.notify.email "Petrolina/PE" --para alguem@exemplo.org # envia
"""

from __future__ import annotations

import html
import json
import os
import smtplib
import sys
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path

SMTP_HOST = "smtp-relay.brevo.com"
SMTP_PORT = 587
BUNDLE = Path(os.environ.get("BUNDLE_DIR", Path(__file__).resolve().parents[1] / "bundle"))

CAT = {
    "SUPPORT": ("Support", "#2f7d4f", "Existing relevant policy: keep or expand."),
    "IMPROVE": ("Improve", "#b7791f", "Existing policy with a gap identified by the data."),
    "CREATE": ("Create", "#b03024", "Need without a matching policy in the reference list."),
    "MONITOR": ("Monitor", "#2b6cb0", "Situation to follow: weak signal, provisional or diverging data."),
}
ALERTA = {"alto": ("High alert", "#b03024"), "moderado": ("Moderate alert", "#b7791f"), "baixo": ("Low alert", "#2f7d4f")}
ESFERA = {"municipal": "Municipal", "estadual": "State", "federal": "Federal"}
PRIO = {"alta": "high", "media": "medium", "baixa": "low"}


class EmailError(Exception):
    """Erro seguro para exibir (sem credenciais)."""


def _e(v) -> str:
    return html.escape(str(v or ""))


def render(rec: dict, app_url: str | None = None) -> tuple[str, str, str]:
    """Devolve (assunto, html, texto) para uma recomendação no contrato do Climate Sentinel."""
    app_url = (app_url or os.environ.get("FRONTEND_URL") or "http://localhost:8090").rstrip("/")
    mun = rec.get("municipio", "")
    alerta_txt, alerta_cor = ALERTA.get(rec.get("nivel_alerta"), ALERTA["moderado"])
    pol = {p["id"]: p for p in rec.get("politicas_referencia") or []}
    subject = f"Climate Sentinel · {mun}: {alerta_txt.lower()} of vegetation degradation — recommendations"

    cards, text_recs = [], []
    for i, r in enumerate(rec.get("recomendacoes") or [], 1):
        nome, cor, desc = CAT.get(r.get("categoria"), ("—", "#555", ""))
        ev = "".join(f"<li>{_e(x)}</li>" for x in r.get("evidencias") or [])
        pols = "".join(
            f'<span style="display:inline-block;margin:2px 4px 2px 0;padding:2px 8px;border:1px solid #d8cbb3;border-radius:10px;font-size:12px;">'
            f'{_e(pol.get(pid, {}).get("nome", pid))}{" (to verify)" if pol.get(pid, {}).get("verificar") else ""}</span>'
            for pid in r.get("politicas") or [])
        resp = ", ".join(f'{ESFERA.get(x.get("esfera"), "")}: {_e(x.get("orgao"))}' for x in r.get("responsaveis") or [])
        lim = "".join(f"<li>{_e(x)}</li>" for x in r.get("limitacoes") or [])
        cards.append(f"""
        <tr><td style="padding:0 0 14px 0;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e6dccb;border-left:5px solid {cor};border-radius:8px;">
            <tr><td style="padding:14px 16px;font-family:Arial,Helvetica,sans-serif;color:#1d2a26;">
              <div style="font-size:12px;letter-spacing:1px;text-transform:uppercase;color:{cor};font-weight:bold;">{i}. {nome} · {PRIO.get(r.get("prioridade"), _e(r.get("prioridade")))} priority</div>
              <div style="font-size:16px;font-weight:bold;margin:6px 0 6px;">{_e(r.get("acao"))}</div>
              <div style="font-size:14px;line-height:1.5;margin-bottom:8px;">{_e(r.get("justificativa"))}</div>
              {f'<div style="font-size:13px;font-weight:bold;">Evidence</div><ul style="margin:4px 0 8px 18px;padding:0;font-size:13px;line-height:1.5;">{ev}</ul>' if ev else ""}
              {f'<div style="font-size:13px;font-weight:bold;margin-bottom:2px;">Related policies</div><div style="margin-bottom:8px;">{pols}</div>' if pols else ""}
              {f'<div style="font-size:13px;"><b>Responsible:</b> {resp}</div>' if resp else ""}
              {f'<div style="font-size:12px;color:#6b6457;margin-top:6px;"><b>Limitations:</b></div><ul style="margin:2px 0 0 18px;padding:0;font-size:12px;color:#6b6457;">{lim}</ul>' if lim else ""}
              <div style="font-size:11px;color:#8a8170;margin-top:6px;">{desc}</div>
            </td></tr>
          </table>
        </td></tr>""")
        text_recs.append(f"{i}. [{nome}] {r.get('acao')}\n   {r.get('justificativa')}\n   Evidence: {'; '.join(r.get('evidencias') or [])}")

    rascunho = (rec.get("rascunho_x") or {}).get("texto") or ""
    lim_g = "".join(f"<li>{_e(x)}</li>" for x in rec.get("limitacoes_gerais") or [])
    body = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{_e(subject)}</title></head>
<body style="margin:0;padding:0;background:#f4f0e8;">
<div style="display:none;max-height:0;overflow:hidden;">{_e(rec.get("diagnostico"))[:150]}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f0e8;padding:24px 0;">
<tr><td align="center">
  <table role="presentation" width="620" cellpadding="0" cellspacing="0" style="max-width:620px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;">
    <tr><td style="background:#10140f;padding:22px 24px;font-family:Arial,Helvetica,sans-serif;">
      <div style="color:#f0c36a;font-size:12px;letter-spacing:2px;text-transform:uppercase;font-weight:bold;">Climate Sentinel · NASA Space Apps 2026</div>
      <div style="color:#f4efe6;font-size:22px;font-weight:bold;margin-top:6px;">Vegetation degradation in {_e(mun)}</div>
      <div style="margin-top:10px;"><span style="background:{alerta_cor};color:#fff;font-size:12px;font-weight:bold;padding:4px 10px;border-radius:12px;">{alerta_txt}</span></div>
    </td></tr>
    <tr><td style="padding:22px 24px 6px;font-family:Arial,Helvetica,sans-serif;color:#1d2a26;">
      <div style="font-size:13px;font-weight:bold;text-transform:uppercase;letter-spacing:1px;color:#8a6d2b;">Diagnosis</div>
      <p style="font-size:15px;line-height:1.6;margin:8px 0 18px;">{_e(rec.get("diagnostico"))}</p>
      <div style="font-size:13px;font-weight:bold;text-transform:uppercase;letter-spacing:1px;color:#8a6d2b;margin-bottom:10px;">Recommendations</div>
    </td></tr>
    <tr><td style="padding:0 24px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{"".join(cards)}</table></td></tr>
    {f'''<tr><td style="padding:6px 24px 0;font-family:Arial,Helvetica,sans-serif;color:#1d2a26;">
      <div style="font-size:13px;font-weight:bold;text-transform:uppercase;letter-spacing:1px;color:#8a6d2b;">Suggested post (requires human review)</div>
      <div style="margin:8px 0 16px;padding:12px 14px;background:#f7f3ea;border-radius:8px;font-size:14px;line-height:1.5;">{_e(rascunho)}</div>
    </td></tr>''' if rascunho else ""}
    <tr><td align="center" style="padding:8px 24px 20px;">
      <a href="{_e(app_url)}/modelo.html" style="display:inline-block;background:#f0c36a;color:#1b1408;font-family:Arial,Helvetica,sans-serif;font-weight:bold;font-size:14px;text-decoration:none;padding:12px 22px;border-radius:22px;">See map and evidence</a>
      <a href="{_e(app_url)}/comparar/" style="display:inline-block;margin-left:8px;color:#8a6d2b;font-family:Arial,Helvetica,sans-serif;font-size:14px;">Compare and explain</a>
    </td></tr>
    <tr><td style="padding:14px 24px 22px;background:#faf7f1;font-family:Arial,Helvetica,sans-serif;color:#6b6457;font-size:12px;line-height:1.5;">
      {f'<b>Limitations</b><ul style="margin:4px 0 10px 18px;padding:0;">{lim_g}</ul>' if lim_g else ""}
      Data: NASA NISAR (L2 GCOV, provisional, 2026 dry season), MODIS, CHIRPS, ERA5-Land and MapBiomas.
      Satellite-based vegetation degradation is not proof of desertification on the ground.
      Recommendations generated by AI from these indicators and a closed list of policies; items marked
      "to verify" must be checked against the official source.<br>
      Generated {_e(rec.get("gerado_em"))} · model {_e(rec.get("modelo"))}.
    </td></tr>
  </table>
</td></tr></table></body></html>"""
    text = (f"{subject}\n\nDiagnosis: {rec.get('diagnostico')}\n\nRecommendations:\n" + "\n".join(text_recs)
            + (f"\n\nSuggested post (requires review): {rascunho}" if rascunho else "")
            + f"\n\nMap and evidence: {app_url}/modelo.html\n"
            "Satellite-based degradation is not proof of desertification. Recommendations generated by AI.")
    return subject, body, text


_LEVEL_EN = {"bioma": "Biome", "regiao": "Region", "estado": "State", "municipio": "Municipality"}
_IMPACT_EN = {"inseguranca_alimentar": "Food insecurity", "deficit_hidrico": "Water deficit",
              "perda_renda": "Income / crop loss", "migracao": "Migration / emergency",
              "pressao_biodiversidade": "Pressure on flora and fauna"}
_RISK_EN = {"critico": "Critical", "alto": "High", "moderado": "Moderate"}
_ROLE_EN = {"gestor": "Government / public sector", "imprensa": "Journalism / media",
            "ong": "NGO / civil society", "empresa": "Business / private sector", "outro": "Other"}


_RISK_ORDER = {"critico": 3, "alto": 2, "moderado": 1}
_RISK_COLOR = {"critico": "#b0301f", "alto": "#A0522D", "moderado": "#C9A227"}


def _territories() -> list[dict]:
    try:
        return json.loads((BUNDLE / "territorios.json").read_text(encoding="utf-8"))["territories"]
    except (OSError, ValueError, KeyError):
        return []


def select_territories(prefs: dict) -> tuple[list[dict], bool]:
    """Territórios analisados que casam com a seleção da newsletter.

    Devolve (lista ordenada por risco e tendência, casou_com_a_selecao). Se nada da seleção
    estiver entre os municípios analisados, devolve o panorama dos municípios e False.
    """
    allt = _territories()
    level = prefs.get("level", "estado")
    items = [t for t in allt if t.get("level") == level]
    if level == "estado" and prefs.get("estados"):
        uf_by_code = {str((t.get("dados") or {}).get("ibge", ""))[:2]: t.get("mapKey")
                      for t in allt if t.get("level") == "municipio"}
        wanted = {uf_by_code.get(str(c)) for c in prefs["estados"]} - {None}
        items = [t for t in items if t.get("mapKey") in wanted]
    elif level == "municipio" and prefs.get("municipios"):
        wanted = {f"mun-{c}" for c in prefs["municipios"]}
        items = [t for t in items if t.get("id") in wanted]
    elif level == "bioma" and prefs.get("biomas"):
        items = [t for t in items if t.get("mapKey") in set(prefs["biomas"])]
    elif level == "regiao" and prefs.get("regioes"):
        # As áreas de estudo ficam todas no Nordeste (região IBGE 2)
        items = items if "2" in {str(r) for r in prefs["regioes"]} else []
    impacts = set(prefs.get("impacts") or [])
    if impacts and len(impacts) < len(_IMPACT_EN):
        items = [t for t in items if impacts & set(t.get("impacts") or [])]
    risks = set(prefs.get("risks") or [])
    if risks and len(risks) < len(_RISK_EN):
        items = [t for t in items if t.get("risk") in risks]
    matched = bool(items)
    if not matched:
        items = [t for t in allt if t.get("level") == "municipio"]
    items.sort(key=lambda t: (-_RISK_ORDER.get(t.get("risk"), 0), -(t.get("tendenciaPp") or 0)))
    return items, matched


def _briefing(prefs: dict) -> tuple[str, str]:
    """Primeira edição: situação atual da seleção (HTML, texto)."""
    items, matched = select_territories(prefs)
    top = items[:8]
    n_crit = sum(1 for t in items if t.get("risk") == "critico")
    losses = sum(t.get("custoNaoAgirMi") or 0 for t in items)
    lead = (f"{len(items)} {'territory matches' if len(items) == 1 else 'territories match'} your selection; {n_crit} at critical risk. "
            f"Recorded drought and flood losses 2015–24: R$ {losses:,.0f} million (inflation-adjusted)."
            if matched else
            "Nothing in your selection matches your filters today: either it is outside the 18 municipalities "
            "we analyse, or no territory there is at the risk level or impact you chose. Here is the overview of "
            "the Brazilian semi-arid; you will be notified as soon as your selection is affected.")

    def row(t: dict) -> str:
        nisar = ((t.get("dados") or {}).get("nisar") or {}).get("auc")
        risk = t.get("risk")
        return (
            '<tr>'
            f'<td style="padding:7px 6px 7px 0;color:#220F08;font-size:13px;border-bottom:1px solid #F0E6CC;">{_e(t.get("name"))}</td>'
            f'<td style="padding:7px 6px;font-size:12px;border-bottom:1px solid #F0E6CC;">'
            f'<span style="color:#fff;background:{_RISK_COLOR.get(risk, "#999")};border-radius:4px;padding:2px 6px;">{_e(_RISK_EN.get(risk, risk))}</span></td>'
            f'<td style="padding:7px 6px;color:#220F08;font-size:13px;text-align:right;border-bottom:1px solid #F0E6CC;">{(t.get("tendenciaPp") or 0):.1f}%</td>'
            f'<td style="padding:7px 0 7px 6px;color:#220F08;font-size:13px;text-align:right;border-bottom:1px solid #F0E6CC;">{(t.get("custoNaoAgirMi") or 0):,.0f}</td>'
            f'<td style="padding:7px 0 7px 6px;color:#220F08;font-size:13px;text-align:right;border-bottom:1px solid #F0E6CC;">{f"{nisar:.2f}" if isinstance(nisar, (int, float)) else "—"}</td>'
            '</tr>')

    th = 'style="padding:6px 6px 6px 0;color:#7a6250;font-size:11px;text-align:{a};text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #E5D4A8;"'
    html = (
        '<h2 style="margin:22px 0 6px;color:#642F07;font-family:Georgia,serif;font-size:19px;font-weight:normal;">'
        'Your first briefing</h2>'
        f'<p style="margin:0 0 10px;color:#220F08;font-size:14px;line-height:1.5;">{_e(lead)}</p>'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 6px;">'
        f'<tr><th {th.format(a="left")}>Territory</th><th {th.format(a="left")}>Risk</th>'
        f'<th {th.format(a="right")}>Area degrading</th><th {th.format(a="right")}>Losses R$ M</th>'
        f'<th {th.format(a="right")}>NISAR AUC</th></tr>'
        + "".join(row(t) for t in top) + '</table>'
        '<p style="margin:0 0 4px;color:#7a6250;font-size:11px;line-height:1.5;">'
        'Area degrading: share of the area with declining vegetation, MODIS NDVI 2001–2024 with rainfall '
        'removed (RESTREND, Mann-Kendall p&lt;0.05). Losses: Atlas Digital de Desastres (S2iD) 2015–24. '
        'NISAR AUC: how well the 2026 L-band SAR radar separates degraded from stable areas.</p>')
    text = "\nYour first briefing\n" + lead + "\n" + "\n".join(
        f"- {t.get('name')}: {_RISK_EN.get(t.get('risk'), t.get('risk'))} risk, "
        f"{(t.get('tendenciaPp') or 0):.1f}% area degrading, R$ {(t.get('custoNaoAgirMi') or 0):,.0f} M losses"
        for t in top) + "\n"
    return html, text


def render_welcome(email: str, role: str, org: str | None, prefs: dict,
                   app_url: str | None = None) -> tuple[str, str, str]:
    """Primeira edição da newsletter, enviada na inscrição.

    Layout do modelo da Gabi (platform/public/newsletter/sample-email.html): cabeçalho
    escuro em degradê, bloco "Your selection" com borda mel e cartões numerados por
    território. Estilos inline e tabelas, porque clientes de e-mail ignoram <style>,
    variáveis CSS, grid e color-mix. Dados reais do bundle (territorios.json).
    """
    from datetime import datetime, timezone

    app_url = (app_url or os.environ.get("FRONTEND_URL") or "http://localhost:8090").rstrip("/")
    C = {"cafe": "#220F08", "barro": "#642F07", "sol": "#FFEA7F", "ocre": "#A2510F", "mel": "#DAA849",
         "ambar": "#B67523", "canvas": "#FBF7EF", "surface": "#FFFDF8", "subtle": "#F3EBD9",
         "border": "#DDD5BA", "muted": "#6B5545", "error": "#963B2F"}
    accent = {"critico": C["error"], "alto": C["barro"], "moderado": C["ambar"]}

    level = prefs.get("level", "estado")
    key = {"bioma": "biomas", "regiao": "regioes", "estado": "estados", "municipio": "municipios"}.get(level, "estados")
    chosen = prefs.get(key) or []
    impacts_sel = [_IMPACT_EN.get(i, i) for i in (prefs.get("impacts") or [])]
    risks_sel = [_RISK_EN.get(r, r) for r in (prefs.get("risks") or [])]
    items, matched = select_territories(prefs)
    top = items[:6]
    n_crit = sum(1 for t in items if t.get("risk") == "critico")
    losses = sum(t.get("custoNaoAgirMi") or 0 for t in items)
    today = datetime.now(timezone.utc).strftime("%d %b %Y")

    selection_line = (
        f"Level: {_LEVEL_EN.get(level, level)} · Geography: "
        f"{(str(len(chosen)) + ' selected') if chosen else 'all in the level'} · Impacts: "
        f"{', '.join(impacts_sel) if impacts_sel and len(impacts_sel) < len(_IMPACT_EN) else 'all'} · Risks: "
        f"{', '.join(risks_sel) if risks_sel and len(risks_sel) < len(_RISK_EN) else 'all'} · Monthly digest: "
        f"{'on' if prefs.get('emailMonthly', True) else 'off'}")
    if matched:
        lede = (f"{len(items)} {'territory matches' if len(items) == 1 else 'territories match'} your selection, "
                f"{n_crit} at critical risk. Recorded drought and flood losses 2015–24: "
                f"R$ {losses:,.0f} million (inflation-adjusted).")
        sub = "Where your selection stands today, from the most to the least urgent."
    else:
        lede = ("Nothing in your selection matches your filters today: either it is outside the 18 municipalities "
                "we analyse, or no territory there is at the risk level or impact you chose.")
        sub = "Meanwhile, the overview of the Brazilian semi-arid we monitor."

    def stat(label: str, value: str) -> str:
        return (f'<td width="25%" valign="top" style="padding:8px 8px 8px 0;">'
                f'<div style="font-size:10px;letter-spacing:1px;text-transform:uppercase;color:{C["muted"]};">{_e(label)}</div>'
                f'<div style="font-size:15px;color:{C["cafe"]};font-weight:bold;margin-top:2px;">{_e(value)}</div></td>')

    def card(i: int, t: dict) -> str:
        d = t.get("dados") or {}
        risk = t.get("risk")
        a = accent.get(risk, C["mel"])
        nisar = (d.get("nisar") or {}).get("auc")
        warm = d.get("aquecimento_c_decada")
        region = " · ".join(x for x in [_LEVEL_EN.get(t.get("level"), ""), d.get("area_estudo") or ""] if x)
        imp = ", ".join(_IMPACT_EN.get(x, x).lower() for x in (t.get("impacts") or [])[:3])
        story = (f"{(t.get('tendenciaPp') or 0):.1f}% of the area shows declining vegetation once rainfall is removed "
                 f"(MODIS 2001–2024)."
                 + (f" NISAR L-band SAR separates degraded from stable areas with AUC {nisar:.2f}." if isinstance(nisar, (int, float)) else "")
                 + (f" Main impacts: {imp}." if imp else ""))
        why = ("Critical risk: 8% or more of the area is degrading." if risk == "critico" else
               "High risk: 3–8% of the area is degrading." if risk == "alto" else
               "Moderate risk: under 3% of the area is degrading.")
        name = t.get("name", "")
        if d.get("uf") and t.get("level") == "municipio":
            name = f"{name} ({d['uf']})"
        return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 16px;border:1px solid {C['border']};background:{C['canvas']};">
<tr><td width="5" style="background:{a};font-size:0;">&nbsp;</td><td>
 <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{C['surface']};border-bottom:1px solid {C['border']};">
 <tr>
  <td width="44" valign="top" style="padding:16px 0 12px 14px;font-family:Georgia,'Times New Roman',serif;font-size:28px;line-height:1;color:{a};">{i:02d}</td>
  <td valign="top" style="padding:16px 8px 12px 8px;">
   <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:{a};font-weight:bold;">{_e(_RISK_EN.get(risk, risk))} risk</div>
   <div style="font-family:Georgia,'Times New Roman',serif;font-size:20px;line-height:1.2;color:{C['cafe']};margin-top:4px;">{_e(name)}</div>
   <div style="font-size:12px;color:{C['muted']};margin-top:4px;">{_e(region)}</div>
  </td>
  <td valign="top" align="right" style="padding:16px 14px 12px 0;">
   <span style="display:inline-block;padding:5px 9px;border:1px solid {a};color:{a};font-size:11px;letter-spacing:.5px;text-transform:uppercase;font-weight:bold;white-space:nowrap;">{(t.get('tendenciaPp') or 0):.1f}% degrading</span>
  </td>
 </tr></table>
 <div style="padding:14px 16px 16px 16px;">
  <p style="margin:0 0 12px;color:{C['cafe']};font-size:14px;line-height:1.55;">{_e(story)}</p>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid {C['border']};border-bottom:1px solid {C['border']};"><tr>
   {stat("Population", f"{(t.get('populacaoEstimada') or 0):,}")}
   {stat("Losses 2015–24", f"R$ {(t.get('custoNaoAgirMi') or 0):,.0f} mi")}
   {stat("NISAR AUC", f"{nisar:.2f}" if isinstance(nisar, (int, float)) else "—")}
   {stat("Warming", f"{warm:+.2f} °C/dec" if isinstance(warm, (int, float)) else "—")}
  </tr></table>
  <p style="margin:10px 0 0;font-size:12px;color:{C['muted']};"><strong style="color:{C['cafe']};">Why it's here:</strong> {_e(why)}</p>
 </div>
</td></tr></table>"""

    cards = "".join(card(i + 1, t) for i, t in enumerate(top))
    more = (f'<p style="margin:0 0 18px;font-size:13px;color:{C["muted"]};">+ {len(items) - len(top)} more in '
            f'your selection on the Explore page.</p>') if len(items) > len(top) else ""
    greeting = f"Hello{(' ' + _e(org)) if org else ''}."
    subject = (f"Climate Sentinel · {len(items)} {'territory' if len(items) == 1 else 'territories'} in your selection"
               if matched else "Climate Sentinel · Your first briefing")

    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{_e(subject)}</title></head>
<body style="margin:0;padding:0;background:#E8E0D0;font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;color:{C['cafe']};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#E8E0D0;padding:28px 12px 48px;"><tr><td align="center">
<table role="presentation" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;background:{C['surface']};border:1px solid {C['border']};">
<tr><td style="background-color:{C['cafe']};background-image:linear-gradient(158deg,#220F08 0%,#341C10 40%,#642F07 100%);padding:28px 24px 24px;">
 <p style="margin:0;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:{C['mel']};">Climate Sentinel · newsletter</p>
 <h1 style="margin:8px 0 0;font-family:Georgia,'Times New Roman',serif;font-size:28px;font-weight:normal;line-height:1.15;color:#FBF7EF;">Your first briefing</h1>
 <p style="margin:12px 0 0;color:#F3EBD9;font-size:14px;line-height:1.55;">{_e(lede)}</p>
 <span style="display:inline-block;margin-top:16px;border:1px solid rgba(251,247,239,.35);padding:6px 10px;font-size:12px;color:#F3EBD9;">{today} · NISAR SAR 2026 · MODIS 2001–2024</span>
</td></tr>
<tr><td style="padding:24px;">
 <p style="margin:0 0 20px;font-size:15px;line-height:1.55;">{greeting} You are subscribed with <b>{_e(email)}</b>
  ({_e(_ROLE_EN.get(role, role))}). From now on we email you only when the evidence moves in your selection:
  a trend shift, a new risk category, a new impact type, or a territory entering your risk filter.</p>
 <div style="margin:0 0 26px;padding:12px 14px;background:{C['subtle']};border-left:3px solid {C['mel']};font-size:13px;color:{C['muted']};">
  <strong style="color:{C['cafe']};">Your selection</strong> · {_e(selection_line)}</div>
 <h2 style="margin:8px 0 6px;font-family:Georgia,'Times New Roman',serif;font-size:22px;font-weight:normal;color:{C['cafe']};">Territories in your selection</h2>
 <p style="margin:0 0 18px;font-size:13px;color:{C['muted']};">{_e(sub)}</p>
 {cards}{more}
 <p style="margin:8px 0 22px;"><a href="{_e(app_url)}/explore" style="display:inline-block;background:{C['sol']};color:{C['cafe']};text-decoration:none;padding:11px 20px;font-size:14px;font-weight:bold;">Explore the evidence</a></p>
 <p style="margin:0;font-size:11px;line-height:1.6;color:{C['muted']};">Degrading: share of the area with declining vegetation, MODIS NDVI 2001–2024 with rainfall removed
  (RESTREND, Mann-Kendall p&lt;0.05). Losses: Atlas Digital de Desastres (S2iD), drought and floods, inflation-adjusted.
  NISAR AUC: how well the 2026 L-band SAR radar separates degraded from stable areas. Warming: ERA5-Land 1991–2024.
  Satellite-based degradation is not proof of desertification.</p>
</td></tr>
<tr><td style="background:{C['canvas']};border-top:1px solid {C['border']};padding:16px 24px;font-size:12px;color:{C['muted']};">
 Climate Sentinel · NASA Space Apps Challenge 2026 · To change or cancel, open
 <a href="{_e(app_url)}/newsletter" style="color:{C['barro']};">{_e(app_url)}/newsletter</a>.
</td></tr></table>
</td></tr></table></body></html>"""

    text = (f"Climate Sentinel - your first briefing ({today})\n\n{lede}\n\nYour selection: {selection_line}\n\n"
            + "\n".join(f"{i + 1:02d}. {t.get('name')} - {_RISK_EN.get(t.get('risk'), t.get('risk'))} risk, "
                        f"{(t.get('tendenciaPp') or 0):.1f}% area degrading, R$ {(t.get('custoNaoAgirMi') or 0):,.0f} mi losses 2015-24"
                        for i, t in enumerate(top))
            + f"\n\nExplore the evidence: {app_url}/explore\nChange or cancel: {app_url}/newsletter\n")
    return subject, body, text


def send(to: list[str], subject: str, html_body: str, text_body: str) -> str:
    login, key = os.environ.get("BREVO_SMTP_LOGIN", ""), os.environ.get("BREVO_SMTP", "")
    sender = os.environ.get("DEFAULT_FROM_EMAIL", "")
    if not (login and key and sender):
        raise EmailError("Configure BREVO_SMTP_LOGIN, BREVO_SMTP e DEFAULT_FROM_EMAIL.")
    if not to or len(to) > 20:
        raise EmailError("Informe de 1 a 20 destinatários.")
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, formataddr(("Climate Sentinel", sender)), ", ".join(to)
    msg["Message-ID"] = make_msgid(domain=sender.split("@")[-1])
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(login, key)
            smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        raise EmailError("O Brevo recusou o login SMTP. Verifique BREVO_SMTP_LOGIN e BREVO_SMTP.") from None
    except (smtplib.SMTPException, OSError) as e:
        raise EmailError(f"Falha ao enviar pelo Brevo ({type(e).__name__}).") from None
    return msg["Message-ID"]


def _load(chave: str) -> dict:
    path = BUNDLE / "recomendacoes.json"
    if not path.exists():
        raise SystemExit("Sem recomendações: rode o agente (python -m app.agent.sentinel).")
    data = json.loads(path.read_text(encoding="utf-8"))
    if chave not in data:
        raise SystemExit(f"Sem recomendação para {chave}. Disponíveis: {', '.join(data)}")
    return data[chave]


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    chave = args[0]
    rec = json.loads(Path(args[args.index("--exemplo") + 1]).read_text(encoding="utf-8")) if "--exemplo" in args else _load(chave)
    subject, body, text = render(rec)
    if "--preview" in args:
        out = Path(args[args.index("--preview") + 1])
        out.write_text(body, encoding="utf-8")
        print("HTML gerado em", out, "| assunto:", subject)
    if "--para" in args:
        print("enviado:", send([args[args.index("--para") + 1]], subject, body, text))
