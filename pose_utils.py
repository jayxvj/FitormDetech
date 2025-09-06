import math

def angle_between(a, b, c):
    """Return the angle ABC in degrees given three points (x,y).
    a, b, c are (x, y) tuples. Angle at point b between BA and BC.
    """
    try:
        bax = a[0] - b[0]
        bay = a[1] - b[1]
        bcx = c[0] - b[0]
        bcy = c[1] - b[1]
        ang1 = math.atan2(bay, bax)
        ang2 = math.atan2(bcy, bcx)
        ang = abs(ang2 - ang1)
        if ang > math.pi:
            ang = 2*math.pi - ang
        return math.degrees(ang)
    except Exception:
        return None

def get_point(landmarks, width, height, idx):
    """Convert normalized landmark at index `idx` to pixel coordinates (x, y)."""
    lm = landmarks[idx]
    return (int(lm.x * width), int(lm.y * height))

def safe_angle(landmarks, w, h, i1, i2, i3):
    """Compute angle at i2 using points i1-i2-i3; return None if any fails."""
    try:
        p1 = get_point(landmarks, w, h, i1)
        p2 = get_point(landmarks, w, h, i2)
        p3 = get_point(landmarks, w, h, i3)
        return angle_between(p1, p2, p3)
    except Exception:
        return None
