# Pencil Module Control

This repository contains a sample Python application for running a pencil module on a Raspberry Pi 5.
It assumes the following hardware:

* Sequent Microsystems **8-Relay** hat – controls solenoid valves.
* Sequent Microsystems **Multi IO** hat – reads pressure and RTD sensors.
* Two weight scales connected over USB.
* A Raspberry Pi 7 inch touch screen display used as an HMI.

The application uses the vendor Python libraries (`relay8` and `multiio`).

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
Run the `manual_hmi.py` script and interact with the GUI while all hardware
calls are faked:

```bash
python3 manual_hmi.py
```

## Simple Weight Reader

A lightweight script `weight_reader.py` is provided for quick testing of the USB scale. When run it prompts you to either read the current weight or send the zero (`Z`) command:

```bash
python3 weight_reader.py
```
