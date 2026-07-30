# MEU v1 Release Notes

## Release scope

This release stabilizes the Raspberry Pi control application for the MF/UF Membrane Evaluation Unit while preserving the existing hardware mappings, automation sequences, public imports, HMI inheritance structure, and diagnostic launch commands.

## Supported production entry point

```bash
python3 system_control.py
```

## Hardware-independent validation

```bash
python3 -m unittest discover -s tests
python3 -m compileall system_control.py pencil scripts
```

The test suite covers simulated hardware, automation sequences, cycle logging, configuration loading, HMI callback behavior, valve-button synchronization, settings-dialog valve lockout, shared identifiers, summary truncation, and application startup.

## Configuration behavior

A missing `config.json` still uses built-in defaults. Malformed JSON, permission or read errors, and a top-level JSON value that is not an object now produce a clear startup error.

## Pressure units

The pressure transmitters and calibration offsets retain their approved 0 to 30 psi hardware scaling. User-facing pressure values are converted to kPa:

- HMI sensor panels display kPa.
- PFD pressure readings display kPa.
- New CSV files use `feed_tank_pressure_kpa` and `backwash_tank_pressure_kpa`.

The conversion factor is 1 psi = 6.894757293168 kPa.

## Touchscreen and settings behavior

- Valve-button active colors remain synchronized with valve state.
- Test, Benchmark, and Clean settings dialogs use larger controls.
- Valve buttons are disabled while any settings dialog is open.
- Project and Module ID synchronize across all three tabs.
- Sample ID synchronizes between Test and Benchmark.
- Long identifiers are shortened with `...` in the compact summary without changing the complete stored or logged value.

## Final approved I/O mapping

### Valves

- SV-01, Relay 1, Backwash Supply
- SV-02, Relay 2, Feed Supply
- SV-03, Relay 3, Backwash Effluent
- SV-04, Relay 4, Feed Waste
- SV-05, Relay 5, Filtrate Valve

### Instruments

- Feed tank pressure: Multi-IO channel 2, 0 to 30 psi hardware scaling
- Backwash tank pressure: Multi-IO channel 1, 0 to 30 psi hardware scaling
- Feed temperature: RTD input 1
- Filtrate weight: `/dev/ttyAMA3`
- Backwash effluent weight: `/dev/ttyAMA2`

## Known limitations

- Historical HMI layers remain coupled through inheritance.
- Hardware vendor packages are installed separately.
- Simulated tests cannot prove physical relay, Multi-IO, scale, touchscreen, or USB behavior.
- Hardware pressure calibration values remain in psi internally even though the HMI and CSV output use kPa.

## Physical MEU release checks

Confirm the touchscreen, enlarged settings dialogs, valve-button lockout, shared identifiers, kPa values, relay mapping, pressure and RTD channels, scale tare, Test/Benchmark/Clean sequences, CSV output, USB export, shutdown, and long-duration scale stability on the physical unit.
