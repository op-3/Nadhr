# Release process

No release has been published yet.

## Versioning

`<chromium version>-<nadhr revision>`, for example `158.0.8127.88-1`. The Nadhr
revision (`revision.txt`) resets to 1 on each new Chromium version and is bumped
for Nadhr-only changes. Git tags are `v<version>`.

## Checklist

1. `validate` CI is green on `main`.
2. `CHANGELOG.md` has an entry for the version.
3. Tag `v<version>` and push it. `build-windows` (and later the other platform
   builds) produce the packages.
4. Download the artifacts and install them on a clean machine: launch, open
   pages, check `nadhr://version`, uninstall.
5. Sign the installers (when certificates are available), then compute SHA-256 checksums.
6. Create a GitHub Release with the packages, checksums, SBOM and the known
   limitations for this version. Releases are marked **pre-release** until the
   acceptance criteria in [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) are met.

## Signing

| Platform | Mechanism | Status |
|---|---|---|
| Windows | Authenticode | needs a code-signing certificate (human dependency) |
| macOS | Developer ID + notarization | needs an Apple Developer account (human dependency) |
| Linux | GPG-signed repository metadata and checksums | key to be created and stored offline |

Unsigned builds are labelled as unsigned in the release notes.
