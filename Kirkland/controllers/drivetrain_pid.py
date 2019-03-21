from magicbot import StateMachine, state, timed_state

from components.drivetrain import DriveModes, Drivetrain
from components.pneumatic_assemblies import Shifters

from wpilib import PIDController

class DriveStraightPID(StateMachine):
    drivetrain :            Drivetrain
    gearbox_shifters :      Shifters

    drive_forwards_pid :    PIDController

    def drive_distance(self, distance):
        self.drive_forwards_pid.setAbsoluteTolerance(0.5) # lets give it half an inch of tolerance
        self.drive_forwards_pid.setSetpoint(distance)

        self.drivetrain.stop_motors()
        self.drivetrain.reset_encoders()
        self.drivetrain.current_mode = DriveModes.PIDOPERATED

        self.engage()
        
    @state(first=True)
    def shift_gearboxes(self):
        self.gearbox_shifters.shift_down()
        
        self.next_state_now('start_drive')

    @timed_state(duration=1, must_finish=False)
    def start_drive(self):
        # basically reimplement the PID logic from before
        self.drive_forwards_pid.reset()
        self.drive_forwards_pid.enable()

        self.next_state_now('drive')
        
    @timed_state(duration=5)
    def drive(self):
        if self.drive_forwards_pid.onTarget():
            self.drive_forwards_pid.disable()
            self.drivetrain.stop_motors()
            self.drivetrain.driver_takeover()
            self.done()


class TurnPID(StateMachine):
    drivetrain :       Drivetrain
    gearbox_shifters : Shifters

    turn_pid :         PIDController

    def turn_distance(self, distance):
        self.turn_pid.setAbsoluteTolerance(2) # lets give it 2 degrees of tolerance
        self.turn_pid.setSetpoint(distance)

        self.drivetrain.stop_motors()
        self.drivetrain.reset_encoders()
        self.drivetrain.current_mode = DriveModes.PIDOPERATED

        self.engage()
        
    @state(first=True)
    def shift_gearboxes(self):
        self.gearbox_shifters.shift_down()
        
        self.next_state_now('start_turn')

    @timed_state(duration=1, must_finish=False)
    def start_turn(self):
        # basically reimplement the PID logic from before
        self.turn_pid.reset()
        self.turn_pid.enable()

        self.next_state_now('turn')
        
    @timed_state(duration=5)
    def turn(self):
        if self.turn_pid.onTarget():
            self.turn_pid.disable()
            self.drivetrain.stop_motors()
            self.drivetrain.driver_takeover()
            self.done()