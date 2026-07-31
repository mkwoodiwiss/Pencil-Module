# MF/UF Membrane Evaluation Unit (MEU)

This repository contains the Python control application for the **MF/UF Membrane Evaluation Unit**, abbreviated **MEU**, running on a Raspberry Pi 5.

The MEU is a bench-scale membrane evaluation system used to assess microfiltration and ultrafiltration membrane performance through Flush, Benchmark, Test, Post-Scrub, and Clean sequences. It records process pressures, temperature, scale weights, test settings, cycle status, and timestamps where logging is enabled.

## Returning to the project

Read `CODE_HANDOFF.md` before making changes after a long absence or transferring the project to another developer. It explains the architecture, approved hardware mappings, safety invariants, compatibility names, validation expectations, and which module owns each type of behavior.

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

Run the production HMI without energizing Raspberry Pi hardware:

```bash
MEU_EMULATE_RPI=1 python3 system_control.py
```

From a remote shell using the Pi display:

```bash
DISPLAY=:0 XAUTHORITY=/home/waterarc/.Xauthority \
MEU_EMULATE_RPI=1 python3 system_control.py
```

See `RPI_EMULATION.md` for emulator controls and validation scope.

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

Run the complete automated suite:

```bash
DISPLAY=:0 XAUTHORITY=/home/waterarc/.Xauthority \
python3 -m unittest discover -s tests -v
```

The current confirmed branch result is **117 tests passed, with one intentional full-Tk display test skipped**.

Compile the production application:

```bash
python3 -m compileall system_control.py pencil
```

The automated suite covers configuration, automation lifecycle, clean sequencing, logging, result-file selection, HMI composition, emulation, serial transport, Highland protocol behavior, hardware factories, USB eject behavior, and public interfaces.

Completed physical checks:

- Visual comparison of every process tab and settings dialog
- Physical Highland communication and verified tare on both scales
- Relay and final valve mapping
- Pressure and RTD channel readings
- USB result copying and checksum verification
- Automatic USB unmount, device power-off, and safe eject

## Current code boundaries

- `system_control.py`: production entry point and backend selection
- `pencil/config_loader.py`: JSON configuration loading
- `pencil/config_meu.py`: process configuration models and legacy aliases
- `pencil/automation_lifecycle.py`: shared safe process startup and shutdown
- `pencil/clean_sequence.py`: authoritative Clean sequence
- `pencil/log_files.py`: automation file naming and ownership
- `pencil/completed_results.py`: completed-run result-file selection
- `pencil/serial_transport.py`: passive serial connection, read, write, reconnect, and error handling
- `pencil/highland_scale.py`: Highland parsing, command queue, cached readings, and base tare behavior
- `pencil/hardware.py`: relay, Multi-IO, sensor conversion, and hardware composition
- `pencil/hardware_runtime.py`: production Highland tare safeguards and dual-scale verification
- `pencil/usb_export.py`: verified result copying, unmount, and USB device power-off
- `pencil/emulation.py`: deterministic Raspberry Pi hardware emulator
- `pencil/hmi_widget_clone.py`: generic Tk widget-tree cloning mechanics
- `pencil/hmi_v2_clone_test_layout.py`: Flush and Post-Scrub clone policy
- `pencil/hmi_v2_integrated.py`: final production HMI composition

The current UI layout, navigation order, labels, colors, sizing, settings behavior, hardware mapping, and process workflows are treated as release behavior and should not be changed during cleanup.

## Hardware mapping

### Valves

- SV-01, Relay 1: Backwash Supply
- SV-02, Relay 2: Influent Supply
- SV-03, Relay 3: Backwash Effluent
- SV-04, Relay 4: Influent Drain
- SV-05, Relay 5: Effluent Valve

### Instruments

- Backwash supply pressure: Multi-IO current-input channel 1
- Influent supply pressure: Multi-IO current-input channel 2
- Influent temperature: RTD input 1, application channel `read_rtd(0)`
- Effluent scale: `/dev/ttyAMA3`
- Backwash scale: `/dev/ttyAMA2`

The pressure driver uses the approved 0 to 30 psi scaling basis. HMI and CSV values are converted to kPa where labeled as kPa.

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

## Configuration behavior

`config.json` is optional. A missing file uses built-in defaults. Malformed JSON, unreadable files, and valid JSON values that are not objects produce clear startup errors.

## Remaining release validation

- Complete Flush, Benchmark, Test, Post-Scrub, and Clean wet sequences

See `CODE_HANDOFF.md`, `CHANGELOG.md`, `RELEASE_NOTES_V1.md`, and `RPI_EMULATION.md`.