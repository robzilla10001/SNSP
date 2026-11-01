<div align="center">IMPORTANT NOTICE  
  
16/10/2026: ATMOSPHERE 1.12.1 FOR HOS 23.0.1 RELEASED  

Atmosphere has been updated; BornToHonk's fork released with baked in sigpatches.</div>

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
asked for that?) but removing choice is where I draw a line in the sand. NOTE: Yes,
I am forking KitNX to remove TinFoil related patches. This is not to remove user's
choice, but A.) to ensure package3 remains in a known state for troubleshooting
purposes and B.) to stop kicking the can down the road on Tinfoil. It is no longer
supported by it's authors, it is being propped up by community patching efforts,
and it is no longer relevant with the advent of CyberFoil and similar alternatives.

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
  transfers, whereas during 2.0 transfers I was getting low 20's; this
  appears to be intermittent, dependent on DBI version).

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

## Contents  
The applications that are downloaded in this pack are as listed below:  
- `Atmosphere` - BornToHonk: CFW, fork that has patches baked in
- `Hekate+Nyx` - CTCaer: Bootloader and GUI
- `UltraHand` - ppkantorski: A fully scriptable overlay menu ecosystem
- `CyberFoil` - luketanti: 'Shop' software
- `DBI (RU)` - duckbill/rashevskyv: Title management, software installer, system tools
- `DBI (EN)` - rashevskyv: Unofficial translation of DBI
- `JKSV` - J-D-K: Save file management
- `Linkalho` - impeeza: Link NNID accounts offline
- `NXThemeInstaller` - exelixll: Install Homemenu themes
- `Sphaira` - Homebrew Menu replacement with vastly improved feature set
- `Switch90DNSTester` - meganukebmp: Tests DNS to see if Nintendo Servers are blocked
- `Mission Control` - ndeadly: facilitates pairing of any bluetooth controller
- `MC ExeFS Patches` - ndeadly: System patches to improve Mission Control functionality
- `SaltyNX` - masagrator: Sysmodule for injecting custom codes into retail games
- `Nx-ovlloader` - ppkantorski: Core loader sysmodule of the Ultrahand overlay ecosystem
- `FuseCheck` - sthetix: Payload that checks your console's burnt fuse count
- `Lockpick RCM Pro` - sthetix: Payload that extracts encryption keys and dumps PRODINFO
- `KitNX` - sthetix: All-in-one bare-metal maintenance and recovery payload (see [future](#future))
- `TegraExplorer Ext` - sthetix: Payload-based file explorer
- `Modchip Toolbox` - DefenderOfHyrule: Payload to manage modchips
- `Edizon` - proferabg: Cheat overlay for UltraHand
- `FPSLocker` - ppkantorski: An overlay that allows you to set custom display refresh rate and FPS
- `QuickNTP` - ppkantorski: Update your clock using a list of NTP servers
- ~~`HorizonOC` - Horizon-OC: An open-source overclocking tool~~
- `Emuiibo` - XorTroll: Amibo emulation
- `Sys-tune` - ppkantorski: Background audio player with UltraHand overlay

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
  
## Changelog  
### v1.3.3  
- **Removed line from hekate_ipl.ini that prevented boot in some cases.** Seems
  it was leftover from Horizon-OC install. Not their fault, mine. Cleanup can be
  tricky sometimes.
### v1.3.2
- **Removed Horizon-OC.** Issues with HOC's KIP caused one of my test units to
  fail to load software titles or NRO's, whether as forwarders or through the
  HBmenu/Sphaira. Unfortunately, no crash_reports are generated, so I can't
  attempt to track down the issue. For now, in the spirit of making sure I'm
  not sharing software that could potentially cause loss of functionality, I'm
  keeping it out. If you want it, you can always grab it and drop it in manually.
- **Dropped Disable Remap Dialog.** Superseded by MC ExeFS Patches, which adds new
  features.
- **Dropped NetMan.** Superseded by KitNX, which adds new features.
- **Added GoldLeaf.** Some users prefer it to other title management software. Was
  going to leave it off as there are already a few different title managers on this
  list, but decided to include it for completeness for the users who prefer it.
### v1.3.1  
- **Commented out HOC Kip reference.** HOC related kip1 line in hekate_ipl.ini called
  an out of date HOC. It has been commented out until the project is updated.  
### v1.3
- **Dropped sys-patch.** BornToHonk's Atmosphere fork has patches built in, no need for
  redundancy.
- **Fixed Sphaira entry.** Sphaira now packages full folder hierarchy rather than bare
  nro. JSON modified to correctly extract and place contents.]

## Future
- **Possible GUI wrapper** for less technically inclined users. Will simply have an
  output field, a github token field, and a dry-run optional check box. Nothing flashy,
  and will remain platform agnostic.
- **Fork of KitNX** to remove unnecessary TinFoil related compatibility patches.
  CyberFoil natively supports latest firmwares without the need to patch package3.
- **GarageNX** is my own personal title management software. A lot of people are
  wary of using DBI based on some comments made by the author, so I have attempted
  to create an application that has feature parity with DBI. This will be included
  in a future release, once the feature set is fully locked (working on
  improvements currently) and testing is complete. Will not be included until I am
  satisfied that it meets the standards set by the other software featured in this
  package.

## Thanks  
- borntohonk - Atmosphere fork with patches integrated  
- CTCaer - Hekate  
- luketanti - CyberFoil  
- rashevsky / duckbill - DBI  
- J-D-K - JKSV  
- impeeza - linkalho  
- elelix11 - NXThemeInstaller  
- NaGaa95 - Sphaira  
- meganukebmp - Switch90DNSTester  
- ndeadly - MC ExeFS Patches / MissionControl  
- masagrator - SaltyNX  
- ppkantorski - NX-ovlloader / FPSLocker / QuickNTP / Ultrahand / Sys-tune  
- sthetix - FuseCheck / Lockpick RCM Pro / KitNX / TegraExplorer-Ext  
- DefenderOfHyrule - Modchip Toolbox  
- proferabg - EdiZon  
- Horizon-OC - Horizon-OC  
- XorTroll - Emuiibo
- AvengedClippyFold - discovered source of bluescreen on emuMMC with combination of Atmosphere 1.12.0 and Horizon-OC 2.5.1
