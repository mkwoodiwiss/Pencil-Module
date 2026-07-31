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

The normal command still uses the production Raspberry Pi hardware backend:

```bash
python3 system_control.py
```

## Run the emulator tests

```bash
python3 -m unittest tests.test_rpi_emulation tests.test_emulated_startup
```

Run the complete release suite afterward:

```bash
DISPLAY=:0 XAUTHORITY=/home/waterarc/.Xauthority \
python3 -m unittest discover -s tests -v
python3 -m compileall system_control.py pencil scripts
```

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

The emulator also provides test controls:

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

The cleanup keeps the public startup and UI behavior intact while separating recent v2 responsibilities:

- `pencil.config_loader` owns JSON loading and configuration errors.
- `system_control.py` selects real or emulated hardware and starts the HMI.
- `pencil.hmi_identifier_state` owns v2 identifier synchronization.
- `pencil.hmi_filtration_dialogs` owns the shared Test and Post-Scrub settings dialog.
- `pencil.hmi_v2_integrated` is the compact final HMI composition point.

## Safety behavior

- All eight relays start off.
- Closing the emulator forces all relays off.
- Invalid relay and scale channels raise `ValueError`.
- Emulated dual-scale tare raises the same operator-facing `RuntimeError` wording as the production runtime when either scale fails.
- Emulation is opt-in. Unset, false, or unrecognized `MEU_EMULATE_RPI` values continue to create `PencilModule`, the production hardware class.

## Scope

This emulator validates application-to-hardware contracts and supports HMI development without a connected Pi. It does not replace final physical validation of relay wiring, analog scaling, serial communications, touchscreen geometry, USB behavior, or wet process sequences.
