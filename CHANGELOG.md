# Changelog

## MEU architecture cleanup candidate

### Added

- Deterministic Raspberry Pi hardware emulation for relays, scales, pressure, and RTD inputs.
- Explicit emulation selection through `MEU_EMULATE_RPI=1` while preserving production hardware as the default.
- Focused configuration loading, process lifecycle, Clean sequence, CSV schema, log ownership, and completed-result discovery modules.
- Focused HMI components for shared identifiers, filtration dialogs, summary formatting, touchscreen entries, and generic widget-tree cloning.
- Passive serial transport separated from Highland scale protocol handling.
- Regression coverage for hardware contracts, startup selection, configuration compatibility, process sequencing, logging, HMI composition, completed-run file selection, serial transport, and Highland protocol behavior.

### Changed

- Reduced `system_control.py` to production startup, configuration loading, and backend selection.
- Reduced `hmi_v2_integrated.py` to the final production composition point.
- Consolidated Test and Post-Scrub settings-dialog construction.
- Synchronized Project, Module ID, and Sample ID across applicable process tabs.
- Removed duplicate summary-formatting methods from the Test-layout clone layer.
- Extracted generic Tk cloning mechanics from MEU-specific Flush and Post-Scrub policy.
- Consolidated shared automation startup and guaranteed shutdown behavior.
- Replaced the duplicated Clean implementation with one authoritative immutable sequence.
- Consolidated automation CSV file creation, settings snapshots, and ownership.
- Made completed-run result discovery prefer the exact files owned by the completed automation.
- Reduced `hardware.py` to relay, Multi-IO, sensor conversion, and scale-manager composition.
- Moved serial connection handling into `serial_transport.py`.
- Moved Highland parsing, cached readings, protocol commands, and base tare behavior into `highland_scale.py`.
- Retained production-specific `T` tare verification and concurrent dual-scale safeguards in `hardware_runtime.py`.
- Removed obsolete HMI wrapper modules and the duplicate emulation launcher script.

### Preserved

- Current Tkinter UI layout, colors, sizing, labels, navigation, and process-tab order.
- Flush, Benchmark, Test, Post-Scrub, and Clean workflows.
- Existing configuration keys and legacy constructor aliases.
- Final relay and valve mapping.
- Pressure, RTD, and serial-port mappings.
- Production hardware as the default startup backend.
- Runtime Highland `T\r\n` tare command, two-reading verification, ±0.2 g tolerance, controlled `P\r\n` fallback, and dual-scale failure behavior.
- Existing CSV column order and kPa conversion factor.
- Public `MEU`, `PencilModule`, HMI, automation, and internal `_ScaleManager` compatibility imports.

### Automated validation completed

- 113 total tests completed successfully on the Raspberry Pi, with one intentional full-Tk display test skipped.
- `python -m compileall system_control.py pencil` completed successfully.

### Physical validation required before merge

- Visual comparison of every process tab and settings dialog.
- Physical Highland scale communication and verified tare on both ports.
- Relay and final valve mapping.
- Pressure and RTD channel readings.
- USB result export.
- Complete Flush, Benchmark, Test, Post-Scrub, and Clean wet-process checks.
