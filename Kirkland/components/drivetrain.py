# drivetrain.py
# the code to control the drivetrain and shifters

from ctre import WPI_TalonSRX
from wpilib import SpeedControllerGroup, DoubleSolenoid
from wpilib.drive import DifferentialDrive
import navx

import robotmap
import utils

import enum
import math


class ShifterGear(enum.Enum):
    LOW_GEAR = enum.auto()
    HIGH_GEAR = enum.auto()


class Shifters:
    left_shifter_actuator: DoubleSolenoid
    right_shifter_actuator: DoubleSolenoid

    def __init__(self):
        # NOTE: make sure that the robot is forced into low gear at the start of a match
        self.gear = ShifterGear.LOW_GEAR

    def shift_up(self):
        self.gear = ShifterGear.HIGH_GEAR

    def shift_down(self):
        self.gear = ShifterGear.LOW_GEAR

    def toggle(self):
        self.gear = ShifterGear.LOW_GEAR if self.gear == ShifterGear.HIGH_GEAR else ShifterGear.HIGH_GEAR

    def execute(self):
        if self.gear == ShifterGear.LOW_GEAR:
            self.left_shifter_actuator.set(
                robotmap.Tuning.Drivetrain.Shifters.low_gear_state)
            self.right_shifter_actuator.set(
                robotmap.Tuning.Drivetrain.Shifters.low_gear_state)

        if self.gear == ShifterGear.HIGH_GEAR:
            self.left_shifter_actuator.set(
                robotmap.Tuning.Drivetrain.Shifters.high_gear_state)
            self.right_shifter_actuator.set(
                robotmap.Tuning.Drivetrain.Shifters.high_gear_state)


class DriveModes(enum.Enum):
    TANKDRIVE = enum.auto()
    ARCADEDRIVE = enum.auto()
    DRIVETOANGLE = enum.auto()


class Drivetrain:
    drivetrain_right_front: WPI_TalonSRX
    drivetrain_right_back: WPI_TalonSRX
    drivetrain_right_top: WPI_TalonSRX

    drivetrain_left_front: WPI_TalonSRX
    drivetrain_left_back: WPI_TalonSRX
    drivetrain_left_top: WPI_TalonSRX

    drivetrain_right_motors: SpeedControllerGroup
    drivetrain_left_motors: SpeedControllerGroup

    differential_drive: DifferentialDrive

    navx: navx.AHRS

    def __init__(self):
        self.drive_mode = DriveModes.ARCADEDRIVE

        self.left_power = 0
        self.right_power = 0

        self.speed = 0
        self.rotation = 0

        self.angle = 0

        self.turning_modifier = 1

    def arcade_drive(self, power, rotation):
        self.drive_mode = DriveModes.ARCADEDRIVE
        self.speed = power
        # self.speed = min(max(-0.5, power), 0.5)
        # self.speed = utils.clamp(power, -robotmap.Tuning.Drivetrain.motor_power_percentage_limit,
                                #  robotmap.Tuning.Drivetrain.motor_power_percentage_limit)
        self.rotation = rotation

    def tank_drive(self, left_power, right_power):
        self.drive_mode = DriveModes.TANKDRIVE
        self.left_power = left_power
        self.right_power = right_power
        # self.left_power = utils.clamp(left_power, -robotmap.Tuning.Drivetrain.motor_power_percentage_limit,
        #                               robotmap.Tuning.Drivetrain.motor_power_percentage_limit)
        # self.right_power = utils.clamp(right_power, -robotmap.Tuning.Drivetrain.motor_power_percentage_limit,
                                    #    robotmap.Tuning.Drivetrain.motor_power_percentage_limit)

    def drive_to_angle(self, power, angle=0):
        if self.drive_mode != DriveModes.DRIVETOANGLE:
            self.drive_mode = DriveModes.DRIVETOANGLE
            self.navx.reset()
        self.speed = power
        # self.speed = utils.clamp(power, -robotmap.Tuning.Drivetrain.motor_power_percentage_limit,
        #                          robotmap.Tuning.Drivetrain.motor_power_percentage_limit)
        rotation_error = self.navx.getAngle() - angle
        raw_rotation = rotation_error * robotmap.Tuning.Drivetrain.drive_straight_constant
        self.rotation = math.copysign(abs(raw_rotation)**.5, raw_rotation)

    def toggle_mode(self):
        if self.drive_mode == DriveModes.DRIVETOANGLE:
            self.drive_mode = DriveModes.ARCADEDRIVE
        self.drive_mode = DriveModes.TANKDRIVE if self.drive_mode == DriveModes.ARCADEDRIVE else DriveModes.ARCADEDRIVE

    def drive_straight(self, power):
        self.drive_to_angle(power, 0)

    def stop_motors(self):
        self.left_power = 0
        self.right_power = 0

        self.speed = 0
        self.rotation = 0

        self.differential_drive.stopMotor()

    def get_left_position(self):
        # NOTE: left_front is the one with the left encoder
        return -self.drivetrain_left_front.getQuadraturePosition() / robotmap.Physics.Drivetrain.ticks_per_inch

    def get_left_velocity(self):
        return -self.drivetrain_left_front.getQuadratureVelocity()

    def get_right_position(self):
        # NOTE: right_front has the right encoder
        return self.drivetrain_right_top.getQuadraturePosition() / robotmap.Physics.Drivetrain.ticks_per_inch

    def get_right_velocity(self):
        return self.drivetrain_right_top.getQuadratureVelocity()

    def get_average_position(self):
        return (self.get_left_position() + self.get_right_position()) / 2

    def get_average_velocity(self):
        return (self.get_left_velocity() + self.get_right_velocity()) / 2

    def reset_encoders(self):
        self.drivetrain_left_front.setQuadraturePosition(0)
        self.drivetrain_right_top.setQuadraturePosition(0)

    def execute(self):
        if self.drive_mode == DriveModes.TANKDRIVE:
            self.differential_drive.tankDrive(
                self.left_power, self.right_power)
        if self.drive_mode == DriveModes.ARCADEDRIVE:
            self.differential_drive.arcadeDrive(self.speed, self.rotation*self.turning_modifier)
        if self.drive_mode == DriveModes.DRIVETOANGLE:
            self.differential_drive.arcadeDrive(self.speed, self.rotation)


class DrivetrainMechanism:
    drivetrain: Drivetrain
    shifters: Shifters
    navx: navx.AHRS

    def __init__(self):
        pass

    def shift_up(self):
        if robotmap.Tuning.Drivetrain.shifting_speed_enabled:
            if abs(self.drivetrain.get_average_velocity()) > robotmap.Tuning.Drivetrain.min_shifting_speed:
                self.shifters.shift_up()
        else:
            self.shifters.shift_up()

    def shift_down(self):
        if robotmap.Tuning.Drivetrain.shifting_speed_enabled:
            if abs(self.drivetrain.get_average_velocity()) > robotmap.Tuning.Drivetrain.min_shifting_speed:
                self.shifters.shift_down()
        else:
            self.shifters.shift_down()

    def toggle_shift(self):
        if self.shifters.gear == ShifterGear.HIGH_GEAR:
            self.shift_down()
        else:
            self.shift_up()

    def execute(self):
        self.drivetrain.differential_drive.setMaxOutput(
            robotmap.Tuning.Drivetrain.low_gear_speed_limit if self.shifters.gear == ShifterGear.LOW_GEAR else robotmap.Tuning.Drivetrain.high_gear_speed_limit)

        self.drivetrain.turning_modifier = robotmap.Tuning.Drivetrain.low_gear_turning_modifier if self.shifters.gear != ShifterGear.LOW_GEAR else robotmap.Tuning.Drivetrain.high_gear_turning_modifier

    def reset(self):
        self.drivetrain.drive_mode = DriveModes.ARCADEDRIVE
        self.drivetrain.stop_motors()
        self.shifters.shift_down()
