import cv2
import numpy as np
import mediapipe as mp

from config import (
    SQUAT_DOWN_ANGLE, SQUAT_UP_ANGLE,
    PUSHUP_DOWN_ANGLE, PUSHUP_UP_ANGLE,
    MIN_DOWN_HOLD_FRAMES, SHOW_SKELETON_DEFAULT, WINDOW_NAME
)
from pose_utils import safe_angle
from exercises import SquatCounter, PushupCounter

mp_drawing = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles
mp_pose = mp.solutions.pose

POSE_LM = mp_pose.PoseLandmark

# Landmarks
L_HIP, L_KNEE, L_ANKLE = POSE_LM.LEFT_HIP.value, POSE_LM.LEFT_KNEE.value, POSE_LM.LEFT_ANKLE.value
R_HIP, R_KNEE, R_ANKLE = POSE_LM.RIGHT_HIP.value, POSE_LM.RIGHT_KNEE.value, POSE_LM.RIGHT_ANKLE.value
L_SHOULDER, L_ELBOW, L_WRIST = POSE_LM.LEFT_SHOULDER.value, POSE_LM.LEFT_ELBOW.value, POSE_LM.LEFT_WRIST.value
R_SHOULDER, R_ELBOW, R_WRIST = POSE_LM.RIGHT_SHOULDER.value, POSE_LM.RIGHT_ELBOW.value, POSE_LM.RIGHT_WRIST.value

def draw_hud(frame, mode, reps, good_reps, feedback, show_skeleton):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (10, 10), (w-10, 120), (0,0,0), thickness=-1)
    cv2.addWeighted(frame[10:120, 10:w-10], 0.4, np.zeros_like(frame[10:120, 10:w-10]), 0.6, 0, frame[10:120, 10:w-10])
    cv2.putText(frame, f"Mode: {mode}", (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,255,255), 2)
    cv2.putText(frame, f"Reps: {reps}  (Good: {good_reps})", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)
    cv2.putText(frame, f"{feedback}", (w//2, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,255,0), 2)
    cv2.putText(frame, f"[1] Squats  [2] Push-ups  [s] Toggle skeleton  [q] Quit", (20, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1)
    if not show_skeleton:
        cv2.putText(frame, "Skeleton: OFF", (w-200, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100,100,255), 2)

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Cannot open webcam.")
        return

    mode = "Squats"
    squat_counter = SquatCounter(SQUAT_DOWN_ANGLE, SQUAT_UP_ANGLE, MIN_DOWN_HOLD_FRAMES)
    pushup_counter = PushupCounter(PUSHUP_DOWN_ANGLE, PUSHUP_UP_ANGLE, MIN_DOWN_HOLD_FRAMES)
    show_skeleton = SHOW_SKELETON_DEFAULT

    with mp_pose.Pose(
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.5
    ) as pose:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb)

            knee_angle = elbow_angle = None
            squat_torso_angle = pushup_torso_angle = None
            hip_y = shoulder_y = None

            if results.pose_landmarks:
                lms = results.pose_landmarks.landmark

                # Squat → knee angle (min of both)
                left_knee = safe_angle(lms, w, h, L_HIP, L_KNEE, L_ANKLE)
                right_knee = safe_angle(lms, w, h, R_HIP, R_KNEE, R_ANKLE)
                knee_angle = min(x for x in [left_knee, right_knee] if x is not None) if left_knee or right_knee else None

                # Push-up → elbow angle (min of both)
                left_elbow = safe_angle(lms, w, h, L_SHOULDER, L_ELBOW, L_WRIST)
                right_elbow = safe_angle(lms, w, h, R_SHOULDER, R_ELBOW, R_WRIST)
                elbow_angle = min(x for x in [left_elbow, right_elbow] if x is not None) if left_elbow or right_elbow else None

                # ✅ Torso orientation
                squat_torso_angle = safe_angle(lms, w, h, L_SHOULDER, L_HIP, L_KNEE)
                pushup_torso_angle = safe_angle(lms, w, h, L_SHOULDER, L_HIP, L_ANKLE)

                # ✅ Hip Y for squats
                hip_y = (lms[L_HIP].y + lms[R_HIP].y) / 2

                # ✅ Shoulder Y for push-ups
                shoulder_y = (lms[L_SHOULDER].y + lms[R_SHOULDER].y) / 2

                if show_skeleton:
                    mp_drawing.draw_landmarks(
                        frame,
                        results.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS,
                        landmark_drawing_spec=mp_styles.get_default_pose_landmarks_style()
                    )

            # Update counters
            if mode == "Squats":
                st = squat_counter.update(knee_angle, torso_angle=squat_torso_angle, hip_y=hip_y, shoulder_y=shoulder_y)
            else:
                st = pushup_counter.update(elbow_angle, torso_angle=pushup_torso_angle, shoulder_y=shoulder_y)

            draw_hud(frame, mode, st.reps, st.good_reps, st.last_feedback, show_skeleton)

            cv2.imshow(WINDOW_NAME, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('1'):
                mode = "Squats"
            elif key == ord('2'):
                mode = "Push-ups"
            elif key == ord('s'):
                show_skeleton = not show_skeleton

    cap.release()
    cv2.destroyAllWindows()

    print("\n===== Workout Summary =====")
    print(f"Squats: {squat_counter.state.reps}  (Good: {squat_counter.state.good_reps})")
    print(f"Push-ups: {pushup_counter.state.reps}  (Good: {pushup_counter.state.good_reps})")
    total_reps = squat_counter.state.reps + pushup_counter.state.reps
    total_good = squat_counter.state.good_reps + pushup_counter.state.good_reps
    if total_reps > 0:
        print(f"Overall form quality: {int(100*total_good/max(1,total_reps))}%")

if __name__ == "__main__":
    main()