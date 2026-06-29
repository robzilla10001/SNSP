#!/usr/bin/env python3
"""
switchpack.py - Build/refresh a Nintendo Switch homebrew SD payload from a config.

For each entry in software.json it:
  1. Looks up the LATEST GitHub release.
  2. Selects the right release asset(s) per the 'match' rule.
  3. Downloads them into the output root.
  4. Extracts archives (.zip/.7z/.rar/.tar*) and MERGES the contents into the root,
     keeping only the NEWEST copy when two files share the same path.
  5. Writes MANIFEST.md (and manifest.txt) listing each title + version.

Re-running updates an existing folder in place (newest-wins merge).

Usage:
    python3 switchpack.py --out ./sdroot
    GITHUB_TOKEN=ghp_xxx python3 switchpack.py --out ./sdroot   # avoids API rate limits
    python3 switchpack.py --out ./sdroot --only Atmosphere "DBI English"
    python3 switchpack.py --out ./sdroot --dry-run

External tools are optional:
  - .zip and .tar* need nothing (Python stdlib).
  - .7z uses the 'py7zr' pip package if installed, else the '7z'/'7za' command.
  - .rar uses 'unar', 'unrar', or '7z' if any is on PATH.
"""

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
import tarfile
from pathlib import Path

API = "https://api.github.com"
ARCHIVE_TAR_SUFFIXES = (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz", ".tar.zst")


# ----------------------------------------------------------------------------- helpers
def log(msg, *, err=False):
    print(msg, file=(sys.stderr if err else sys.stdout), flush=True)


def http_json(url, token=None):
    req = urllib.request.Request(url, headers=_headers(token, json=True))
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def _headers(token, json=False):
    h = {"User-Agent": "switchpack/1.0", "Accept":
         "application/vnd.github+json" if json else "application/octet-stream"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def is_archive(name):
    n = name.lower()
    return n.endswith((".zip", ".7z", ".rar")) or n.endswith(ARCHIVE_TAR_SUFFIXES)


# ----------------------------------------------------------------------------- GitHub
def get_latest_release(repo, token):
    """Latest published (non-draft) release. Falls back to most recent of /releases
    if the repo only ships pre-releases (so /releases/latest 404s)."""
    try:
        return http_json(f"{API}/repos/{repo}/releases/latest", token)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            rels = http_json(f"{API}/repos/{repo}/releases", token)
            rels = [r for r in rels if not r.get("draft")]
            if not rels:
                raise RuntimeError("no releases found")
            return rels[0]
        if e.code == 403 and "rate limit" in (e.read().decode("utf-8", "ignore").lower()):
            raise RuntimeError("GitHub API rate limit hit - set GITHUB_TOKEN to raise it")
        raise


def select_assets(assets, match):
    """Return a list of asset dicts matching the rule. Raises if nothing matches."""
    names = [a["name"] for a in assets]
    if not assets:
        raise RuntimeError("release has no assets")

    if match.get("first"):
        return [assets[0]]
    if "index" in match:
        i = match["index"]
        if i >= len(assets):
            raise RuntimeError(f"index {i} out of range; assets={names}")
        return [assets[i]]
    if "regex" in match:
        pat = re.compile(match["regex"])
        hits = [a for a in assets if pat.search(a["name"])]
        if hits:
            return [hits[0]]
        raise RuntimeError(f"regex {match['regex']!r} matched nothing; assets={names}")
    if "name" in match:
        want = match["name"].lower()
        hits = [a for a in assets if a["name"].lower() == want]
        if hits:
            return [hits[0]]
        if match.get("ext_fallback"):
            ext = os.path.splitext(want)[1]
            hits = [a for a in assets if a["name"].lower().endswith(ext)]
            if hits:
                log(f"      note: exact '{match['name']}' not found; "
                    f"falling back to '{hits[0]['name']}' by extension")
                return [hits[0]]
        raise RuntimeError(f"name {match['name']!r} not found; assets={names}")
    raise RuntimeError(f"unrecognized match rule: {match}")


def download(url, dest_path, token, dry=False):
    if dry:
        log(f"      [dry-run] would download -> {dest_path}")
        return
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=_headers(token))
    with urllib.request.urlopen(req, timeout=300) as r, open(dest_path, "wb") as f:
        shutil.copyfileobj(r, f, length=1024 * 256)


# ----------------------------------------------------------------------------- extract
def extract_archive(archive_path, dest_dir):
    """Extract any supported archive into dest_dir, preserving internal mtimes."""
    name = archive_path.name.lower()
    if name.endswith(".zip"):
        _extract_zip(archive_path, dest_dir)
    elif name.endswith(ARCHIVE_TAR_SUFFIXES):
        with tarfile.open(archive_path) as t:
            _safe_tar_extract(t, dest_dir)
    elif name.endswith(".7z"):
        _extract_7z(archive_path, dest_dir)
    elif name.endswith(".rar"):
        _extract_rar(archive_path, dest_dir)
    else:
        raise RuntimeError(f"don't know how to extract {archive_path.name}")


def _within(base, target):
    base = os.path.realpath(base)
    target = os.path.realpath(target)
    return target == base or target.startswith(base + os.sep)


def _extract_zip(path, dest):
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            out = os.path.join(dest, info.filename)
            if not _within(dest, out):
                raise RuntimeError(f"unsafe path in zip: {info.filename}")
            if info.is_dir():
                os.makedirs(out, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with z.open(info) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
            # preserve stored mtime so "newest wins" is meaningful
            ts = time.mktime(info.date_time + (0, 0, -1))
            os.utime(out, (ts, ts))


def _safe_tar_extract(tar, dest):
    for m in tar.getmembers():
        out = os.path.join(dest, m.name)
        if not _within(dest, out):
            raise RuntimeError(f"unsafe path in tar: {m.name}")
    tar.extractall(dest)  # tarfile preserves mtimes


def _extract_7z(path, dest):
    try:
        import py7zr
        with py7zr.SevenZipFile(path, "r") as z:
            z.extractall(path=dest)
        return
    except ImportError:
        pass
    for exe in ("7z", "7za", "7zr"):
        if shutil.which(exe):
            subprocess.run([exe, "x", "-y", f"-o{dest}", str(path)],
                           check=True, stdout=subprocess.DEVNULL)
            return
    raise RuntimeError(".7z needs the 'py7zr' pip package or the '7z' command")


def _extract_rar(path, dest):
    if shutil.which("unar"):
        subprocess.run(["unar", "-quiet", "-force-overwrite", "-output-directory",
                        str(dest), str(path)], check=True)
        return
    if shutil.which("unrar"):
        subprocess.run(["unrar", "x", "-y", str(path), str(dest) + "/"], check=True,
                       stdout=subprocess.DEVNULL)
        return
    if shutil.which("7z"):
        subprocess.run(["7z", "x", "-y", f"-o{dest}", str(path)], check=True,
                       stdout=subprocess.DEVNULL)
        return
    raise RuntimeError(".rar needs 'unar', 'unrar', or '7z' on PATH")


# ----------------------------------------------------------------------------- merge
def merge_tree(src_root, dst_root, stats):
    """Move every file from src_root into dst_root. On a path collision keep the file
    with the newer mtime. Identically-named folders merge by recursion (via path)."""
    src_root = Path(src_root)
    dst_root = Path(dst_root)
    for src in src_root.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        place_file(src, dst, stats)


def place_file(src, dst, stats):
    """Copy/replace a single file at dst using newest-wins. src may be outside a tree."""
    src = Path(src)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if src.stat().st_mtime > dst.stat().st_mtime:
            shutil.copy2(src, dst)
            stats["replaced"] += 1
        else:
            stats["kept_existing"] += 1
    else:
        shutil.copy2(src, dst)
        stats["added"] += 1


# ----------------------------------------------------------------------------- main flow
def process_entry(entry, out_root, token, stats, dry=False):
    name = entry["name"]
    repo = entry["repo"]
    log(f"==> {name}  ({repo})")
    rel = get_latest_release(repo, token)
    version = rel.get("tag_name") or rel.get("name") or "unknown"
    assets = rel.get("assets", [])
    record = {"name": name, "repo": repo, "version": version,
              "published": (rel.get("published_at") or "")[:10], "files": []}

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for dl in entry["downloads"]:
            picked = select_assets(assets, dl["match"])
            for asset in picked:
                aname = asset["name"]
                url = asset["browser_download_url"]
                a_mtime = _asset_mtime(asset)
                local = tmp / aname
                log(f"    - {aname}  ({version})")
                download(url, local, token, dry=dry)
                record["files"].append(aname)
                if dry:
                    continue
                os.utime(local, (a_mtime, a_mtime))

                if is_archive(aname):
                    ex = tmp / (aname + "__x")
                    ex.mkdir()
                    extract_archive(local, ex)
                    src = ex / dl["strip_prefix"] if dl.get("strip_prefix") else ex
                    if not src.is_dir():
                        raise RuntimeError(f"strip_prefix {dl['strip_prefix']!r} not found in {aname}; "
                                           f"top level = {[p.name for p in ex.iterdir()]}")
                    for pat, new_name in dl.get("rename_extracted", []):
                        matches = list(src.rglob(pat))
                        if not matches:
                            raise RuntimeError(f"rename_extracted pattern {pat!r} matched nothing in {aname}")
                        for m in matches:
                            m.rename(m.with_name(new_name))
                    merge_tree(src, out_root, stats)
                else:
                    final_name = dl.get("rename", aname)
                    sub = dl.get("dest_subdir", ".")
                    place_file(local, Path(out_root) / sub / final_name, stats)
    return record


def _asset_mtime(asset):
    ts = asset.get("updated_at") or asset.get("created_at")
    if not ts:
        return time.time()
    try:
        return dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=dt.timezone.utc).timestamp()
    except ValueError:
        return time.time()


def write_manifest(records, out_root):
    out_root = Path(out_root)
    today = dt.date.today().isoformat()
    md = [f"# Switch Homebrew Manifest", f"_Generated {today}_", ""]
    md.append("| Software | Version | Released | Files |")
    md.append("|---|---|---|---|")
    for r in sorted(records, key=lambda x: x["name"].lower()):
        files = ", ".join(r["files"]) if r["files"] else "-"
        md.append(f"| {r['name']} | {r['version']} | {r['published'] or '-'} | {files} |")
    (out_root / "MANIFEST.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    txt = [f"Switch Homebrew Manifest - generated {today}", ""]
    for r in sorted(records, key=lambda x: x["name"].lower()):
        txt.append(f"{r['name']}: {r['version']}")
    (out_root / "manifest.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Build a Switch homebrew SD payload.")
    ap.add_argument("--config", default=str(Path(__file__).with_name("software.json")))
    ap.add_argument("--out", required=True, help="output root folder (your SD root)")
    ap.add_argument("--only", nargs="*", help="process only these software names")
    ap.add_argument("--dry-run", action="store_true", help="resolve+report, download nothing")
    ap.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"),
                    help="GitHub token (or set GITHUB_TOKEN) to avoid rate limits")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    software = cfg["software"]
    if args.only:
        wanted = {s.lower() for s in args.only}
        software = [e for e in software if e["name"].lower() in wanted]
        if not software:
            log("nothing matched --only", err=True)
            sys.exit(2)

    out_root = Path(args.out).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    if not args.token:
        log("warning: no GITHUB_TOKEN set - this many repos may exceed the 60/hr "
            "anonymous API limit. Export GITHUB_TOKEN to be safe.\n", err=True)

    stats = {"added": 0, "replaced": 0, "kept_existing": 0}
    records, failures = [], []
    for entry in software:
        try:
            records.append(process_entry(entry, out_root, args.token, stats, dry=args.dry_run))
        except Exception as e:  # keep going; report at the end
            log(f"    !! FAILED: {entry['name']}: {e}", err=True)
            failures.append((entry["name"], str(e)))

    if not args.dry_run and records:
        write_manifest(records, out_root)
        log(f"\nManifest written to {out_root/'MANIFEST.md'}")

    log(f"\nDone. files added={stats['added']} replaced={stats['replaced']} "
        f"kept(existing newer)={stats['kept_existing']}")
    if failures:
        log(f"{len(failures)} item(s) failed:", err=True)
        for n, e in failures:
            log(f"  - {n}: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
