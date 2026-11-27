# Download and re-assemble the ISO

The Aequalyn ISO is **~6.5 GiB**, and GitHub Releases cap **each file at 2 GiB**.
So it isn't shipped as one download. On the
[aequalyn-iso releases page](https://github.com/Aequalyn/aequalyn-iso/releases)
the ISO is **split into 4 raw parts**, each under 2 GiB, plus a checksum:

```
aequalyn-YYYY.MM.DD-x86_64.iso.001
aequalyn-YYYY.MM.DD-x86_64.iso.002
aequalyn-YYYY.MM.DD-x86_64.iso.003
aequalyn-YYYY.MM.DD-x86_64.iso.004
aequalyn-YYYY.MM.DD-x86_64.iso.sha256      (SHA-256 checksum; a GPG .sig may also be attached)
```

## What the `.001 / .002 / .003 / .004` parts are — read this first

These are **raw byte ranges** of the original `.iso`, split with 7-Zip
*Split file* (or `split`). They are **not** four separate `.zip` files, and
**each part cannot be extracted on its own**. You **concatenate them back in
order** to get the original ISO byte-for-byte. Nothing is renamed or removed;
just put all four in one folder and keep their names.

> **WinRAR / WinZip / 7-Zip — what each can do.**
> **7-Zip** (free, Windows + Linux) can both split and re-combine raw `.001`
> parts (*Tools → Combine files*), **and** extract ordinary archives.
> **WinRAR** and **WinZip** *extract archives*, but they **cannot** unpack a
> raw `.001` byte-split — those need concatenation (`copy /b`, `cat`, or
> 7-Zip *Combine*). WinRAR only opens its own `.part1.rar` volumes and
> WinZip only its own `.z01` spanned-ZIP volumes. So for these `.001`
> parts: **7-Zip or the built-in commands below; not WinRAR/WinZip.**
> You don't strictly need any archiver at all — Windows `copy /b` and
> Linux/macOS `cat` are enough.

## Windows

Download all four `.001 … .004` parts into the **same folder**, then in that
folder:

### A. No extra software (Command Prompt)

```bat
copy /b aequalyn-2026.11.26-x86_64.iso.001 + aequalyn-2026.11.26-x86_64.iso.002 + aequalyn-2026.11.26-x86_64.iso.003 + aequalyn-2026.11.26-x86_64.iso.004 aequalyn-2026.11.26-x86_64.iso
```

`/b` = binary mode; parts are joined **in order** (`.001`, `.002`, `.003`,
`.004`). The `.iso` is created next to the parts.

### B. No extra software (PowerShell)

```powershell
$name = "aequalyn-2026.11.26-x86_64.iso"
$out = [System.IO.File]::Create("$PWD\$name")
1..4 | ForEach-Object {
  $in = [System.IO.File]::OpenRead("$PWD\$name.{0:000}" -f $_); $in.CopyTo($out); $in.Dispose()
}
$out.Close()
```

### C. 7-Zip (if installed)

*Tools → Combine files*, select `…iso.001`, output `aequalyn-…-x86_64.iso`.
Or use 7-Zip to split yourself: `7z a -v1900m out.7z aequalyn.iso` makes
`.7z.001…` archive volumes instead, which **7-Zip extracts** directly (a
different format from these raw `.001` parts).

### Verify

```bat
CertUtil -hashfile aequalyn-2026.11.26-x86_64.iso SHA256
```
or in PowerShell `Get-FileHash aequalyn-2026.11.26-x86_64.iso -Algorithm SHA256`,
and compare with `aequalyn-2026.11.26-x86_64.iso.sha256`. If a GPG `.sig` is
attached, `gpg --verify aequalyn-…-x86_64.iso.sig aequalyn-…-x86_64.iso`.

## Linux / macOS

```sh
cd ~/Downloads
# concatenate in order; do not glob blindly past .004
cat aequalyn-2026.11.26-x86_64.iso.001 aequalyn-2026.11.26-x86_64.iso.002 \
    aequalyn-2026.11.26-x86_64.iso.003 aequalyn-2026.11.26-x86_64.iso.004 \
    > aequalyn-2026.11.26-x86_64.iso
sha256sum -c aequalyn-2026.11.26-x86_64.iso.sha256      # must print "OK"
# optional signature check
gpg --verify aequalyn-2026.11.26-x86_64.iso.sig aequalyn-2026.11.26-x86_64.iso
```

7-Zip on Linux can also `7z x` a 7-Zip-volume set, but for raw `.001` parts
`cat` (above) is what reassembles the ISO.

## Then

Once `sha256sum`/`CertUtil`/`Get-FileHash` matches, you have one ISO. Write it
to a USB stick (e.g. **Ventoy**, `dd`, `Rufus`, `gnome-disks`, **Startup Disk
Creator**, `Fedora Media Writer`) and boot it. See
[Install from the ISO](/docs/install/) and
[The live session](/docs/live-session/).

**Checksum vs signature.** The `.sha256` confirms the re-assembled ISO is
byte-identical to what was published (integrity); a GPG `.sig`/`.asc`
additionally proves it came from Aequalyn (authenticity). Verify *after*
re-assembling, not the individual parts.
