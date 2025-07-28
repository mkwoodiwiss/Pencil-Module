# Controls Narrative

**System Name:** Pencil Module
**Date:** 07/25/2025
**Author:** M. Woodiwiss

## 1 - INTRODUCTION
The Pencil Module Filtration Test System is designed to automate and log performance data for pencil module filters. It enables precise control and monitoring of filtration, backwash, cleaning and benchmark test cycles, ensuring repeatable test sequences. The system integrates pressure and temperature sensing, weight measurement, and both manual and automatic operation modes via an HMI interface.

## 2 - PROCESS OBJECTIVE
The system performs automated filtration, backwash, cleaning and benchmark test cycles on pencil module filters. Throughout these processes it continuously logs:
- Influent temperature
- Backwash supply pressure
- Influent supply pressure
- Weight of collected effluent and backwash water
- Operator-entered setpoints and process metadata
- Timestamps for each logged data point
The collected data is used to evaluate filter performance, cleaning effectiveness and repeatability across multiple test cycles.

## 3 - INPUTS
| Signal | Type | Description |
|-------|------|-------------|
| Influent Supply Pressure | PIT | Monitors influent supply tank pressure |
| Backwash Supply Pressure | PIT | Monitors backwash supply tank pressure |
| Influent Temperature | RTD | Measures influent temperature |
| Effluent Weight | Scale | Measures filtered effluent |
| Backwash Weight | Scale | Measures backwash water output |
| Setpoints/Input Controls | HMI | Operator-configurable values (see Section 5) |
| Prime Button | HMI | Starts priming routine |
| Start/Stop Test Button | HMI | Begins/Stops automated cycle |
| Calibration Button | HMI | Applies offset to pressure/temp readings |

## 4 - OUTPUTS
| Device | Type | Function |
|-------|------|----------|
| Influent Supply Valve | Solenoid | Controls influent supply flow |
| Backwash Supply Valve | Solenoid | Controls backwash supply flow |
| Effluent Valve | Solenoid | Controls effluent flow |
| Backwash Effluent Valve | Solenoid | Controls backwash effluent flow |
| Influent Water Drain Valve | Solenoid | Drains influent line during refill |
| Scale Zero Command | Digital | Zeros both scales at test start |

## 5 - SETPOINTS AND OPERATOR INPUTS (VIA HMI)
- Filtration Target: Time (sec) or Weight (g)
- Backwash Target: Time (sec) or Weight (mL)
- Purge Time: Duration in seconds
- Cycle Count: Number of full cycles to perform
- Sample Time: Data logging interval in seconds
- Calibration Offsets: Offsets used to calibrate sensors
- Project Name: Included in log file titles
- Sample ID: Included in log file titles
- Module ID: Included in log file titles
- FWD Soak Time: Duration in seconds
- BW Soak Time: Duration in seconds

## 6 - AUTOMATED PROCESSES
### Test Sequence
1. **Start Test**
   - Zero both scales.
   - Begin data logging at defined sample time intervals.
2. **Cycle Loop** (repeats for the defined Cycle Count)
   - **Purge Phase**
     - Open Influent Supply Valve and Influent Water Drain Valve.
     - Run for the configured Refill Time then close all valves.
   - **Filter Phase**
     - Open Influent Supply Valve and Effluent Valve.
     - Continue until either the Filtration Time or Effluent Weight setpoint is met.
   - **Backwash Phase**
     - Open Backwash Supply Valve and Backwash Effluent Valve.
     - Continue until either the Backwash Time or Backwash Weight setpoint is met.
3. **Cycle Completion**
   - Stop all outputs.
   - End data logging.
   - Return to idle state.

### Clean Sequence
1. **Start Clean**
   - Zero both scales.
   - Begin data logging at defined sample time intervals.
2. **Cycle Loop** (repeats for the defined Cycle Count)
   - **Forward Clean Phase**
     - Open Influent Supply Valve and Effluent Valve to run cleaning solution through the filter.
     - Continue until either the Effluent Time or Effluent Weight setpoint is met.
     - Close valves and soak for the configured FWD Soak Time.
   - **Backwash Clean Phase**
     - Open Backwash Supply Valve and Backwash Effluent Valve to run cleaning solution through the backwash line.
     - Continue until either the Backwash Time or Backwash Weight setpoint is met.
     - Close valves and soak for the configured BW Soak Time.
3. **Rinse Phase**
   - Prompt the operator to refill supply tanks with DI water.
   - Perform Purge, Filter and Backwash phases as in the Test sequence.
4. **Cycle Completion**
   - Stop all outputs.
   - End data logging.
   - Return to idle state.

### Benchmark Sequence
1. **Start Benchmark**
   - Zero both scales.
   - Begin data logging at defined sample time intervals.
2. **Cycle Loop** (repeats for the defined Repeat Count)
   - **Purge Phase**
     - Open Influent Supply Valve and Influent Water Drain Valve for the configured Refill Time.
   - **Filter Phase**
     - Open Influent Supply Valve and Effluent Valve until the Filtration Time or Effluent Weight setpoint is reached.
   - **Backwash Phase**
     - Open Backwash Supply Valve and Backwash Effluent Valve until the Backwash Time or Backwash Weight setpoint is reached.
3. **Cycle Completion**
   - Stop all outputs.
   - End data logging.
   - Return to idle state.

## 7 - MANUAL OPERATION
- A process flow diagram (PFD) is shown on the HMI.
- Tapping any solenoid symbol toggles that valve open or closed for manual testing or troubleshooting. Manual operation is only available when in idle mode.

## 8 - CALIBRATION & SPECIAL FUNCTIONS
- **Calibration:** Users can apply calibration offsets to pressure and temperature readings via the HMI.
- **Scale Zeroing:** Two individual manual zero buttons are available on the HMI, and an automatic scale zero command is issued at the start of each test.

