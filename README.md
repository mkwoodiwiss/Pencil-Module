# Pencil Module Control

This repository contains a sample Python application for running a pencil module on a Raspberry Pi 5.
It assumes the following hardware:

* Sequent Microsystems **Home Automation** (or **8-Relay**) hat – controls solenoid valves.
* Sequent Microsystems **Multi IO** hat – reads pressure and RTD sensors.
* A weight scale connected over USB.
* A Raspberry Pi 7 inch touch screen display used as an HMI.

The application uses the vendor Python libraries (`relay8` and `multiio`).
Install them on the Pi with:

```bash
pip install relay8 multiio
```

The driver documentation for the Sequent Microsystems boards also provides
installation scripts. Run them on the Raspberry Pi to fetch the latest
drivers for the **Home Automation** and **Multi IO** hats:

```bash
curl https://raw.githubusercontent.com/SequentMicrosystems/home-automation-rpi/master/install.sh | sudo bash
curl https://raw.githubusercontent.com/SequentMicrosystems/multiio-rpi/master/install.sh | sudo bash
```
For convenience this repository also includes an `install_vendor_deps.sh`
script which wraps the above commands.

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


## Manual GUI Testing

You can experiment with the interface on any machine using simulated hardware.
Run the `manual_hmi.py` script and interact with the GUI while all hardware
calls are faked:

```bash
python3 manual_hmi.py
```
