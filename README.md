# MF/UF Membrane Evaluation Unit (MEU)

This repository contains the Python control application for the **MF/UF Membrane Evaluation Unit**, abbreviated **MEU**, running on a Raspberry Pi 5.

The MEU is a bench-scale membrane evaluation system used to assess microfiltration and ultrafiltration membrane performance through filtration, backwash, cleaning, and benchmark test sequences. It records influent and backwash pressure, influent temperature, filtrate weight, backwash effluent weight, test settings, cycle status, and timestamps.

The pressure transmitters and calibration offsets remain based on the approved 0 to 30 psi instrument scaling. The HMI and newly generated CSV data files convert those readings to kPa.

## Hardware

The application assumes the following hardware:

- Sequent Microsystems **8-Relay** HAT for controlling solenoid valves.
- Sequent Microsystems **Multi-IO** HAT for reading pressure transmitters and the RTD.
- Two weight scales connected through RS232.
  - Filtrate scale: `/dev/ttyAMA3`
  - Backwash effluent scale: `/dev/ttyAMA2`
- Raspberry Pi 7-inch touchscreen used as the HMI.

The application uses the vendor Python libraries `lib8relind` and `multiio`.
The 8-Relay HAT is controlled through `lib8relind`, while the Multi-IO HAT is
accessed through the `SMmultiio` class in the `multiio` package.

Vendor repositories:

- http://github.com/SequentMicrosystems/8relind-rpi
- https://github.com/SequentMicrosystems/multiio-rpi

## Application startup

Install the Sequent Microsystems vendor drivers on the Raspberry Pi, then run:

```bash
python3 system_control.py
```

`system_control.py` is the supported production entry point. Public compatibility
names exported from `pencil` and `system_control` are intentionally retained.

## Python dependencies

Normal Python runtime dependencies are listed in `requirements.txt`:

```bash
python3 -m pip install -r requirements.txt
```

Raspberry Pi OS may reject system-wide `pip` installation because the Python
environment is externally managed. In that case, create a virtual environment:

```bash
sudo apt install python3-venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The Sequent Microsystems packages are installed separately from their vendor
repositories and are not normal PyPI requirements.

## Release testing

The authoritative hardware-independent release test uses Python's standard
library `unittest` runner:

```bash
python3 -m unittest discover -s tests
```

The complete application and script tree should also compile successfully:

```bash
python3 -m compileall system_control.py pencil scripts
```

The tests use simulated hardware interfaces and do not require the relay HAT,
Multi-IO HAT, scales, or touchscreen.

### Optional pytest runner

Development dependencies are listed in `requirements-dev.txt`. Install them in
a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

`pytest` is optional. The `unittest` command remains the release gate because it
is available without an additional test-runner dependency.

## Hardware integration testing

If the Pi touchscreen and weight scales are connected, run:

```bash
python3 -m unittest tests.test_scale_display_integration
```

The test automatically skips when no display is available. A skip in the full
hardware-independent suite is therefore expected on headless systems.

The following functions still require physical MEU validation before a complete
hardware release:

- Touchscreen layout and navigation
- Relay outputs and final valve mapping
- Multi-IO pressure and RTD channels
- Scale communication and verified tare
- USB export
- Complete Test, Benchmark, and Clean wet sequences
- Long-duration scale stability

## Manual HMI testing

Run the HMI with simulated hardware:

```bash
python3 scripts/manual_hmi.py
```

## Diagnostic scripts

### Simple weight reader

Use `scripts/weight_reader.py` for RS232 scale testing:

```bash
python3 scripts/weight_reader.py
```

It can read the current weight or send the scale zero command.

### Relay test

Use `scripts/relay_test.py` to manually toggle the 8-Relay HAT:

```bash
python3 scripts/relay_test.py
```

Enter commands such as `on 1` or `off 1`. Enter `q` to quit.

### Continuous scale stress test

Run the root-level compatibility launcher:

```bash
python3 stress_test_continuous.py 60
```

The optional argument specifies the duration in seconds. Logs are written to the
`logs` directory using the filename pattern
`usb_scale_stress_test_<timestamp>.txt`.

Root-level launchers that duplicate script names under `scripts/` are retained
for compatibility with existing Raspberry Pi commands and documentation.

## Pressure channels and units

The final pressure channel mapping is:

- Backwash tank pressure: Multi-IO 4-20 mA channel 1
- Feed tank pressure: Multi-IO 4-20 mA channel 2

The hardware driver uses the approved 0 to 30 psi scaling basis. HMI values and
CSV columns named `feed_tank_pressure_kpa` and
`backwash_tank_pressure_kpa` are converted using 1 psi = 6.894757293168 kPa.

When the Multi-IO board or driver is unavailable, hardware methods fall back to
simulated values. A message such as the following indicates that a pressure
input could not be read:

```text
[debug] read_pressure: ch=1, io unavailable, offset=0.00
```

Install the vendor libraries for the same Python interpreter used to run the
MEU application and verify the HAT connection.

## Configuration behavior

`config.json` is optional. If it is missing, the application starts with built-in
default values.

The following conditions are treated as startup errors instead of being silently
discarded:

- Malformed JSON
- Permission or read failures
- A valid JSON value that is not an object

## v1 compatibility policy

The v1 cleanup deliberately preserves:

- `system_control.py` as the production launcher
- Public `pencil` package exports
- The `PencilModule` compatibility name
- Existing HMI inheritance layers
- Existing automation and configuration compatibility layers
- Approved valve, relay, instrument, and serial-port mappings
- README-supported diagnostic scripts

See `RELEASE_NOTES_V1.md` for release scope and known limitations.
