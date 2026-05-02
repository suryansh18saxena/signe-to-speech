from django.shortcuts import render
import base64
import cv2
import numpy as np
import mediapipe as mp
import joblib
import os
import json
from django.conf import settings
import sys

MODELS_DIR = os.path.join(settings.BASE_DIR.parent, 'Main_Folder', '1_Models')
sys.path.append(MODELS_DIR)
from sign_utils import normalize_landmarks

# Global AI Initialization for Render (Loads once into memory)
try:
    AI_MODEL = joblib.load(os.path.join(MODELS_DIR, 'model_v132.joblib'))
    LABEL_ENCODER = joblib.load(os.path.join(MODELS_DIR, 'label_encoder_v132.joblib'))
except Exception as e:
    print("Warning: Could not load models", e)
    AI_MODEL = None
    LABEL_ENCODER = None

MP_HANDS = mp.solutions.hands
HANDS = MP_HANDS.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.5)
MP_DRAW = mp.solutions.drawing_utils

def index(request):
    return render(request, 'index.html')

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@csrf_exempt
def predict_frame(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_data = data.get('image', '')
            
            if not image_data:
                return JsonResponse({'error': 'No image data'}, status=400)
                
            # Decode Base64 Image from Frontend
            encoded_data = image_data.split(',')[1] if ',' in image_data else image_data
            nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return JsonResponse({'error': 'Failed to decode image'}, status=400)
                
            # OpenCV processes BGR, Mediapipe wants RGB
            frame = cv2.flip(frame, 1)
            H, W, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = HANDS.process(rgb_frame)
            
            current_pred = "No Hand Detected"
            
            if results.multi_hand_landmarks and AI_MODEL:
                for hand_landmarks in results.multi_hand_landmarks:
                    MP_DRAW.draw_landmarks(frame, hand_landmarks, MP_HANDS.HAND_CONNECTIONS)
                    landmarks = normalize_landmarks(hand_landmarks)
                    prediction = AI_MODEL.predict([landmarks])
                    current_pred = LABEL_ENCODER.inverse_transform(prediction)[0]
                    
            # Draw overlay on the frame to send back to frontend
            cv2.rectangle(frame, (0, 0), (W, 90), (45, 45, 45), -1) 
            cv2.putText(frame, f"SIGN: {current_pred}", (15, 35), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Encode drawn frame back to Base64
            _, buffer = cv2.imencode('.jpg', frame)
            out_base64 = base64.b64encode(buffer).decode('utf-8')
            out_data_url = "data:image/jpeg;base64," + out_base64
            
            return JsonResponse({'prediction': current_pred, 'image': out_data_url})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
def save_history(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            text = data.get('text')
            if email and email != 'guest' and text:
                from translations.models import TranslationHistory
                TranslationHistory.objects.create(user_email=email, text=text)
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid'}, status=405)

from django.http import JsonResponse
from translations.models import TranslationHistory

def get_history(request):
    user_email = request.GET.get('user', 'guest@example.com')
    history = TranslationHistory.objects.filter(user_email=user_email).order_by('-created_at')[:10]
    data = [{'text': h.text, 'created_at': h.created_at.strftime("%Y-%m-%d %H:%M:%S")} for h in history]
    return JsonResponse({'history': data})

import json
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def register_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')
            if User.objects.filter(username=email).exists():
                return JsonResponse({'error': 'User already exists'}, status=400)
            user = User.objects.create_user(username=email, email=email, password=password)
            auth_login(request, user)
            return JsonResponse({'success': True, 'email': email})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
def login_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                auth_login(request, user)
                return JsonResponse({'success': True, 'email': email})
            return JsonResponse({'error': 'Invalid credentials'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
def logout_user(request):
    if request.method == 'POST':
        auth_logout(request)
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Invalid method'}, status=405)

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings

@csrf_exempt
def google_login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = data.get('credential')
            
            client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)
            if not client_id or client_id == 'YOUR_GOOGLE_CLIENT_ID':
                return JsonResponse({'error': 'Google Client ID not configured on the backend.'}, status=500)
                
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), client_id)
            email = idinfo['email']
            
            user, created = User.objects.get_or_create(username=email, defaults={'email': email})
            auth_login(request, user)
            return JsonResponse({'success': True, 'email': email})
        except ValueError as e:
            return JsonResponse({'error': 'Invalid token'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)
