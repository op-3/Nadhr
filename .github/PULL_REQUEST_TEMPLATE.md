## What and why

## How it was verified

<!-- Commands you ran, builds, tests, measurements. Unverified claims will be questioned. -->

## Checklist

- [ ] `python devutils/validate_patches.py --remote` passes (if patches changed)
- [ ] No weakening of sandbox, Site Isolation, certificate or extension isolation
- [ ] New network requests (if any) are documented in docs/PRIVACY.md
- [ ] docs/DEVELOPMENT_STATUS.md / KNOWN_LIMITATIONS.md updated if status changed
