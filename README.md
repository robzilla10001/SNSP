# SNSP - Switch Noob Software Pack

A Python script that builds/refreshes a Nintendo Switch homebrew SD payload from
a json config file. For each app it grabs the **latest GitHub release**, picks
the right asset, downloads it, extracts archives while **merging folders and
keeping the newest copy of any duplicated file**, and writes a manifest of titles
and versions. Note: this is my attempt to replace the HATS pack by Sthetix with a
known working pack (should always be up to date since you grab the packages your-
self with a few working config files thrown in) that doesn't have a boatload of
forked vanity projects. I completely understand forking projects to add/remove
features and make (what you may feel) are necessary adjustments, but I do not
agree with:
A.) forking a project just so you can slap your own name on it and
B.) forking a project and taking away user's choice.
Streamline if you want to (I have considered making a 'hekate lite', but who
asked for that?) but removing choice is where I draw a line in the sand.

## Files
- `switchpack.py` — the script
- `software.json` — editable list of apps, repos, and which asset to grab
- `MANIFEST.md` / `manifest.txt` — written into your output root after a run
- `_extra/atmosphere/config/system_settings.ini` — starter config for Atmosphere
- `_extra/bootloader/hekate_ipl.ini` — basic setup to get you booting right away, 
   can be edited as needed. Not a standard by any means, just a starting point.
- `_extra/bootloader/res` — icons for boot options.
- `_extra/switch/DBI/dbi.config` — basic DBI config to set basic defaults so
   screen is not turned off during FTP/MTP connection.
   
## Known Issues
- DBI indicates USB 2.0 speeds regardless of whether or not 3.0 is enabled;
  however, it appears that it is utilizing 3.0 speeds (I observed 30-50mbps
  transfers, whereas during 2.0 transfers I was getting low 20's).

## Requirements
- Python 3.8+ (uses only the standard library for `.zip` and `.tar*`)
- Optional, only if a release ships these formats:
  - `.7z` → `pip install py7zr` **or** the `7z` command (`p7zip-full`)
  - `.rar` → `unar`, `unrar`, or `7z` on your PATH

## Usage
### Recommended:
A token lifts GitHub's 60-requests/hour anonymous limit.
Not absolutely necessary, given the number of packages here, but if
you have to re-run the package in a short time period, it will assist.
```
python3 switchpack.py --out ./sdroot                                 # build everything into ./sdroot
GITHUB_TOKEN=ghp_inserttoken python3 switchpack.py --out ./sdroot    # utilize github token to download packages. 
python3 switchpack.py --out ./sdroot --dry-run                       # resolve + report, download nothing
python3 switchpack.py --out ./sdroot --only Atmosphere "DBI English" # download only Atmosphere and DBI English.
```
Re-running against an existing `--out` folder updates it in place (newest file wins),
so this doubles as an updater.

## How asset picking works (`software.json`)
Each app has one or more `downloads`, each with a `match` rule:
- `{"first": true}` — top asset under the release ("top link under assets")
- `{"index": N}` — the Nth asset, 0-based
- `{"name": "x.zip", "ext_fallback": true}` — exact filename (case-insensitive);```
  with `ext_fallback`, if that exact name is gone it falls back to the first asset
  with the same extension (survives version-number renames)
- `{"regex": "..."}` — regex against the asset name (used for the Hekate Nyx zip, etc.)

Other per-download options:
- `"dest_subdir"` — where a **non-archive** file is placed (e.g. `switch/.overlays`).
  Archives always extract+merge into the root and ignore this.
- `"strip_prefix"` — if a zip file extracts to any other folder than what is present on the root
   (i.e. it bundles all the folders needed in a parent folder called "SdOut"), this will strip
   the root folder name and dump the resultant folders out at the root. Supports / for multi-
   layer folders should they be an issue.
- `"rename"` — rename a non-archive file (used for DBI's `translation_en.bin` → `translation.bin`).
- `"rename-extracted"` — rename the result of a zip extraction, i.e. :
  "rename_extracted": [ ["hekate_ctcaer_*.bin", "payload.bin"] ]

## Notes / things to double-check
- **Placement defaults are conventional, not gospel.** Loose `.nro` files go to
  `switch/`, `.ovl` overlays to `switch/.overlays/`, DBI-EN to `switch/DBI/` as
  specified in software.json. 
- **"Keep newest" uses each file's stored modification time** inside the archive.
  That's the best per-file signal available; a few projects set odd build timestamps,
  so if a specific file ever loses out unexpectedly, that's why.
- If an asset name has drifted, the script prints the available asset names in the
  error so you can fix that one line in `software.json` quickly.

## Future
- **Possible GUI wrapper** for less technically inclined users. Will simply have an
  output field, a github token field, and a dry-run optional check box. Nothing flashy,
  and will remain platform agnostic.
