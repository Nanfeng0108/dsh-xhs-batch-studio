"""DeepSeek 文本接口 + OpenAI 兼容图片接口的最小客户端（仅标准库）。"""
from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

from . import creds


class APIError(RuntimeError):
    pass


def _post(url: str, headers: dict, payload: dict, timeout: int = 300) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    # 部分中转网关对空 UA 直接 403（Cloudflare 1010），统一带一个常规 UA
    headers = {"User-Agent": "OpenAI/Python 1.0", **headers}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    last: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")[:600]
            last = APIError(f"HTTP {e.code}: {body}")
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt + 1)
                continue
            raise last from None
        except (urllib.error.URLError, TimeoutError) as e:
            last = APIError(f"network: {e}")
            time.sleep(2 ** attempt + 1)
    raise last or APIError("unknown")


def chat(
    messages: list[dict],
    model: str | None = None,
    json_mode: bool = True,
    temperature: float = 0.85,
    max_tokens: int = 8000,
    timeout: int = 300,
) -> str:
    api = creds.text_api()
    model = model or api.get("model") or "deepseek-flash"
    candidates = [model] + [m for m in (api.get("models") or []) if m and m != model]
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    url = f"{api['base']}/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api['key']}"}
    resp: dict = {}
    last_error: Exception | None = None
    for candidate in candidates[:3]:
        payload["model"] = candidate
        try:
            resp = _post(url, headers, payload, timeout=timeout)
            last_error = None
            break
        except APIError as e:
            text = str(e)
            # 部分代理不支持 response_format，退回普通模式
            if "response_format" in text or "HTTP 400" in text:
                payload.pop("response_format", None)
                try:
                    resp = _post(url, headers, payload, timeout=timeout)
                    last_error = None
                    break
                except APIError as inner:
                    last_error = inner
                    text = str(inner)
            last_error = last_error or e
            # 模型没了/通道挂了，换该 provider 的下一个模型再试
            if not any(tag in text for tag in ("502", "503", "404", "model_not_found", "No available channel")):
                raise
    if last_error:
        raise last_error
    try:
        msg = resp["choices"][0]["message"]
    except (KeyError, IndexError) as e:
        raise APIError(f"bad response: {json.dumps(resp)[:400]}") from e
    content = msg.get("content") or ""
    if not content and msg.get("reasoning_content"):
        content = msg["reasoning_content"]
    return content.strip()


def parse_json(text: str) -> dict:
    """从模型输出中稳健地抠出 JSON 对象。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start >= 0:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    raise APIError(f"模型未返回合法 JSON: {text[:200]}")


_IMG_MODEL: str | None = None


def _image_models(preferred: str | None) -> list[str]:
    api = creds.image_api()
    cands = [
        preferred or "",
        os.environ.get("XHS_IMAGE_MODEL", ""),
        api.get("model", ""),
        "gpt-image-2.5",
        "gpt-image-2",
        "gpt-image-1.5",
        "gpt-image-1",
        "dall-e-3",
    ]
    seen, out = set(), []
    for c in cands:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    if _IMG_MODEL:
        out.remove(_IMG_MODEL)
        out.insert(0, _IMG_MODEL)
    return out


def generate_image(prompt: str, out_path: Path, size: str = "1024x1536",
                   model: str | None = None, timeout: int = 240) -> Path:
    """按可用模型逐个尝试；单个模型偶发 4xx/5xx 时重试一次，全部失败才报错。"""
    global _IMG_MODEL
    api = creds.image_api()
    last: Exception | None = None
    for name in _image_models(model):
        for attempt in range(2):
            payload = {"model": name, "prompt": prompt, "n": 1, "size": size}
            url = f"{api['base']}/images/generations"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api['key']}"}
            try:
                resp = _post(url, headers, payload, timeout=timeout)
                item = (resp.get("data") or [{}])[0]
                if not (item.get("b64_json") or item.get("url")):
                    raise APIError(f"图片接口无数据: {json.dumps(resp)[:200]}")
            except APIError as e:
                last = e
                msg = str(e)
                if attempt == 0 and any(k in msg for k in ("HTTP 400", "HTTP 429", "HTTP 5")):
                    time.sleep(1.5)
                    continue
                break
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if item.get("b64_json"):
                out_path.write_bytes(base64.b64decode(item["b64_json"]))
            else:
                with urllib.request.urlopen(item["url"], timeout=120) as r:
                    out_path.write_bytes(r.read())
            _IMG_MODEL = name
            return out_path
    raise last or APIError("没有可用的图片模型")
