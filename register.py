import cv2
import pickle
import time
import face_recognition
from database import connect
from face_utils import get_ear, EAR_THRESHOLD

def register_user(userId, email):
    try:
        # Check if user already exists
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("SELECT userId FROM user WHERE userId = %s OR email = %s", (userId, email))
        existing = cursor.fetchone()
        conn.close()
        
        if existing:
            return False, f"User '{userId}' or email '{email}' is already registered."
        
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return False, "Camera not accessible."

        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Warm up
        for _ in range(5):
            cap.read()

        cv2.namedWindow("Register - Face Capture", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Register - Face Capture", 640, 480)

        blinked      = False
        eye_closed   = False
        captured     = False
        HOLD_SECONDS = 2
        face_detected_since = None

        while True:
            ret, frame = cap.read()
            if not ret:
                cap.release()
                cv2.destroyAllWindows()
                return False, "Failed to read from camera."

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb)
            landmarks_list = face_recognition.face_landmarks(rgb, face_locations)

            if face_locations and landmarks_list:
                top, right, bottom, left = face_locations[0]
                lm = landmarks_list[0]

                ear = get_ear(lm)
                if ear < EAR_THRESHOLD:
                    eye_closed = True
                elif eye_closed:
                    blinked    = True
                    eye_closed = False

                liveness_color = (0, 255, 0) if blinked else (0, 165, 255)
                liveness_text  = "Liveness OK" if blinked else "Please blink to verify liveness"
                cv2.putText(frame, liveness_text, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, liveness_color, 2)

                elapsed = 0
                if blinked:
                    if face_detected_since is None:
                        face_detected_since = time.time()
                    else:
                        elapsed = time.time() - face_detected_since
                else:
                    face_detected_since = None

                progress  = min(elapsed / HOLD_SECONDS, 1.0)
                bar_width = int((right - left) * progress)

                cv2.rectangle(frame, (left, top), (right, bottom), liveness_color, 2)
                cv2.rectangle(frame, (left, bottom + 4),
                              (left + bar_width, bottom + 12), liveness_color, cv2.FILLED)
                cv2.rectangle(frame, (left, bottom + 4),
                              (right, bottom + 12), liveness_color, 1)

                remaining = max(0, HOLD_SECONDS - elapsed)
                label = f"Hold still... {remaining:.1f}s" if progress < 1.0 else "Capturing..."
                cv2.putText(frame, label, (left, top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, liveness_color, 2)

                if blinked and elapsed >= HOLD_SECONDS and not captured:
                    captured  = True
                    encodings = face_recognition.face_encodings(rgb, face_locations)

                    if not encodings:
                        cap.release()
                        cv2.destroyAllWindows()
                        return False, "Face detected but encoding failed. Try again."

                    conn = connect()
                    cursor = conn.cursor()
                    for encoding in encodings:
                        blob = pickle.dumps(encoding)
                        cursor.execute("""
                        INSERT INTO user (userId, email, face_encoding)
                        VALUES (%s, %s, %s)
                        """, (userId, email, blob))
                    conn.commit()
                    conn.close()

                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 4)
                    cv2.putText(frame, "Registered!", (left, top - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.imshow("Register - Face Capture", frame)
                    cv2.waitKey(1000)

                    cap.release()
                    cv2.destroyAllWindows()
                    return True, f"{len(encodings)} face(s) registered for '{userId}'."

            else:
                face_detected_since = None
                cv2.putText(frame, "No face detected. Please look at the camera.",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            cv2.putText(frame, "ESC to cancel", (10, frame.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
            cv2.imshow("Register - Face Capture", frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break

        cap.release()
        cv2.destroyAllWindows()
        return False, "Registration cancelled."

    except Exception as e:
        return False, f"Error: {str(e)}"
