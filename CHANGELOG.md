# Changelog

## v1 cleanup candidate

### Added

- Deterministic Raspberry Pi hardware emulation for relays, scales, pressure, and RTD inputs.
- Hardware contract, startup-selection, configuration, HMI component, hardware-factory, and data-logging tests.
- Dedicated configuration loader with explicit error reporting.
- Dedicated CSV schema and sensor-row construction module.
- Focused v2 identifier-state and filtration-dialog components.
- Emulated HMI launcher and Raspberry Pi display instructions.

### Changed

- Reduced `hmi_v2_integrated.py` to a compact production composition point.
- Consolidated Test and Post-Scrub settings-dialog construction.
- Isolated v2 identifier synchronization from older HMI compatibility traces.
- Simplified `system_control.py` while preserving its public compatibility exports and production command.
- Removed duplicated production hardware initialization from `hardware_runtime.py`.
- Added explicit scale-manager and relay-wrapper factory hooks to the base hardware interface.
- Centralized scale selection, Multi-IO creation, CSV headers, pressure conversion, and sensor-row construction.
- Split filtration phase selection and progress reporting into focused automation methods.

### Preserved

- Current Tkinter UI layout, colors, sizing, labels, navigation, and process-tab order.
- Flush, Benchmark, Test, Post-Scrub, and Clean workflows.
- Existing configuration keys, hardware mappings, serial ports, and public imports.
- Production hardware as the default startup backend.
- Runtime Highland scale tare command, verification timing, controlled print fallback, and dual-scale failure behavior.
- Existing CSV column order and kPa conversion factor.

### Validation required before merge

- Full `unittest` suite on the Raspberry Pi display.
- `compileall` across the production tree.
- Visual comparison of every process tab and settings dialog.
- Physical relay, instrument, scale, USB export, and wet-process checks.
