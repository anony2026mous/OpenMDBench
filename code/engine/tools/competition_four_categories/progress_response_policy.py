"""Own-velocity feedback for response navigation; no environment oracle."""
import math

from .standing_response_policy import StandingResponsePolicy

SETTINGS = {"initial_gain": 1.0, "minimum_gain": .25, "smoothing": .5,
    "stable_command_tolerance_mps": 1.0, "stable_velocity_tolerance_mps": 2.0,
    "maximum_command_speed_mps": 80.0}


class ProgressResponsePolicy(StandingResponsePolicy):
    def __init__(self, brief, identifier, mode="progress-watch"):
        if mode != "progress-watch":
            raise ValueError("progress response requires its declared mode")
        super().__init__(brief, identifier)
        self.motion_gain = SETTINGS["initial_gain"]
        self.gain_samples = 0
        self.previous_command = self.older_command = self.previous_speed = None

    def command(self, observation):
        owned = observation["own_entities"]
        if (not owned or len(owned) != 1 or owned[0]["entity_id"] != self.identifier
            or observation["tick"] <= self.last_tick):
            return super().command(observation)
        velocity = owned[0].get("velocity_mps")
        measured = None
        if (isinstance(velocity, (list, tuple)) and len(velocity) == 3
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in velocity)):
            measured = math.hypot(velocity[0], velocity[1])
        if (measured is not None and measured > 2.0 and self.previous_speed is not None
            and self.previous_command is not None and self.older_command is not None
            and self.previous_command > 3.0
            and abs(self.previous_command-self.older_command) <= SETTINGS["stable_command_tolerance_mps"]
            and abs(measured-self.previous_speed) <= SETTINGS["stable_velocity_tolerance_mps"]):
            observed_gain = max(SETTINGS["minimum_gain"], min(1., measured/self.previous_command))
            alpha = SETTINGS["smoothing"]
            self.motion_gain = (1-alpha)*self.motion_gain + alpha*observed_gain
            self.gain_samples += 1
        command = super().command(observation)
        self.previous_speed = measured
        self.older_command, self.previous_command = self.previous_command, None if command is None else command["speed_mps"]
        return command

    def _navigate(self, position, goal, altitude, key):
        command = super()._navigate(position, goal, altitude, key)
        if command["speed_mps"] > 0:
            command["speed_mps"] = min(SETTINGS["maximum_command_speed_mps"], command["speed_mps"]/self.motion_gain)
        return command
