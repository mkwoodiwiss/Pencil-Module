# MF/UF Membrane Evaluation Unit (MEU)

This repository contains the Python control application for the **MF/UF Membrane Evaluation Unit**, abbreviated **MEU**, running on a Raspberry Pi 5.

The MEU is a bench-scale membrane evaluation system used to assess microfiltration and ultrafiltration membrane performance through filtration, backwash, cleaning, and benchmark test sequences. It records influent and backwash pressure, influent temperature, effluent weight, backwash weight, test settings, cycle status, and timestamps.

It assumes the following hardware:

* Sequent Microsystems **8-Relay** HAT for controlling solenoid valves.
* Sequent Microsystems **Multi-IO** HAT for reading pressure transmitters and the RTD.
* Two weight scales connected through RS232.
  The effluent scale is typically available as `/dev/ttyAMA3` and the
  backwash scale as `/dev/ttyAMA2`.
* A Raspberry Pi 7-inch touchscreen used as the HMI.

The application uses the vendor Python libraries `lib8relind` and `multiio`.
The 8-Relay HAT is controlled through `lib8relind`, while the Multi-IO HAT is
accessed through the `SMmultiio` class in the `multiio` package.

Vendor repositories:

* http://github.com/SequentMicrosystems/8relind-rpi
* https://github.com/SequentMicrosystems/multiio-rpi

Install the vendor drivers on the Raspberry Pi, then run the MEU controller:

```bash
python3 system_control.py
```

The HMI provides live readings, automated test sequences, and manual solenoid controls.

## Testing

A basic test suite provides simulated versions of the hardware interfaces so the
code can run without a Raspberry Pi. Execute the tests with:

```bash
python3 -m unittest discover -s tests
```

If the Pi touchscreen and weight scales are connected, an integration test can
use the real devices while simulating the remaining hardware:

```bash
python3 -m unittest tests.test_scale_display_integration
```

The test automatically skips itself when no display is available, making it safe
to include in the full suite on headless machines.

## Manual HMI Testing

The interface can be run on another machine with simulated hardware. Run:

```bash
python3 scripts/manual_hmi.py
```

## Simple Weight Reader

Use `scripts/weight_reader.py` for quick RS232 scale testing. The script can read
the current weight or send the zero command:

```bash
python3 scripts/weight_reader.py
```

## Relay Test Program

Use `scripts/relay_test.py` to manually toggle the relays on the 8-Relay HAT:

```bash
python3 scripts/relay_test.py
```

Enter commands such as `on 1` or `off 1` to operate a relay. Enter `q` to quit.

## Continuous Scale Stress Test

Run `stress_test_continuous.py` to listen to both scales for a fixed period. The
script expects the effluent scale on `/dev/ttyAMA3` and the backwash scale on
`/dev/ttyAMA2`.

```bash
python3 stress_test_continuous.py 60
```

The optional argument specifies the duration in seconds. Log messages are written
to the `logs` directory using the filename pattern
`usb_scale_stress_test_<timestamp>.txt`.

## Troubleshooting Debug Logs

When the Multi-IO board or its driver is unavailable, hardware methods fall back
to simulated values. Messages such as the following indicate that the pressure
sensor could not be read:

```text
[debug] read_pressure: ch=1, io unavailable, offset=0.00
```

The returned value will be the calibration offset. Install the vendor libraries
and connect the Multi-IO HAT to obtain real readings.

The backwash and influent pressure transmitters use Multi-IO 4-20 mA input
channels 1 and 2, respectively. If the driver is installed but remains
unavailable, verify that it was installed for the same Python interpreter used
to run the MEU application.
