1 - INTRODUCTION
The Pencil Module Filtration Test System is designed to automate and log performance data for filtration cycles. It facilitates the precise control and monitoring of filter and backwash processes, enabling repeatable test sequences. The system integrates pressure and temperature sensing, weight measurement, and manual and automatic operation modes via an HMI interface.
2 - PROCESS OBJECTIVE
The system performs automated filtration cycles on pencil module filters. It logs:
•Influent temperature
•Backwash supply pressure
•Influent supply pressure
•Weight of collected effluent and backwash water
•Operator-entered setpoints
•Timestamps for each data point
The data is used to assess filtration and backwash performance over repeated cycles.
3 - INPUTS: 
SignalTypeDescription
Influent Supply PressurePITMonitors influent supply tank pressure
Backwash Supply PressurePITMonitors backwash supply tank pressure
Influent TemperatureRTDMeasures influent temperature
Effluent WeightScaleMeasures filtered effluent
Backwash WeightScaleMeasures backwash water output
Setpoints/Input ControlsHMIOperator-configurable values (see Section 5)
Prime ButtonHMIStarts priming routine
Start/Stop Test ButtonHMIBegins/Stops automated cycle
Calibration ButtonHMIApplies offset to pressure/temp readings
Manual Zero ButtonsHMIZeros each scale individually from idle

4 - OUTPUTS: 
DeviceTypeFunction
Influent Supply ValveSolenoidControls influent supply flow
Backwash Supply ValveSolenoidControls backwash supply flow
Effluent ValveSolenoidControls effluent flow
Backwash Effluent ValveSolenoidControls backwash effluent flow
Influent Water Drain ValveSolenoidDrains influent line during refill
Scale Zero CommandDigitalZeros both scales at test start

5 - SETPOINTS AND OPERATOR INPUTS (VIA HMI)
•Filtration Target: Either Time (sec) or Volume (mL)
•Backwash Target: Either Time (sec) or Volume (mL)
•Purge Time: Duration in seconds
•Cycle Count: Number of full cycles to perform
•Calibration Offsets: Manual offset values for pressure and temperature
•Sample Time: Logging interval in seconds
•Project Name: Name of project for log files

6 - SEQUENCE OF OPERATION
Start Test
1.Operator presses Start Test
2.System issues zeroing command to both scales
3.Data log file created [Project Name]_[Date]_[Time] 
4.Settings log file created [Project Name]_[Date]_[Time]
5.Data logging begins at the interval defined by the Sample Time setpoint
Automated Test Cycle
The following steps repeat for the number of cycles defined in the Cycle Count setpoint:
A.Refill Phase
1.Activate: Influent Supply Valve and Influent Water Drain Valve
2.Run for duration set by Purge Time
3.Deactivate valves after time elapses
B.Filtration Phase
1.Activate: Influent Supply Valve and Effluent Valve
2.Depending on mode. flow continues until the following condition is met:
1.Filtration time = Filtration Time Setpoint, OR
2.Effluent weight = Effluent Volume Setpoint
C.Backwash Phase
1.Activate: Backwash Supply Valve and Backwash Effluent Valve
2.Direct water through backwash line to backwash collection
3.Depending on mode. flow continues until the following condition is met:
1.Backwash time = Backwash Time Setpoint, OR
2.Backwash weight = Backwash Volume Setpoint
D.Cycle Completion
4.Loop above until Cycle Count is reached
5.Stop all outputs
6.End data logging
7.Return to idle state
7 - MANUAL OPERATION (IDLE MODE ONLY)
•A process flow diagram (PFD) is shown on the HMI.
•Tapping any solenoid symbol on the HMI toggles that valve open/closed for manual testing or troubleshooting.
8 - CALIBRATION & SPECIAL FUNCTIONS
•Calibration: User can apply calibration offsets to pressure and temperature readings via HMI.
•Scale Zeroing: Two individual manual zero buttons on the HMI, and an automatic scale zero command issued at the start of each test.
