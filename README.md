# Pencil Module Control

This repository contains a sample Python application for running a pencil module on a Raspberry Pi 5.
It assumes the following hardware:

* Sequent Microsystems **8-Relay** hat – controls solenoid valves.
* Sequent Microsystems **Multi IO** hat – reads pressure and RTD sensors.
* Two weight scales connected via RS232.
  The effluent scale is typically available as ``/dev/ttyAMA3`` and the
  backwash scale as ``/dev/ttyAMA2``.
* A Raspberry Pi 7 inch touch screen display used as an HMI.

The application uses the vendor Python libraries (`lib8relind` and `multiio`).
The 8-relay hat is controlled using the functions provided by ``lib8relind``
while the Multi-IO hat is accessed through the ``SMmultiio`` class in the
``multiio`` package.

http://github.com/SequentMicrosystems/8relind-rpi

https://github.com/SequentMicrosystems/multiio-rpi

The driver documentation for the Sequent Microsystems boards provides
installation scripts. Run them on the Raspberry Pi to fetch the latest
drivers for the **8 Relay** and **Multi IO** hats:

Then run the controller:

```bash
python3 system_control.py
```

The GUI provides live readings and buttons for operating the solenoids.

## Testing

A basic test suite provides simulated versions of the hardware interfaces so the
code can run without a Raspberry Pi. Execute the tests with:

```bash
python3 -m unittest discover -s tests
```

If you have the Pi's touch screen and weight scales connected you can also run an
integration test that uses the real devices while simulating the other hardware:

```bash
python3 -m unittest tests.test_scale_display_integration
```
The test automatically skips itself when no display is available, making it safe
to include in the full suite on headless machines.


## Manual GUI Testing

You can experiment with the interface on any machine using simulated hardware.
Run the `scripts/manual_hmi.py` script and interact with the GUI while all hardware
calls are faked:

```bash
python3 scripts/manual_hmi.py
```

## Simple Weight Reader

A lightweight script `scripts/weight_reader.py` is provided for quick testing of the RS232 scale. When run it prompts you to either read the current weight or send the zero (`Z`) command:

```bash
python3 scripts/weight_reader.py
```

## Relay Test Program

Use `scripts/relay_test.py` to manually toggle the relays on the 8‑Relay hat. The
script is handy for verifying wiring and confirming that the `lib8relind`
driver is installed:

```bash
python3 scripts/relay_test.py
```
Enter commands such as `on 1` or `off 1` to operate a relay. Type `q` to quit.

## Continuous Scale Stress Test

Run `stress_test_continuous.py` to listen to both scales for a fixed
period of time. The script expects the scales to be connected to the Pi's
RS232 ports with the effluent scale on `/dev/ttyAMA3` and the backwash scale on
`/dev/ttyAMA2`. No commands are sent; the script simply logs each line
received from the scales.

```bash
python3 stress_test_continuous.py 60
```

The optional argument specifies the duration in seconds (default is 60). Log
messages are written to the `logs` directory.

## Troubleshooting Debug Logs

When running without the Multi IO board or its `multiio` driver, hardware
methods fall back to simulated values. In that case you may see messages such
as:

```
[debug] read_pressure: ch=1, io unavailable, offset=0.00
```
This indicates the pressure sensor could not be read because the driver or the
board itself is not available. The returned value will simply be the calibration
offset (zero by default). To obtain real sensor readings, install the vendor
libraries and connect the Multi IO hat before starting the application.

In normal operation the backwash and influent pressure sensors use the hat's
4-20 mA inputs on Multi IO channels **1** and **2**, respectively.

If you see the "io unavailable" message even though the vendor drivers are installed, verify that the libraries were installed for the same Python interpreter you use to run the application. A mismatch in Python versions can prevent the `multiio` module from loading even when the files are present.
