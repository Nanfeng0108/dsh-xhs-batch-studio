"""密钥解析：优先环境变量，其次 DSH 桌面版凭据库，最后本地 config。

不打印、不落盘任何密钥明文。
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

CRED_PATHS = [
    Path.home() / "Library/Application Support/dsh-desktop/harness/.credentials.yaml",
    Path.home() / "Library/Application Support/dsh-desktop/harness/credentials.yaml",
    Path.home() / ".dsh/credentials.yaml",
]


def _load_yaml() -> dict:
    for p in CRED_PATHS:
        if not p.exists():
            continue
        try:
            import yaml  # type: ignore

            return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception:
            return _load_loose(p)
    return {}


def _load_loose(path: Path) -> dict:
    """PyYAML 不可用时的极简解析：只认 refs 与 image 配置里的标量。"""
    txt = path.read_text(encoding="utf-8")
    out: dict = {"refs": {}, "records": {}}
    for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY"):
        m = re.search(rf"^\s*{k}:\s*(\S+)\s*$", txt, re.M)
        if m:
            out["refs"][k] = m.group(1)
    for k in ("baseUrl", "model", "key"):
        m = re.search(rf"^\s*{k}:\s*(\S+)\s*$", txt, re.M)
        if m:
            out["records"].setdefault("img", {})[k] = m.group(1)
    return out


_CREDS: Optional[dict] = None


def creds() -> dict:
    global _CREDS
    if _CREDS is None:
        _CREDS = _load_yaml()
    return _CREDS


# ---------------------------------------------------------------- DSH 模型配置
# DSH 的模型 provider 写在 profiles/<profile>/cordis.patch.yml 的 llm-pi-ai 里：
#   providers: {openai: {baseURL: ..., apiKeyEnv: OPENAI_API_KEY, models: [...]}}
# 同事机器上如果只配了中转/别家模型，就读这份配置，做到“用 DSH 客户端那把 key”。
def _profile_dirs() -> list[Path]:
    roots: list[Path] = []
    home = os.environ.get("DSH_HOME")
    if home:
        roots.append(Path(home))
    roots.append(Path.home() / "Library/Application Support/dsh-desktop/harness")
    roots.append(Path.home() / ".dsh")
    dirs: list[Path] = []
    for root in roots:
        profiles = root / "profiles"
        if not profiles.is_dir():
            continue
        dirs.append(profiles / "web")
        try:
            dirs.extend(sorted(p for p in profiles.iterdir() if p.is_dir() and p.name != "web"))
        except OSError:
            pass
    return dirs


def _read_yaml_file(path: Path) -> list:
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        return data if isinstance(data, list) else []
    except Exception:
        return []


def dsh_llm_provider() -> Optional[dict]:
    """从 DSH 的 profile 配置里找当前模型的 baseURL / key / model。"""
    refs = creds().get("refs") or {}
    for profile in _profile_dirs():
        for name in ("cordis.patch.yml", "cordis.yml"):
            path = profile / name
            if not path.is_file():
                continue
            for entry in _read_yaml_file(path):
                if not isinstance(entry, dict) or entry.get("id") != "llm-pi-ai":
                    continue
                providers = ((entry.get("config") or {}).get("providers") or {})
                for provider in providers.values():
                    if not isinstance(provider, dict):
                        continue
                    base = str(provider.get("baseURL") or provider.get("baseUrl") or "").strip()
                    env_name = str(provider.get("apiKeyEnv") or "").strip()
                    key = os.environ.get(env_name, "") if env_name else ""
                    key = key or refs.get(env_name, "")
                    if not (base and key):
                        continue
                    models = provider.get("models") or []
                    ids = [str(m.get("id")) for m in models if isinstance(m, dict) and m.get("id")]
                    ordered = [i for i in ids if "deepseek" in i.lower()] + [i for i in ids if "deepseek" not in i.lower()]
                    model = ordered[0] if ordered else ""
                    return {"base": base.rstrip("/"), "key": key, "model": model,
                            "models": ordered, "source": f"dsh:{env_name}"}
    return None


def text_api() -> dict:
    """只认 DeepSeek：显式环境变量 → DSH 凭据库里的 DEEPSEEK_API_KEY。

    DSH 当前 provider（baseURL + 模型名 + 别家 Key）默认不参与，避免文案风格随机器漂移；
    确实想借用时显式设置 XHS_USE_DSH_MODEL=1。
    """
    refs = creds().get("refs") or {}
    key = os.environ.get("DEEPSEEK_API_KEY") or refs.get("DEEPSEEK_API_KEY", "")
    base = os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
    if key:
        return {
            "key": key,
            "base": base.rstrip("/"),
            "model": os.environ.get("DEEPSEEK_MODEL") or "deepseek-flash",
            "source": "deepseek",
        }
    if os.environ.get("XHS_USE_DSH_MODEL") == "1":
        provider = dsh_llm_provider()
        if provider and provider.get("model"):
            return provider
    raise SystemExit(
        "找不到 DEEPSEEK_API_KEY：请在 DSH 里配置 DeepSeek 模型（设置 → 模型 → DeepSeek），"
        "或在终端设置环境变量 DEEPSEEK_API_KEY 后从终端启动 DSH。"
        "（不想用 DeepSeek 时可显式设置 XHS_USE_DSH_MODEL=1 借用 DSH 当前模型）"
    )


def image_api() -> dict:
    rec = creds().get("records") or {}
    cfg = rec.get("dsh-image-generation/configuration") or {}
    payload = cfg.get("payload") or {}
    profiles = payload.get("profiles") or {}
    prof = profiles.get("openai") or {}
    key = os.environ.get("OPENAI_API_KEY") or prof.get("key") or (creds().get("refs") or {}).get("OPENAI_API_KEY", "")
    base = prof.get("baseUrl") or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = prof.get("model") or "gpt-image-1"
    if not key:
        raise RuntimeError("找不到图片生成密钥（Settings > Plugins > Image generation 未配置）")
    return {"key": key, "base": base.rstrip("/"), "model": model}
