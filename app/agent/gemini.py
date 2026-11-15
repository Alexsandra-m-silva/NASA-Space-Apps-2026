"""Cliente mínimo da API oficial do Google Gemini (mesmo padrão do Simemap).

A chave fica só no servidor (variável GEMINI_API_KEY) e nunca vai para o navegador nem para logs.
"""

from __future__ import annotations

import http.client
import json
import os
import urllib.error
import urllib.request

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-3.8-flash"


class GeminiError(Exception):
    """Erro seguro para exibir: sem a chave nem o corpo da resposta do provedor."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def _key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise GeminiError("GEMINI_API_KEY não configurada.")
    return key


def _call(path: str, payload: dict, timeout: int) -> dict:
    request = urllib.request.Request(
        f"{API_BASE}/{path}", data=json.dumps(payload).encode(),
        headers={"x-goog-api-key": _key(), "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with _opener.open(request, timeout=timeout) as response:
            data = json.loads(response.read().decode())
        if not isinstance(data, dict):
            raise GeminiError("O Gemini devolveu uma resposta inesperada.")
        return data
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise GeminiError("Modelo Gemini indisponível neste projeto (ajuste GEMINI_MODEL).") from None
        if exc.code in (400, 401, 403):
            raise GeminiError("O Google recusou a solicitação. Verifique a chave Gemini e as permissões.") from None
        if exc.code == 429:
            raise GeminiError("Cota da API Gemini atingida.") from None
        raise GeminiError(f"A API Gemini respondeu com erro {exc.code}.") from None
    except (OSError, ValueError, http.client.HTTPException):
        raise GeminiError("Não foi possível acessar a API Gemini.") from None


def complete(system: str, user: str, max_tokens: int = 8000, timeout: int = 150) -> str:
    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    data = _call(f"models/{model}:generateContent", {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "responseMimeType": "application/json",
                             "temperature": 0.3, "thinkingConfig": {"thinkingLevel": "low"}},
    }, timeout)
    try:
        candidate = data["candidates"][0]
        if candidate.get("finishReason") != "STOP":
            raise GeminiError("O Gemini não concluiu a resposta.")
        text = "".join(p.get("text", "") for p in candidate["content"]["parts"] if not p.get("thought"))
        if not text.strip():
            raise GeminiError("O Gemini não devolveu conteúdo.")
        return text
    except (KeyError, IndexError, TypeError, AttributeError):
        raise GeminiError("O Gemini devolveu uma resposta inesperada.") from None
