"""把一次运行的产物打成 zip，供浏览器下载。用法：python zip_run.py <runDir> <zipPath>"""
import os
import sys
import zipfile


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: zip_run.py <runDir> <zipPath>")
        return 2
    run_dir, zip_path = sys.argv[1], sys.argv[2]
    base = os.path.basename(os.path.normpath(run_dir))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(run_dir):
            dirs[:] = [d for d in dirs if d not in {"_ingest", "data", ".git", "__pycache__"}]
            for name in files:
                if name.endswith((".pyc", ".zip")):
                    continue
                full = os.path.join(root, name)
                rel = os.path.relpath(full, run_dir)
                zf.write(full, os.path.join(base, rel))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
