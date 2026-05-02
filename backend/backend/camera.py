import cv2
import threading
import mediapipe as mp
import numpy as np
import joblib
import pyttsx3
from collections import Counter
import os
from django.conf import settings
import sys

# Add the 1_Models folder to sys.path so we can import sign_utils
MODELS_DIR = os.path.join(settings.BASE_DIR.parent, 'Main_Folder', '1_Models')
sys.path.append(MODELS_DIR)

from sign_utils import normalize_landmarks

# Global Initialization
engine_lock = threading.Lock() 

def speak_task(text_to_say):
    with engine_lock:
        try:
            import pythoncom
            pythoncom.CoInitialize()
            local_engine = pyttsx3.init()
            local_engine.setProperty('rate', 150)
            local_engine.say(text_to_say)
            local_engine.runAndWait()
        except Exception as e:
            print(f"Audio Error: {e}")
        finally:
            try:
                pythoncom.CoUninitialize()
            except:
                pass

from translations.models import TranslationHistory

class VideoCamera(object):
    def __init__(self, user_email='guest@example.com'):
        self.user_email = user_email
        self.video = cv2.VideoCapture(0)
        
        # Load the 'Brain' and 'Dictionary'
        self.model = joblib.load(os.path.join(MODELS_DIR, 'model_v132.joblib'))
        self.label_encoder = joblib.load(os.path.join(MODELS_DIR, 'label_encoder_v132.joblib'))
        
        # MediaPipe Configuration
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False, 
            max_num_hands=1, 
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # State Variables
        self.sentence = ""
        self.prediction_buffer = [] 
        self.BUFFER_SIZE = 20

    def __del__(self):
        self.video.release()

    def get_frame(self):
        ret, frame = self.video.read()
        if not ret:
            return None

        frame = cv2.flip(frame, 1)
        H, W, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        current_pred = "No Hand Detected"

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

                landmarks = normalize_landmarks(hand_landmarks)

                prediction = self.model.predict([landmarks])
                current_pred = self.label_encoder.inverse_transform(prediction)[0]

                self.prediction_buffer.append(current_pred)
                if len(self.prediction_buffer) > self.BUFFER_SIZE:
                    self.prediction_buffer.pop(0)

                most_common = Counter(self.prediction_buffer).most_common(1)[0]
                if most_common[1] >= 15:
                    stable_char = most_common[0]

                    if stable_char.lower() == 'space':
                        if self.sentence.strip() != "":
                            threading.Thread(target=speak_task, args=(self.sentence,), daemon=True).start()
                            try:
                                TranslationHistory.objects.create(user_email=self.user_email, text=self.sentence.strip())
                            except Exception as e:
                                print(f"DB Error: {e}")
                            self.sentence = "" 
                            self.prediction_buffer = []
                    
                    elif stable_char.lower() in ['nothing', 'none']:
                        pass 
                    
                    else:
                        if not self.sentence or self.sentence[-1] != stable_char:
                            self.sentence += stable_char

        # UI Overlay
        cv2.rectangle(frame, (0, 0), (W, 90), (45, 45, 45), -1) 
        cv2.putText(frame, f"SIGN: {current_pred}", (15, 35), 
                    cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, f"TEXT: {self.sentence}", (15, 75), 
                    cv2.FONT_HERSHEY_DUPLEX, 1, (255, 255, 255), 2)

        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()
