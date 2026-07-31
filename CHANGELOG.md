# Changelog

## v1 cleanup candidate

### Added

- Deterministic Raspberry Pi hardware emulation for relays, scales, pressure, and RTD inputs.
- Hardware contract, startup-selection, configuration, and HMI component tests.
- Dedicated configuration loader with explicit error reporting.
- Focused v2 identifier-state and filtration-dialog components.
- Emulated HMI launcher and Raspberry Pi display instructions.

### Changed

- Reduced `hmi_v2_integrated.py` to a compact production composition point.
- Consolidated Test and Post-Scrub settings-dialog construction.
- Isolated v2 identifier synchronization from older HMI compatibility traces.
- Simplified `system_control.py` while preserving its public compatibility exports and production command.

### Preserved

- Current Tkinter UI layout, colors, sizing, labels, navigation, and process-tab order.
- Flush, Benchmark, Test, Post-Scrub, and Clean workflows.
- Existing configuration keys, hardware mappings, serial ports, and public imports.
- Production hardware as the default startup backend.

### Validation required before merge

- Full `unittest` suite on the Raspberry Pi display.
- `compileall` across the production tree.
- Visual comparison of every process tab and settings dialog.
- Physical relay, instrument, scale, USB export, and wet-process checks.
