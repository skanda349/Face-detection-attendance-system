import cv2
import face_recognition
import pickle
import time
from datetime import date
from database import connect
from face_utils import compare_faces, get_ear, EAR_THRESHOLD

def login_user(userId, email):
    try:
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("SELECT userId, email, face_encoding FROM user")
        rows = cursor.fetchall()

        if not rows:
            conn.close()
            return False, "No registered users found in database."

        known_encodings = []
        known_ids = []
        for r in rows:
            known_ids.append((r[0], r[1]))
            known_encodings.append(pickle.loads(r[2]))

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            conn.close()
            return False, "Camera not accessible."

        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Warm up
        for _ in range(5):
            cap.read()

        cv2.namedWindow("Attendance - Face Recognition", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Attendance - Face Recognition", 640, 480)

        marked_today = set()
        marked_names = []
        success_time = None
        already_marked_user = None
        CLOSE_AFTER = 2.0
        blink_state = {}

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Success overlay
            if success_time is not None:
                elapsed = time.time() - success_time
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]),
                              (0, 40, 0), cv2.FILLED)
                cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
                cv2.putText(frame, "Attendance Marked!",
                            (frame.shape[1]//2 - 160, frame.shape[0]//2 - 20),
                            cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 255, 100), 2)
                cv2.putText(frame, ", ".join(marked_names),
                            (frame.shape[1]//2 - 120, frame.shape[0]//2 + 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                bar_w = int(frame.shape[1] * min(elapsed / CLOSE_AFTER, 1.0))
                cv2.rectangle(frame, (0, frame.shape[0] - 8),
                              (bar_w, frame.shape[0]), (0, 255, 100), cv2.FILLED)
                cv2.imshow("Attendance - Face Recognition", frame)
                cv2.waitKey(1)
                if elapsed >= CLOSE_AFTER:
                    break
                continue

            # Already-marked error overlay
            if already_marked_user is not None:
                elapsed = time.time() - already_marked_user[1]
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]),
                              (0, 0, 60), cv2.FILLED)
                cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
                cv2.putText(frame, "Already Marked Today!",
                            (frame.shape[1]//2 - 190, frame.shape[0]//2 - 20),
                            cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 100, 255), 2)
                cv2.putText(frame, already_marked_user[0],
                            (frame.shape[1]//2 - 120, frame.shape[0]//2 + 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                bar_w = int(frame.shape[1] * min(elapsed / CLOSE_AFTER, 1.0))
                cv2.rectangle(frame, (0, frame.shape[0] - 8),
                              (bar_w, frame.shape[0]), (0, 100, 255), cv2.FILLED)
                cv2.imshow("Attendance - Face Recognition", frame)
                cv2.waitKey(1)
                if elapsed >= CLOSE_AFTER:
                    break
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb)
            face_encodings = face_recognition.face_encodings(rgb, face_locations)
            landmarks_list = face_recognition.face_landmarks(rgb, face_locations)

            active_keys = set(range(len(face_locations)))
            for k in list(blink_state.keys()):
                if k not in active_keys:
                    del blink_state[k]

            for i, ((top, right, bottom, left), encoding, lm) in enumerate(
                    zip(face_locations, face_encodings, landmarks_list)):

                state = blink_state.setdefault(i, {"closed": False, "blinked": False})

                ear = get_ear(lm)
                if ear < EAR_THRESHOLD:
                    state["closed"] = True
                elif state["closed"]:
                    state["blinked"] = True
                    state["closed"]  = False

                if not state["blinked"]:
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 165, 255), 2)
                    cv2.rectangle(frame, (left, bottom), (right, bottom + 28),
                                  (0, 165, 255), cv2.FILLED)
                    cv2.putText(frame, "Blink to verify", (left + 6, bottom + 20),
                                cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 0, 0), 1)
                    continue

                match_index = compare_faces(known_encodings, encoding)

                if match_index is not None:
                    uid, mail = known_ids[match_index]
                    today = str(date.today())

                    if (uid, today) not in marked_today:
                        cursor.execute("""
                        SELECT 1 FROM attendance WHERE userId=%s AND date=%s
                        """, (uid, today))
                        already_marked = cursor.fetchone()

                        if already_marked:
                            marked_today.add((uid, today))
                            already_marked_user = (uid, time.time())
                            continue

                        cursor.execute("""
                        INSERT INTO attendance (userId, email, date, attendance_status)
                        VALUES (%s, %s, %s, %s)
                        """, (uid, mail, today, "Present"))
                        conn.commit()
                        marked_today.add((uid, today))
                        marked_names.append(uid)
                        success_time = time.time()

                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    cv2.rectangle(frame, (left, bottom), (right, bottom + 28),
                                  (0, 255, 0), cv2.FILLED)
                    cv2.putText(frame, f"{uid}  Present", (left + 6, bottom + 20),
                                cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 0, 0), 1)
                else:
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                    cv2.rectangle(frame, (left, bottom), (right, bottom + 28),
                                  (0, 0, 255), cv2.FILLED)
                    cv2.putText(frame, "Unknown", (left + 6, bottom + 20),
                                cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

            cv2.putText(frame, "ESC to cancel",
                        (10, frame.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
            cv2.imshow("Attendance - Face Recognition", frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break

        cap.release()
        conn.close()
        cv2.destroyAllWindows()

        if marked_names:
            return True, f"Attendance marked for: {', '.join(marked_names)}."
        if already_marked_user:
            return False, f"Attendance already marked for '{already_marked_user[0]}' today."
        return False, "No matching face recognized."

    except Exception as e:
        return False, f"Error: {str(e)}"
