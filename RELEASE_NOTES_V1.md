# MEU v1 Release Cleanup Notes

## Scope

This release cleanup prepares the MF/UF Membrane Evaluation Unit application for a controlled v1 release without broad architectural changes. Operational sequences, hardware mappings, valve mappings, instrument mappings, scale timing, and the final HMI inheritance structure remain unchanged unless explicitly listed below.

## Baseline

Baseline commit: `3619a0bf06109dc7f4032ff2389151a07126de71`

Initial documented test result:

- `python -m unittest discover -s tests`
- 19 tests discovered
- 1 failure
- 13 errors
- 1 skipped

Initial failures were caused by stale simulated scale interfaces and stale expected logging and terminology values. The production application was not changed to make those stale tests pass.

Initial `pytest` result:

- Not available in the Raspberry Pi system Python
- Raspberry Pi OS rejected a system-wide `pip` install under PEP 668
- Development installation now uses a project virtual environment

## Changes included

### Test harness restoration

- Updated the simulated MEU to match the current scale-manager interface.
- Preserved read-only production serial compatibility properties.
- Updated stale terminology expectations to `Filtrate Weight`.
- Updated the expected CSV header to include the intentional `cycle` column.

### Configuration handling

- A missing `config.json` still uses empty defaults.
- A valid JSON object still loads normally.
- Malformed JSON now stops startup with a clear error.
- Permission and file-read errors now stop startup with a clear error.
- A JSON root that is not an object now stops startup with a clear error.

This is the only intentional application behavior change in the cleanup to date.

### Regression coverage

Hardware-independent regression tests now protect:

- Public export of the final HMI class
- Non-widget map callback targets
- Destroyed widget handling during shutdown
- Valve button synchronization
- Process-line refresh after completion
- Missing runtime state handling
- The final completion callback path
- Bypassing the duplicate themed USB completion dialog
- Calling the original completion workflow once

### Dependencies

- Added `requirements.txt` for the normal PyPI runtime dependency.
- Added `requirements-dev.txt` for optional `pytest` development use.
- Sequent Microsystems `lib8relind` and `multiio` remain separately installed vendor dependencies.

### Documentation

- Established `unittest` as the authoritative release test command.
- Documented optional `pytest` use through `.venv`.
- Separated hardware-independent and hardware integration validation.
- Classified maintained diagnostic scripts and compatibility launchers.
- Documented public API and compatibility preservation rules.

## Preserved compatibility

The following remain intentionally supported for v1:

- `system_control.py` as the application and compatibility entry point
- `PencilModule` as an alias for `MEU`
- Public exports from `pencil/__init__.py`
- Re-exports from `system_control.py`
- Historical configuration aliases including `refill_time` and `*_by_volume`
- Root-level diagnostic launchers
- The final HMI completion inheritance bypass
- Existing HMI layering and module names

## Files not removed

No files were removed during the controlled cleanup. Several modules appear to represent historical compatibility or incremental HMI layers, but none were proven obsolete with sufficient confidence for v1 removal.

## Known limitations and remaining hardware validation

The automated hardware-independent suite does not prove correct operation of:

- Real scale tare acceptance and two-zero-reading verification
- Continuous versus requested scale output behavior
- Scale reconnection after intermittent serial faults
- Relay HAT operation
- Multi-IO pressure and RTD acquisition
- Raspberry Pi touchscreen geometry
- Fullscreen exit behavior on the production display
- USB automount detection
- Post-test file export to USB
- Final field wiring and instrument channel assignments

These items require a separate wet-test and hardware-validation record before final release approval.

## Release validation commands

Hardware-independent release gate:

```bash
python3 -m unittest discover -s tests
python3 -m compileall system_control.py pencil scripts
```

Optional development runner:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Hardware integration test:

```bash
python3 -m unittest tests.test_scale_display_integration
```
