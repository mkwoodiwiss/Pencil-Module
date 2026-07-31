# Raspberry Pi Emulation

The MEU application can run without Raspberry Pi hardware by using the built-in `EmulatedMEU` backend. Production startup remains unchanged unless emulation is explicitly enabled.

## Launch the full HMI with emulated hardware

From the repository root:

```bash
MEU_EMULATE_RPI=1 python3 system_control.py
```

From a remote shell while using the Raspberry Pi display:

```bash
DISPLAY=:0 XAUTHORITY=/home/waterarc/.Xauthority \
MEU_EMULATE_RPI=1 python3 system_control.py
```

On Windows PowerShell:

```powershell
$env:MEU_EMULATE_RPI = "1"
python system_control.py
```

The normal command continues to use the production Raspberry Pi hardware backend:

```bash
python3 system_control.py
```

There is no separate emulation launcher script. The environment variable is the single supported selection path.

## Run the emulator tests

```bash
python3 -m unittest tests.test_rpi_emulation tests.test_emulated_startup -v
```

Run the complete automated release suite afterward:

```bash
DISPLAY=:0 XAUTHORITY=/home/waterarc/.Xauthority \
python3 -m unittest discover -s tests -v
python3 -m compileall system_control.py pencil
```

The current branch result is 113 passing tests with one intentional full-Tk display test skipped.

## Emulated interfaces

`pencil.emulation.EmulatedMEU` mirrors the production hardware methods used by the HMI and automation systems:

- `set_solenoid(relay, state)`
- `read_pressure(channel)`
- `read_rtd(channel)`
- `read_scale(channel)`
- `zero_scale(channel)`
- `zero_scales()`
- `scale_health(channel)`
- `apply_offsets(...)`
- `close()`

The emulator also provides deterministic test controls:

- `set_scale_value(channel, value)`
- `add_scale_weight(channel, amount)`
- `set_scale_connected(channel, connected)`
- `set_tare_allowed(channel, allowed)`
- `set_pressure(channel, psi)`
- `set_rtd(channel, temperature_c)`
- `relay_state(relay)`
- `relay_events`
- `reset()`

## Refactored application boundaries

The cleanup preserves public startup and HMI behavior while separating responsibilities:

- `system_control.py` selects real or emulated hardware and starts the HMI.
- `pencil.config_loader` owns JSON loading and configuration errors.
- `pencil.automation_lifecycle` owns shared process startup and guaranteed shutdown.
- `pencil.clean_sequence` owns the authoritative Clean step order.
- `pencil.log_files` owns automation file naming and settings snapshots.
- `pencil.completed_results` owns exact completed-run result discovery.
- `pencil.serial_transport` owns passive serial connection handling.
- `pencil.highland_scale` owns Highland parsing, worker coordination, cached readings, commands, and base tare behavior.
- `pencil.hardware_runtime` owns production Highland tare verification and dual-scale safeguards.
- `pencil.hmi_widget_clone` owns generic Tk cloning mechanics.
- `pencil.hmi_v2_clone_test_layout` owns MEU-specific Flush and Post-Scrub clone policy.
- `pencil.hmi_v2_integrated` is the compact production HMI composition point.

## Safety behavior

- All eight emulated relays start off.
- Closing the emulator forces all relays off.
- Invalid relay and scale channels raise `ValueError`.
- Emulated dual-scale tare raises the same operator-facing `RuntimeError` wording as production when either scale fails.
- Emulation is opt-in. Unset, false, or unrecognized `MEU_EMULATE_RPI` values create `PencilModule`, the production hardware class.
- The emulator never opens the production serial ports or energizes relay outputs.

## Scope

The emulator validates application-to-hardware contracts and supports HMI development without connected Raspberry Pi hardware. It does not replace final physical validation of relay wiring, analog scaling, Highland serial communication, touchscreen geometry, USB behavior, or wet-process sequences.
