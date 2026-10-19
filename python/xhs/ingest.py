"""资料摄取：Excel / CSV / PDF（文字版 + 扫描件 OCR）/ Word / 纯文本。

统一输出为带定位信息的文本块，便于后续选题与溯源。
"""
from __future__ import annotations

import csv
import io
import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .config import BIN_DIR, PKG_DIR

SUPPORTED = {".xlsx", ".xlsm", ".xls", ".csv", ".pdf", ".docx", ".doc", ".md", ".txt"}
SOFFICE_CANDIDATES = [
    "/Applications/DSH Desktop.app/Contents/Resources/app.asar.unpacked/node_modules/"
    "@deepseek-ai/libreoffice-kit-darwin-arm64/program/LibreOfficeDev.app/Contents/MacOS/soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    shutil.which("soffice") or "",
]


@dataclass
class Block:
    loc: str
    text: str


@dataclass
class Doc:
    path: Path
    kind: str
    blocks: list[Block] = field(default_factory=list)
    ocr_used: bool = False
    warning: str = ""

    @property
    def chars(self) -> int:
        return sum(len(b.text) for b in self.blocks)

    def as_text(self, max_chars: int | None = None) -> str:
        out, total = [], 0
        for b in self.blocks:
            piece = f"[{b.loc}]\n{b.text}"
            if max_chars and total + len(piece) > max_chars:
                break
            out.append(piece)
            total += len(piece)
        return "\n\n".join(out)


# ---------------------------------------------------------------- OCR

def ensure_ocr_binary() -> Path:
    exe = BIN_DIR / "ocr"
    src = PKG_DIR / "ocr.swift"
    if exe.exists() and exe.stat().st_mtime >= src.stat().st_mtime:
        return exe
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["swiftc", "-O", str(src), "-o", str(exe)],
        capture_output=True, text=True, timeout=300,
    )
    if r.returncode != 0:
        raise RuntimeError(f"OCR 编译失败: {r.stderr[-500:]}")
    return exe


def ocr_images(paths: list[Path], batch: int = 8, workers: int = 4) -> dict[str, str]:
    exe = ensure_ocr_binary()
    batches = [paths[i : i + batch] for i in range(0, len(paths), batch)]

    def run(chunk: list[Path]) -> dict[str, str]:
        r = subprocess.run(
            [str(exe), *[str(p) for p in chunk]],
            capture_output=True, text=True, timeout=600,
        )
        res: dict[str, str] = {}
        cur: str | None = None
        buf: list[str] = []
        for line in r.stdout.splitlines():
            if line.startswith("===FILE:"):
                if cur:
                    res[cur] = "\n".join(buf).strip()
                cur = line[len("===FILE:") :]
                buf = []
            else:
                buf.append(line)
        if cur:
            res[cur] = "\n".join(buf).strip()
        return res

    out: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for part in pool.map(run, batches):
            out.update(part)
    return out


# ---------------------------------------------------------------- helpers

def _soffice() -> str | None:
    for c in SOFFICE_CANDIDATES:
        if c and Path(c).exists():
            return c
    return None


def _convert_with_soffice(path: Path) -> Path:
    exe = _soffice()
    if not exe:
        raise RuntimeError(f"需要 LibreOffice 才能读取 {path.suffix}")
    tmp = Path(tempfile.mkdtemp(prefix="xhs-conv-"))
    target = "xlsx" if path.suffix.lower() in (".xls",) else "docx"
    r = subprocess.run(
        [exe, "--headless", "--convert-to", target, "--outdir", str(tmp), str(path)],
        capture_output=True, text=True, timeout=180,
    )
    found = list(tmp.glob(f"*.{target}"))
    if not found:
        raise RuntimeError(f"转换失败 {path.name}: {r.stderr[-200:]}")
    return found[0]


def _clean_text(text: str) -> str:
    import unicodedata

    # PDF 里常见康熙部首（⼩ ⼀ ⽤）与兼容汉字，统一成常规汉字
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def _strip_running_heads(pages: list[str]) -> list[str]:
    """去掉 PDF 每页重复的页眉页脚和纯页码。"""
    if len(pages) < 4:
        return pages
    from collections import Counter

    cnt: Counter[str] = Counter()
    for p in pages:
        lines = [l.strip() for l in p.splitlines() if l.strip()]
        for l in set(lines[:2] + lines[-2:]):
            if len(l) <= 60:
                cnt[l] += 1
    thresh = max(3, int(len(pages) * 0.5))
    noise = {l for l, c in cnt.items() if c >= thresh}

    def filt(p: str) -> str:
        keep = []
        for i, l in enumerate(p.splitlines()):
            s = l.strip()
            if s in noise:
                continue
            if re.fullmatch(r"[-—–\s]*\d{1,4}[-—–\s]*", s):
                continue
            keep.append(l)
        return "\n".join(keep)

    return [filt(p) for p in pages]


# ---------------------------------------------------------------- readers

def read_excel(path: Path) -> Doc:
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    blocks: list[Block] = []
    for ws in wb.worksheets:
        rows: list[list[str]] = []
        for row in ws.iter_rows(values_only=True, max_col=40):
            cells = ["" if v is None else str(v).strip() for v in row]
            if any(cells):
                rows.append(cells)
        if not rows:
            continue
        # 列名 = 第一行非空；若首行像数据（都短且无重复标题），退回通用列名
        header = rows[0]
        n_cols = max(len(r) for r in rows)
        header = header + [""] * (n_cols - len(header))
        named = [h or f"列{i+1}" for i, h in enumerate(header)]
        uniq = len(set(named))
        if uniq < max(2, n_cols * 0.6):
            named = [f"列{i+1}" for i in range(n_cols)]
        for idx, row in enumerate(rows[1:], start=2):
            pairs = []
            for i, val in enumerate(row):
                if val:
                    pairs.append(f"{named[i]}：{val}")
            if pairs:
                blocks.append(Block(loc=f"{ws.title}!行{idx}", text=" | ".join(pairs)))
    wb.close()
    return Doc(path=path, kind="excel", blocks=blocks)


def read_csv(path: Path) -> Doc:
    raw = path.read_bytes()
    text = None
    for enc in ("utf-8-sig", "utf-8", "gb18030", "big5"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = raw.decode("utf-8", "ignore")
    sample = text[:4096]
    delim = max([",", "\t", ";", "|"], key=sample.count) or ","
    reader = list(csv.reader(io.StringIO(text), delimiter=delim))
    rows = [[c.strip() for c in r] for r in reader if any(c.strip() for c in r)]
    blocks: list[Block] = []
    if rows:
        header = [h or f"列{i+1}" for i, h in enumerate(rows[0])]
        for idx, row in enumerate(rows[1:], start=2):
            pairs = [f"{header[i] if i < len(header) else f'列{i+1}'}：{v}" for i, v in enumerate(row) if v]
            if pairs:
                blocks.append(Block(loc=f"行{idx}", text=" | ".join(pairs)))
    return Doc(path=path, kind="csv", blocks=blocks)


def _pdf_pages(path: Path) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return pages


def _pdf_render_ocr(path: Path, workers: int = 4) -> list[str]:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(path))
    tmp = Path(tempfile.mkdtemp(prefix="xhs-ocr-"))
    imgs: list[Path] = []
    for i in range(len(pdf)):
        page = pdf[i]
        width = page.get_width()
        scale = max(1.5, 1700 / max(width, 1))
        pil = page.render(scale=scale).to_pil()
        p = tmp / f"p{i+1:04d}.png"
        pil.save(p)
        imgs.append(p)
    texts = ocr_images(imgs, workers=workers)
    out = [texts.get(str(p), "") for p in imgs]
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def read_pdf(path: Path, force_ocr: bool = False) -> Doc:
    pages = _pdf_pages(path) if not force_ocr else [""] * 1
    total = sum(len(p.strip()) for p in pages)
    need_ocr = force_ocr or (total / max(len(pages), 1) < 40)
    if need_ocr:
        pages = _pdf_render_ocr(path)
        used_ocr = True
    else:
        used_ocr = False
    pages = _strip_running_heads([_clean_text(p) for p in pages])
    blocks = [Block(loc=f"第{i+1}页", text=t) for i, t in enumerate(pages) if t.strip()]
    warning = ""
    if used_ocr and not blocks:
        warning = "扫描件 OCR 未识别到文字，建议提供更清晰的 PDF 或原始文件"
    return Doc(path=path, kind="pdf", blocks=blocks, ocr_used=used_ocr, warning=warning)


def read_docx(path: Path) -> Doc:
    import docx

    d = docx.Document(str(path))
    blocks: list[Block] = []
    for i, p in enumerate(d.paragraphs):
        t = p.text.strip()
        if t:
            blocks.append(Block(loc=f"段落{i+1}", text=t))
    for ti, table in enumerate(d.tables):
        for ri, row in enumerate(table.rows):
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                blocks.append(Block(loc=f"表格{ti+1}行{ri+1}", text=" | ".join(c for c in cells if c)))
    return Doc(path=path, kind="docx", blocks=blocks)


def read_text(path: Path) -> Doc:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", "ignore")
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return Doc(path=path, kind="text", blocks=[Block(loc=f"第{i+1}段", text=p) for i, p in enumerate(paras)])


def ingest_file(path: Path) -> Doc:
    suf = path.suffix.lower()
    if suf in (".xlsx", ".xlsm"):
        return read_excel(path)
    if suf == ".xls":
        return read_excel(_convert_with_soffice(path))
    if suf == ".csv":
        return read_csv(path)
    if suf == ".pdf":
        return read_pdf(path)
    if suf == ".docx":
        return read_docx(path)
    if suf == ".doc":
        return read_docx(_convert_with_soffice(path))
    if suf in (".md", ".txt"):
        return read_text(path)
    raise ValueError(f"不支持的格式: {suf}")


def collect(data_dir: Path) -> list[Path]:
    files = []
    for p in sorted(data_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in SUPPORTED and not p.name.startswith((".", "~$")):
            files.append(p)
    return files


def ingest_all(data_dir: Path, out_dir: Path, log=print) -> list[Doc]:
    files = collect(data_dir)
    if not files:
        raise SystemExit(f"{data_dir} 里没有找到可读资料（支持 {', '.join(sorted(SUPPORTED))}）")
    docs: list[Doc] = []
    dump = out_dir / "_ingest"
    dump.mkdir(parents=True, exist_ok=True)
    for f in files:
        try:
            d = ingest_file(f)
        except Exception as e:  # 单文件失败不阻断整批
            log(f"  ! {f.name} 解析失败: {e}")
            docs.append(Doc(path=f, kind=f.suffix.lstrip("."), warning=str(e)))
            continue
        docs.append(d)
        flag = " [OCR]" if d.ocr_used else ""
        log(f"  · {f.name}: {len(d.blocks)} 段 / {d.chars} 字{flag}")
        (dump / f"{f.stem}.md").write_text(d.as_text() or "(空)", encoding="utf-8")
    return docs
