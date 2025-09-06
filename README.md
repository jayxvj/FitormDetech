# Exercise Form Analysis — MVP (24‑Hour Build)

This is a minimal, working prototype that detects **squats** and **push-ups** from your webcam,
counts reps, and gives simple real-time feedback using **MediaPipe Pose + OpenCV**.

## 1) Install
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

If you face issues installing `mediapipe` on Apple Silicon or Linux, ensure Python 3.9–3.11 and `pip` are up to date.

## 2) Run
```bash
python main.py
```
Keys inside the app:
- `1` → Squats mode
- `2` → Push-ups mode
- `s` → Show/Hide skeleton
- `q` → Quit

## 3) What it does
- Uses your webcam to detect pose landmarks in real time.
- Tracks **knee angle** (squats) and **elbow angle** (push-ups).
- Counts reps when you go **down → up** through thresholds.
- Shows **“Good / Needs to go lower / Extend fully”** messages.
- Prints a simple **Workout Summary** on exit.

## 4) Notes
- Ensure you’re fully visible to the camera.
- Good lighting improves detection accuracy.
- For push-ups, angle works best in **side view**.
- This is an MVP; thresholds are approximate and may need tuning for your body/mechanics.

## 5) Next Steps (beyond MVP)
- Add more exercises (lunges, planks, bicep curls).
- Voice feedback (pyttsx3) and sound cues.
- Per-rep form scoring; charts & session history.
- Mobile app (React Native) using a lightweight pose model or MediaPipe Tasks.
- AR overlay guides and personalized plans.
```
