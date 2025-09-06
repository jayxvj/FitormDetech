from dataclasses import dataclass

@dataclass
class CounterState:
    reps: int = 0
    good_reps: int = 0
    phase: str = "not_ready"   # 'not_ready', 'up', 'down'
    down_frames: int = 0
    last_feedback: str = "Get into starting position..."

class BaseExerciseCounter:
    def __init__(self, down_threshold, up_threshold, torso_check_fn=None,
                 min_down_hold_frames=3, min_range_of_motion=40, min_rep_frames=10):
        self.down_threshold = down_threshold
        self.up_threshold = up_threshold
        self.state = CounterState()
        self.min_down_hold_frames = min_down_hold_frames
        self.min_range_of_motion = min_range_of_motion
        self.min_rep_frames = min_rep_frames
        self.torso_check_fn = torso_check_fn

        # Internal trackers
        self.last_down_angle = None
        self.rep_frame_counter = 0

    def update(self, primary_angle, torso_angle=None):
        fb = ""
        self.rep_frame_counter += 1

        if primary_angle is None:
            self.state.last_feedback = "Move into frame"
            return self.state

        # Ready check
        if self.state.phase == "not_ready":
            if primary_angle >= self.up_threshold:
                if self.torso_check_fn and not self.torso_check_fn(torso_angle):
                    self.state.last_feedback = "Adjust body orientation"
                else:
                    self.state.phase = "up"
                    self.state.last_feedback = "Ready ✅ Start exercise"
                    self.rep_frame_counter = 0
            else:
                self.state.last_feedback = "Get into starting position..."
            return self.state

        # Up → going down
        if self.state.phase == "up":
            if primary_angle <= self.down_threshold:
                self.state.phase = "down"
                self.state.down_frames = 1
                self.last_down_angle = primary_angle
                self.rep_frame_counter = 0
                fb = "Good depth" if primary_angle < (self.down_threshold - 5) else "Go a bit lower"
            else:
                fb = "Go lower"

        # Down → going up
        elif self.state.phase == "down":
            if primary_angle <= self.down_threshold:
                self.state.down_frames += 1
                self.last_down_angle = primary_angle
            if primary_angle >= self.up_threshold:
                # ✅ Check stricter conditions
                rom_ok = abs(self.up_threshold - self.last_down_angle) >= self.min_range_of_motion
                time_ok = self.rep_frame_counter >= self.min_rep_frames
                hold_ok = self.state.down_frames >= self.min_down_hold_frames

                if rom_ok and time_ok:
                    self.state.reps += 1
                    if hold_ok:
                        self.state.good_reps += 1
                    fb = "Rep counted ✅"
                else:
                    fb = "Bad rep (too shallow/too fast)"
                self.state.phase = "up"
                self.rep_frame_counter = 0
                self.state.down_frames = 0
            else:
                fb = "Hold… then extend"

        self.state.last_feedback = fb
        return self.state


# ✅ Squats should have torso vertical
def squat_torso_check(torso_angle):
    if torso_angle is None:
        return False
    return 160 <= torso_angle <= 180  # upright


# ✅ Push-ups should have torso horizontal
def pushup_torso_check(torso_angle):
    if torso_angle is None:
        return False
    return 150 <= torso_angle <= 180  # plank-ish


class SquatCounter(BaseExerciseCounter):
    def __init__(self, down_threshold=95, up_threshold=165,
                 min_down_hold_frames=3, min_hip_drop=0.2, min_torso_angle=150):
        super().__init__(down_threshold, up_threshold,
                         torso_check_fn=None,
                         min_down_hold_frames=min_down_hold_frames)
        self.min_hip_drop = min_hip_drop
        self.min_torso_angle = min_torso_angle
        self.hip_y_standing = None
        self.hip_y_lowest = None

    def update(self, knee_angle, torso_angle=None, hip_y=None, shoulder_y=None):
        state = super().update(knee_angle, torso_angle)

        if hip_y is not None and shoulder_y is not None:
            # Reset standing position
            if self.state.phase == "up":
                if self.hip_y_standing is None or hip_y < self.hip_y_standing:
                    self.hip_y_standing = hip_y
                self.hip_y_lowest = None
            elif self.state.phase == "down":
                if self.hip_y_lowest is None or hip_y > self.hip_y_lowest:
                    self.hip_y_lowest = hip_y

            # On rep completion, validate depth + torso
            if self.state.last_feedback == "Rep counted ✅":
                if self.hip_y_standing is not None and self.hip_y_lowest is not None:
                    drop = self.hip_y_lowest - self.hip_y_standing
                    torso_ok = (torso_angle is not None and torso_angle > self.min_torso_angle)
                    depth_ok = drop >= self.min_hip_drop

                    if not torso_ok:
                        self.state.reps -= 1
                        self.state.good_reps -= 1
                        self.state.last_feedback = "Bad rep (leaning forward)"
                    elif not depth_ok:
                        self.state.reps -= 1
                        self.state.good_reps -= 1
                        self.state.last_feedback = "Bad rep (not enough depth)"
        return self.state


class PushupCounter(BaseExerciseCounter):
    def __init__(self, down_threshold=95, up_threshold=165,
                 min_down_hold_frames=3, min_shoulder_drop=0.15):
        super().__init__(down_threshold, up_threshold,
                         torso_check_fn=pushup_torso_check,
                         min_down_hold_frames=min_down_hold_frames)
        self.min_shoulder_drop = min_shoulder_drop
        self.shoulder_y_highest = None
        self.shoulder_y_lowest = None

    def update(self, elbow_angle, torso_angle=None, shoulder_y=None):
        state = super().update(elbow_angle, torso_angle)

        # Track shoulder movement
        if shoulder_y is not None:
            if self.state.phase == "up":
                # Reset at plank
                if self.shoulder_y_highest is None or shoulder_y < self.shoulder_y_highest:
                    self.shoulder_y_highest = shoulder_y
                self.shoulder_y_lowest = None
            elif self.state.phase == "down":
                if self.shoulder_y_lowest is None or shoulder_y > self.shoulder_y_lowest:
                    self.shoulder_y_lowest = shoulder_y

            # On rep completion, check shoulder drop
            if self.state.last_feedback == "Rep counted ✅":
                if self.shoulder_y_highest is not None and self.shoulder_y_lowest is not None:
                    drop = self.shoulder_y_lowest - self.shoulder_y_highest
                    if drop < self.min_shoulder_drop:
                        # Cancel this rep
                        self.state.reps -= 1
                        self.state.good_reps -= 1
                        self.state.last_feedback = "Bad rep (not enough depth)"
        return self.state