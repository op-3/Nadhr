# Performance

**No Nadhr performance measurements exist yet.** This document defines how
they will be made. Results will be added only from real runs.

## Approach

1. Start from upstream's optimised build: official build, ThinLTO, and PGO
   (`chrome_pgo_phase=2` with Chromium's profiles; the git-clone build path keeps
   them).
2. Use Chromium's existing mechanisms before writing new ones: Memory Saver and
   tab discarding, tab freezing, background timer throttling, the
   memory-pressure monitor, and the battery saver.
3. The **Adaptive Resource Engine** is a policy layer over those mechanisms. It
   picks discard and freeze thresholds and throttling from available RAM,
   memory pressure, battery state and tab activity. Modes: Adaptive (default),
   Ultra Lightweight, Balanced, Performance.
4. It never discards a tab that is playing audio, in a call or capture,
   downloading, or holding unsaved form input. These are the same protections
   Chromium's `TabLifecycleUnit` applies, kept in every mode.
5. A change that regresses the benchmark suite must be fixed or redesigned
   before release.

## Benchmark methodology (planned)

- **Browsers:** Nadhr, Google Chrome, Microsoft Edge, Helium, and
  ungoogled-chromium at the same Chromium version as Nadhr.
- **Machines:** 4 GB, 8 GB and 16 GB RAM configurations. Hardware, OS build,
  power plan and background load are recorded for each run.
- **Workloads:** cold and warm start (time to first paint of `about:blank`);
  new tab latency; Speedometer 3; private working set with 1, 10, 30 and 100
  tabs from a fixed site list; idle CPU over 10 minutes; video playback CPU;
  WebRTC call CPU; session restore time; an 8-hour mixed session for growth;
  battery drain where measurable.
- **Method:** fresh profile per run, at least 5 runs, report median and spread.
  Extensions off unless a test is about them. Raw data committed under `benchmarks/`.
