#!/bin/bash
# Install Sequent Microsystems board libraries.
set -e

# Home Automation HAT driver
curl https://raw.githubusercontent.com/SequentMicrosystems/home-automation-rpi/master/install.sh | sudo bash

# Multi IO HAT driver
curl https://raw.githubusercontent.com/SequentMicrosystems/multiio-rpi/master/install.sh | sudo bash
