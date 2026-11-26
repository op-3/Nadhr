# Roadmap

Stages are dependency-ordered engineering milestones toward one complete
product, not separate reduced releases. Status lives in
[DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md).

1. **Foundation:** pinned upstream, patch system, Windows build pipeline,
   first working Nadhr build launched and smoke-tested.
2. **Identity and interface:** complete branding (strings, icons, `nadhr://`
   scheme), the Classic, Modern and Focus layouts with live switching,
   appearance settings, onboarding, Arabic/English localization with RTL.
3. **Privacy and security:** bundled full uBlock Origin, privacy defaults,
   a phishing/malware protection replacement for Safe Browsing, permissions.
4. **Performance:** Adaptive Resource Engine, Performance Center, measured
   benchmarks.
5. **Browsing features:** workspaces, split view, command bar (Ctrl+K),
   profiles, downloads, extensions.
6. **Enterprise and government:** Nadhr policies, ADMX templates, deployment
   and hardening guides, restricted-network support.
7. **Optional encrypted sync:** self-hostable, opt-in, independently reviewed
   before any end-to-end encryption claim.
8. **Cross-platform:** Linux (portable and packages) and macOS builds, tested natively.
9. **Release engineering:** signed installers, secure updater, GitHub Releases.
10. **Final verification:** full functional, security, performance and
    platform test pass against [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md).

## Dependencies on people or paid services

These cannot be completed by automation alone and will be requested when needed:

- Windows Authenticode code-signing certificate.
- Apple Developer Program membership (macOS signing and notarization).
- Hardware or virtual machines for 4 GB / 8 GB / 16 GB benchmark environments.
- An independent security review before claiming end-to-end encrypted sync.
