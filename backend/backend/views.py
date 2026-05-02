from django.shortcuts import render
from django.http.response import StreamingHttpResponse
from backend.camera import VideoCamera

def index(request):
    return render(request, 'index.html')

def gen(camera):
    try:
        while True:
            frame = camera.get_frame()
            if frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
    finally:
        del camera

def video_feed(request):
    user_email = request.GET.get('user', 'guest@example.com')
    return StreamingHttpResponse(gen(VideoCamera(user_email=user_email)),
                                 content_type='multipart/x-mixed-replace; boundary=frame')

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
