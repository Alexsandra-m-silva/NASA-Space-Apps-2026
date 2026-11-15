"""E-mail da recomendação do Desert Sentinel, enviado pelo Brevo (SMTP), como no Clinibud.

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
    """Devolve (assunto, html, texto) para uma recomendação no contrato do Desert Sentinel."""
    app_url = (app_url or os.environ.get("FRONTEND_URL") or "http://localhost:8090").rstrip("/")
    mun = rec.get("municipio", "")
    alerta_txt, alerta_cor = ALERTA.get(rec.get("nivel_alerta"), ALERTA["moderado"])
    pol = {p["id"]: p for p in rec.get("politicas_referencia") or []}
    subject = f"Desert Sentinel · {mun}: {alerta_txt.lower()} of vegetation degradation — recommendations"

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
      <div style="color:#f0c36a;font-size:12px;letter-spacing:2px;text-transform:uppercase;font-weight:bold;">Desert Sentinel · NASA Space Apps 2026</div>
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


def send(to: list[str], subject: str, html_body: str, text_body: str) -> str:
    login, key = os.environ.get("BREVO_SMTP_LOGIN", ""), os.environ.get("BREVO_SMTP", "")
    sender = os.environ.get("DEFAULT_FROM_EMAIL", "")
    if not (login and key and sender):
        raise EmailError("Configure BREVO_SMTP_LOGIN, BREVO_SMTP e DEFAULT_FROM_EMAIL.")
    if not to or len(to) > 20:
        raise EmailError("Informe de 1 a 20 destinatários.")
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, formataddr(("Desert Sentinel", sender)), ", ".join(to)
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
