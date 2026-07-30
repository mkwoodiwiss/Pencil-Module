# MF/UF Membrane Evaluation Unit (MEU)

This repository contains the Python control application for the **MF/UF Membrane Evaluation Unit (MEU)** running on a Raspberry Pi 5.

The MEU is a bench-scale membrane evaluation system used to assess microfiltration and ultrafiltration membrane performance through filtration, backwash, cleaning, and benchmark sequences. It records feed temperature, feed and backwash pressure, filtrate and backwash weight, cycle status, step status, test settings, and timestamps.

## Hardware requirements

The production application assumes the following hardware:

- Raspberry Pi 5
- Raspberry Pi 7-inch touchscreen
- Sequent Microsystems 8-Relay HAT
- Sequent Microsystems Multi-IO HAT
- Two RS232 weight scales
  - Filtrate scale: `/dev/ttyAMA3`
  - Backwash effluent scale: `/dev/ttyAMA2`

The application uses the Sequent Microsystems `lib8relind` and `multiio` vendor libraries. Install those drivers from their vendor repositories on the Raspberry Pi. They are not installed by `requirements.txt`.

- 8-Relay driver: http://github.com/SequentMicrosystems/8relind-rpi
- Multi-IO driver: https://github.com/SequentMicrosystems/multiio-rpi

## Application startup

Run the production application from the repository root:

```bash
python3 system_control.py
```

`system_control.py` is the supported compatibility entry point. It intentionally re-exports the public classes from `pencil` and retains the historical `PencilModule` name as an alias for `MEU`.

## Configuration

Runtime defaults are loaded from `config.json`.

- A missing configuration file uses empty defaults.
- A valid JSON object is passed to the HMI.
- Malformed JSON, unreadable files, or a JSON root that is not an object stop startup with a clear error instead of silently discarding the problem.

## Python dependencies

Install the normal Python runtime dependency with:

```bash
python3 -m pip install -r requirements.txt
```

Raspberry Pi OS may reject system-wide `pip` installs because Python is externally managed. Do not use `--break-system-packages` for development setup. Create a virtual environment instead:

```bash
sudo apt install python3-venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

The `.venv` directory is ignored by Git.

## Testing

### Authoritative release test

The supported release gate uses the Python standard library and simulated hardware:

```bash
python3 -m unittest discover -s tests
```

This command does not require `pytest`. The display and scale integration test skips automatically when no display is available.

### Optional pytest run

When development dependencies are installed in `.venv`, the same suite can also be run with:

```bash
python -m pytest -q
```

`pytest` is a secondary test runner. A v1 release should not be blocked solely because `pytest` is absent from the system Python when the authoritative `unittest` suite passes.

### Syntax compilation check

```bash
python3 -m compileall system_control.py pencil scripts
```

### Hardware integration test

With the Pi touchscreen and weight scales connected, run:

```bash
python3 -m unittest tests.test_scale_display_integration
```

This test uses the real display and scale interfaces while simulating the remaining hardware. Hardware validation should be reported separately from the hardware-independent suite.

## Supported diagnostic scripts

The files under `scripts/` are the maintained implementations. Root-level files with matching names are compatibility launchers and should not be removed without a documented migration.

### Simulated HMI

```bash
python3 scripts/manual_hmi.py
```

Runs the interface with simulated hardware for layout and workflow checks.

### Multi-IO reader

```bash
python3 scripts/multiio_reader.py
```

Reads the Multi-IO inputs for hardware troubleshooting.

### Weight reader

```bash
python3 scripts/weight_reader.py
```

Provides an interactive RS232 scale read and zero utility.

### Relay test

```bash
python3 scripts/relay_test.py
```

Provides an interactive relay test. Commands include `on 1`, `off 1`, and `q`.

### Scale stress tests

```bash
python3 scripts/scale_stress_test.py
python3 stress_test_continuous.py 60
```

The continuous test expects the filtrate scale on `/dev/ttyAMA3` and the backwash scale on `/dev/ttyAMA2`. It writes logs under `logs/` using a timestamped filename.

## Public API and compatibility

The intended public API is exported from `pencil/__init__.py`.

For the v1 release:

- Preserve `PencilModule` as an alias for `MEU`.
- Preserve the exports from `system_control.py` and `pencil/__init__.py`.
- Preserve historical configuration aliases such as `refill_time` and the `*_by_volume` names.
- Preserve root-level diagnostic launchers while they remain documented or used.
- Do not simplify the final HMI completion inheritance workaround without regression coverage.

## Known hardware-sensitive areas

The following require final validation on the production Raspberry Pi and should not be inferred from simulated tests alone:

- Scale tare timing and two-reading verification
- Continuous versus requested scale output
- Serial reconnection behavior
- Relay and Multi-IO board operation
- Touchscreen geometry and fullscreen shutdown
- USB mount detection and post-test export
- Final valve and instrument wiring mappings

See `RELEASE_NOTES_V1.md` for the v1 cleanup summary and known limitations.
