import face_recognition
import numpy as np
from scipy.spatial import distance as dist

def encode_faces(image):
    return face_recognition.face_encodings(image)


def compare_faces(known_encodings, unknown_encoding):
    if len(known_encodings) == 0:
        return None

    distances = face_recognition.face_distance(known_encodings, unknown_encoding)
    best_match = np.argmin(distances)

    if distances[best_match] < 0.5:
        return best_match

    return None


EAR_THRESHOLD = 0.25

def eye_aspect_ratio(eye_points):
    A = dist.euclidean(eye_points[1], eye_points[5])
    B = dist.euclidean(eye_points[2], eye_points[4])
    C = dist.euclidean(eye_points[0], eye_points[3])
    return (A + B) / (2.0 * C)


def get_ear(landmarks):
    left  = np.array(landmarks["left_eye"])
    right = np.array(landmarks["right_eye"])
    return (eye_aspect_ratio(left) + eye_aspect_ratio(right)) / 2.0
