# MEU Code Handoff Guide

This guide is written for the person returning to the MF/UF Membrane Evaluation Unit code after enough time has passed that the architecture and engineering decisions are no longer familiar.

Start here before making a feature change. The code is divided by responsibility so most changes should have one clear home. Avoid adding new behavior to whichever class is easiest to reach through inheritance. First identify which boundary owns the behavior.

## Release state at handoff

The architecture cleanup was merged after these checks:

- 117 automated tests passed
- one full-Tk display integration test remained intentionally opt-in
- every touchscreen tab and settings dialog was visually checked
- both Highland scales communicated and completed verified tare
- relay and valve mapping was checked
- pressure and RTD channels were checked
- USB copying, checksum verification, unmount, device power-off, and eject were checked

The full integrated wet-process validation was still outstanding at the time of the cleanup merge. Treat that as the primary remaining system-level validation.

## Start the application

Production hardware:

```bash
python3 system_control.py
```

Production HMI from a remote shell on the Pi display:

```bash
DISPLAY=:0 XAUTHORITY=/home/waterarc/.Xauthority python3 system_control.py
```

Emulated hardware:

```bash
MEU_EMULATE_RPI=1 python3 system_control.py
```

The environment variable is intentionally opt-in. Unset or unrecognized values use physical hardware.

## Validation commands

Run after any production change:

```bash
DISPLAY=:0 XAUTHORITY=/home/waterarc/.Xauthority \
python3 -m unittest discover -s tests -v

python3 -m compileall system_control.py pencil
```

Run the opt-in full-Tk integration check when changing widget construction, cloning, or teardown behavior:

```bash
MEU_RUN_TK_INTEGRATION=1 \
DISPLAY=:0 XAUTHORITY=/home/waterarc/.Xauthority \
python3 -m unittest tests.test_scale_display_integration -v
```

A passing automated suite does not replace a wet test when changing valve sequences, stopping conditions, scale behavior, process timing, prompts, or logging during flow.

## Stable hardware mapping

### Valve outputs

- SV-01, Relay 1: Backwash Supply
- SV-02, Relay 2: Influent Supply
- SV-03, Relay 3: Backwash Effluent
- SV-04, Relay 4: Influent Drain
- SV-05, Relay 5: Effluent Valve

Do not infer valve assignments from old names or comments elsewhere. This mapping is the approved source of truth.

### Instruments

- Backwash supply pressure: Multi-IO current-input channel 1
- Influent supply pressure: Multi-IO current-input channel 2
- Influent temperature: physical RTD input 1, application call `read_rtd(0)`
- Effluent/filtrate scale: application channel 0, `/dev/ttyAMA3`
- Backwash-effluent scale: application channel 1, `/dev/ttyAMA2`

Pressure transmitters use a 4-20 mA, 0-30 psi basis. HMI and CSV layers convert to kPa only where the label/schema requires kPa.

## Architecture map

### `system_control.py`

Owns only startup:

- optional `config.json` loading
- real-versus-emulated backend selection
- final HMI construction
- Tk main loop

It also re-exports historical public names. Do not add process or hardware logic here.

### `pencil/hardware.py`

Owns common hardware composition:

- relay wrapper
- Multi-IO construction
- pressure conversion
- RTD channel translation
- scale-channel selection
- offsets
- base scale API

The class attributes `SCALE_MANAGER_CLASS` and `RELAY_WRAPPER_CLASS` are injection points used by production runtime code and tests.

### `pencil/serial_transport.py`

Owns passive serial mechanics only:

- open and close
- reconnect throttling
- input-buffer reset
- read and write
- flush
- transport error state

Do not add Highland parsing or tare decisions here. Keeping the transport protocol-neutral is what makes failures easy to isolate and test.

### `pencil/highland_scale.py`

Owns normal Highland scale behavior:

- response parsing
- cached readings
- health information
- worker thread
- command queue
- stale-reading print fallback
- base tare request

The worker thread is the serialization boundary for serial traffic. Avoid direct serial reads/writes from HMI or automation threads.

### `pencil/hardware_runtime.py`

Owns production-only verified tare:

- sends `T\r\n`
- clears pre-tare input
- accepts only fresh post-tare readings
- requires two consecutive values within +/-0.2 g
- uses no more than two `P\r\n` fallback requests per attempt
- retries a failed tare
- tares both scales concurrently
- raises and prevents a run if either scale fails

The timing and tolerance values are safety/operability decisions, not formatting preferences. Revalidate physically after changing them.

### `pencil/emulation.py`

Mirrors the hardware API without opening Raspberry Pi devices. Use it to develop HMI and automation behavior safely. It is deterministic and provides controls for values, disconnects, tare failures, relay state, and offsets.

Emulation proves the application-to-hardware contract. It does not prove physical wiring, serial timing, analog scaling, touchscreen geometry, USB behavior, or wet-process hydraulics.

### `pencil/automation_lifecycle.py`

Owns the common run boundary:

- clear cancellation
- optionally close all valves
- open exact run-owned logs
- apply offsets
- optionally tare scales
- execute process body
- always call `stop_test()` in `finally`

New process types should use `_run_managed`. Bypassing it risks leaving valves on or logs open after an exception.

### `pencil/clean_sequence.py`

Owns the authoritative Clean step order and valve combinations. There should not be another independent Clean sequence hidden in an HMI class or automation subclass.

When changing Clean:

1. update the sequence definition;
2. update sequence tests;
3. confirm operator prompts and progress labels;
4. dry-run with emulation;
5. perform a wet test.

### `pencil/automation_meu.py`

Owns the process implementations that execute Flush, Benchmark, Test, Post-Scrub, and Clean behavior. It should consume lifecycle, logging, configuration, and hardware APIs rather than recreate those responsibilities.

When adding a phase, keep valve selection and progress reporting explicit. Ensure every wait loop checks cancellation and every exit reaches the managed cleanup path.

### `pencil/data_logging.py`

Owns CSV headers and construction of synchronized sensor rows. Keep schema order stable unless downstream analysis users agree to a versioned change.

### `pencil/log_files.py`

Owns the files for one automation run:

- filenames
- settings snapshot
- data writer
- handles
- idempotent close

A completed run should refer to its owned files rather than scan the directory and guess based on modification time.

### `pencil/completed_results.py`

Selects the exact files to show in the completion/USB workflow. It prefers files owned by the completed automation and only uses discovery as a compatibility fallback.

### `pencil/usb_export.py`

Owns safe USB export:

1. copy to a hidden partial file;
2. flush and `fsync`;
3. atomically replace the final file;
4. compare size and SHA-256 checksum;
5. run system `sync`;
6. unmount the partition;
7. power off the parent USB block device;
8. report safe removal only after success.

Do not simplify this to `shutil.copy` followed by a success message. The current sequence was added after the original export copied successfully but did not eject the drive.

### HMI modules

- `hmi_v2_integrated.py`: final composition point
- `hmi_identifier_state.py`: shared Project, Module ID, and Sample ID coordination
- `hmi_filtration_dialogs.py`: shared Test and Post-Scrub settings dialog construction
- `hmi_post_scrub_state.py`: Post-Scrub-specific state
- `hmi_summary_formatting.py`: summary text formatting
- `hmi_touch_entries.py`: touchscreen entry selection and keyboard routing
- `hmi_widget_clone.py`: generic Tk widget-tree cloning mechanics
- `hmi_v2_clone_test_layout.py`: MEU-specific Flush and Post-Scrub clone policy
- `hmi_tk_clone_compat.py`: narrow compatibility helpers

Keep generic cloning mechanics separate from MEU-specific decisions about which commands, variables, and labels a cloned tab should use.

## Compatibility names that look removable but are not necessarily dead

The project retains names such as:

- `PencilModule`
- `_ScaleManager`
- selected exports from `system_control.py`
- legacy configuration aliases

These exist because deployed Pi scripts, service files, diagnostics, tests, or old project code may import them. Search the repository and deployed startup configuration before deleting compatibility names.

## Safety invariants

Preserve these unless deliberately redesigning and revalidating the machine:

- production startup defaults to real hardware
- all process runs have a guaranteed cleanup path
- cleanup closes valves and logs even after exceptions
- a required tare failure prevents process startup
- scale tare verification uses fresh readings
- both scales must verify when a process requires dual tare
- USB is not reported safe until copy verification and eject complete
- hardware mappings come from the approved mapping above
- application scale channels remain 0 = effluent and 1 = backwash
- `read_rtd(0)` remains physical RTD input 1

## How to add a feature without rebuilding the old monolith

1. Identify the owner of the behavior in the architecture map.
2. Add or extend a focused helper/module when the behavior has a distinct responsibility.
3. Keep the final HMI and startup modules as composition points.
4. Add tests at the lowest practical boundary.
5. Add one integration test when several boundaries interact.
6. Run the complete suite.
7. Physically validate any changed hardware or operator behavior.
8. Wet-test any changed process sequence or stop condition.

## Useful diagnostic scripts

```bash
python3 scripts/manual_hmi.py
python3 scripts/weight_reader.py
python3 scripts/relay_test.py
python3 stress_test_continuous.py 60
```

Use the continuous scale stress test when diagnosing intermittent `--` readings, stale values, reconnect behavior, or missed tare responses.

## When returning after a long absence

Use this order:

1. Read this file and `README.md`.
2. Review `CHANGELOG.md` for the architecture cleanup.
3. Run the full automated suite before editing anything.
4. Start the emulator and exercise the relevant HMI workflow.
5. Read the focused owner module and its corresponding tests together.
6. Make the smallest boundary-respecting change.
7. Re-run all tests, not only the new test.
8. Perform the applicable physical and wet validation.
