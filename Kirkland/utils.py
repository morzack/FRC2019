import time
import math

class MathFunctions:
    @staticmethod
    def clamp(i, mi, ma):
        """
        clamp a value between a min and max value
            :param i: number to clamp
            :param mi: min value
            :param ma: max value
        """
        return max(min(i, ma), mi)

class PIDController:
    def __init__(self, kP=1, kI=0, kD=0):
        """
        constructor
            :param self: 
            :param kP=1: kP value to use for this controller, default is 1
            :param kI=0: kI value, defualts to 0 (not in use)
            :param kD=0: kD value, defaults to 0 (not in use)
        """
        self.setpoint = 0
        self.measurement = 0

        self.kP = kP
        self.kI = kI
        self.kD = kD

        self.integral = 0
        self.previous_error = 0
        self.last_time = 0

    def reset(self):
        """
        reset the pid controller for reuse
            :param self: 
        """
        self.integral = 0
        self.previous_error = 0
        self.last_time = time.time()

    def set_setpoint_reset(self, setpoint):
        """
        set the setpoint of this pid controller and reset for reuse
            :param self: 
            :param setpoint: the setpoint of the controller
        """
        self.setpoint = setpoint
        self.reset()

    def pid(self, measurement):
        """
        calculate the output given the input measurement. should be called as frequently as possible while in use
            :param self: 
            :param meausrement: last reading from whatever is being used to make the measurementdef pid(self, meausrement)
        """
        self.measurement = measurement

        # calculate time in ms since last called
        current_time = time.time()
        dT = current_time - self.last_time
        if dT == 0:
            dT = 0.000000001

        # error = target - actual
        error = self.setpoint - self.measurement
        self.integral += (error * dT)
        derivative = (error - self.previous_error) / dT

        self.last_time = current_time

        self.previous_error = error

        a = self.kP * error + self.kI * self.integral + self.kD * derivative
        return a


class PIDToleranceController:
    def __init__(self, pidController, tolerance=1, timeout=3, timeStable=.5, gain=1, mi=-1, ma=1):
        """
        pid controller that runs based off of tolerances and timeouts
            :param self: 
            :param pidController: existing pid controller for holding k values
            :param tolerance=1: tolerance (in whatever unit is used) that should be held
            :param timeout=3: timeout for this method, if time is up then it considers the pid loop to be over
            :param timeStable=.5: time to stay within the tolerances
            :param gain=1: linear constant applied to the pid output
            :param mi=-1: min value of output clamped
            :param ma=1: max value of output clamped
        """
        self.pidController = pidController
        self.tolerance = tolerance
        self.timeout = timeout
        self.timeStable = timeStable
        self.startTime = 0
        self.lastTimeNotInTolerance = self.startTime
        self.gain = gain
        self.min = mi
        self.max = ma
        self.started = False

    def start(self, setpoint, tolerance, timeout, timeStable):
        """
        start the controller and asign a setpoint
            :param self: 
            :param setpoint:
            :param tolerance: tolerance to use
            :param timeout: timeout for this controller
            :param timeStable: time to remain stable
        """
        self.tolerance = tolerance
        self.timeout = timeout
        self.timeStable = timeStable
        self.pidController.set_setpoint_reset(setpoint)
        self.startTime = time.time()
        self.lastTimeNotInTolerance = self.startTime
        self.started = True

    def updateConstants(self, kP=0, kI=0, kD=0):
        self.pidController.kP = kP
        self.pidController.kI = kI
        self.pidController.kD = kD

    def kill(self):
        self.started = False

    def isDone(self):
        """
        see if the controller is done, as in the timer is exipired or its stayed within tolerance for long enough
            :param self: 
        """
        if time.time() > self.startTime+self.timeout:
            return True
        if time.time()-self.lastTimeNotInTolerance > self.timeStable:
            return True
        if not self.started:
            return False
        return False

    def getOutput(self, i):
        """
        get the output from the pid controller with clamping and gain calculated
            :param self: 
            :param i: input to be compared with setpoint
        """
        if self.isDone():
            return 0
        if abs(self.pidController.previous_error) > self.tolerance:
            self.lastTimeNotInTolerance = time.time()
        return MathFunctions.clamp(self.pidController.pid(i)*self.gain, self.min, self.max)

class State:
    def __init__(self):
        pass

class TimedState(State):
    def __init__(self, duration, method):
        # so the python magic here is passing in a function as the method variable
        self.timer = Timer()
        self.duration = duration
        self.method = method

    def start(self):
        self.timer.start()
        self.method()

    def abort(self):
        self.endTime = 0

    def isRunning(self):
        if self.timer.update() > self.duration:
            return False
        return True

    def execute(self):
        if self.isRunning():
            self.method()

class TimedStateRunner:
    def __init__(self, states):
        self.states = states
        self.currentState = 0
        self.running = False

    def start(self):
        self.running = True
        self.states[0].start()
    
    def abort(self):
        self.running = False
    
    def reset(self):
        self.currentState = 0
        self.running = False

    def execute(self):
        if self.running:
            if self.currentState >= len(self.states):
                self.abort()
            elif self.states[self.currentState].isRunning():
                self.states[self.currentState].execute()
            else:
                self.currentState += 1
                if self.currentState < len(self.states):
                    self.states[self.currentState].start()

class TimedStateRunnerChooser:
    def __init__(self, runnerTrue, runnerFalse, choiceMethod):
        self.runnerTrue = runnerTrue
        self.runnerFalse = runnerFalse
        self.choose = choiceMethod
        self.choice = -1

    def start(self):
        if self.choose() == False:
            self.runnerFalse.start()
            self.choice = 0
        else:
            self.runnerTrue.start()
            self.choice = 1

    def abort(self):
        if self.choice == 0:
            self.runnerFalse.abort()
        if self.choice == 1:
            self.runnerTrue.abort()
        
    def reset(self):
        if self.choice == 0:
            self.runnerFalse.reset()
        if self.choice == 1:
            self.runnerTrue.reset()

    def execute(self):
        if self.choice == -1:
            self.start()
        if self.choice == 0:
            self.runnerFalse.execute()
        if self.choice == 1:
            self.runnerTrue.execute()

class Timer:
    def __init__(self):
        self.startTime = 0
    
    def start(self):
        self.startTime = time.time()

    def update(self):
        return time.time()-self.startTime