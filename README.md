# MF/UF Membrane Evaluation Unit (MEU)

This repository contains the Python control application for the **MF/UF Membrane Evaluation Unit**, abbreviated **MEU**, running on a Raspberry Pi 5.

The MEU is a bench-scale membrane evaluation system used to assess microfiltration and ultrafiltration membrane performance through Flush, Benchmark, Test, Post-Scrub, and Clean sequences. It records process pressures, temperature, scale weights, test settings, cycle status, and timestamps where logging is enabled.

## Production startup

Install the Sequent Microsystems hardware drivers, then run:

```bash
python3 system_control.py
```

From a remote shell while displaying the HMI on the Raspberry Pi touchscreen:

```bash
DISPLAY=:0 XAUTHORITY=/home/waterarc/.Xauthority python3 system_control.py
```

`system_control.py` remains the supported production entry point. Existing public imports and the `PencilModule` compatibility name are retained.

## Hardware emulation

Run the current HMI without energizing Raspberry Pi hardware:

```bash
python3 scripts/run_emulated_hmi.py
```

See `RPI_EMULATION.md` for emulator controls and remote-display commands.

## Runtime dependencies

```bash
python3 -m pip install -r requirements.txt
```

Raspberry Pi OS may require a virtual environment:

```bash
sudo apt install python3-venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The Sequent Microsystems packages are installed separately from their vendor repositories.

## Release validation

Run the complete test suite against the Pi display:

```bash
DISPLAY=:0 XAUTHORITY=/home/waterarc/.Xauthority \
python3 -m unittest discover -s tests -v
```

Compile the production application and scripts:

```bash
python3 -m compileall system_control.py pencil scripts
```

The tests include simulated hardware and HMI regression coverage. Physical hardware and wet testing are still required before release.

## Current code boundaries

- `system_control.py`: production entry point and backend selection
- `pencil/config_loader.py`: JSON configuration loading
- `pencil/hardware_runtime.py`: production hardware safeguards
- `pencil/emulation.py`: deterministic Raspberry Pi hardware emulator
- `pencil/automation_cycle_logging.py`: process automation and cycle logging
- `pencil/hmi_identifier_state.py`: shared v2 identifier coordination
- `pencil/hmi_filtration_dialogs.py`: shared Test and Post-Scrub settings dialog
- `pencil/hmi_v2_integrated.py`: final production HMI composition

The current UI layout, navigation order, labels, colors, sizing, settings behavior, and process workflows are treated as release behavior and should not be changed during cleanup.

## Diagnostic scripts

### Manual HMI

```bash
python3 scripts/manual_hmi.py
```

### Scale reader

```bash
python3 scripts/weight_reader.py
```

### Relay test

```bash
python3 scripts/relay_test.py
```

### Continuous scale stress test

```bash
python3 stress_test_continuous.py 60
```

## Hardware mapping

- Backwash tank pressure: Multi-IO current-input channel 1
- Feed tank pressure: Multi-IO current-input channel 2
- Feed temperature: RTD input 1
- Filtrate scale: `/dev/ttyAMA3`
- Backwash effluent scale: `/dev/ttyAMA2`

The pressure driver uses the approved 0 to 30 psi scaling basis. HMI and new CSV values are converted to kPa where labeled as kPa.

## Configuration behavior

`config.json` is optional. A missing file uses built-in defaults. Malformed JSON, unreadable files, and valid JSON values that are not objects produce clear startup errors.

## Release notes

See `CHANGELOG.md`, `RELEASE_NOTES_V1.md`, and `RPI_EMULATION.md`.
