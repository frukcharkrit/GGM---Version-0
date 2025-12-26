# APP01/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth import login, logout, authenticate
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.files.storage import FileSystemStorage # สำหรับอัปโหลดไฟล์
from django.conf import settings # สำหรับเข้าถึง MEDIA_ROOT
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
from django.db.models.functions import TruncDate # เพิ่ม import นี้

import json # เพิ่ม import นี้สำหรับ json.loads

from .models import User, Role, ProPlayer, GamingGear, Preset, Rating, AIModel, Alert, ProPlayerGear, PresetGear # นำเข้า Models ของคุณ
from .forms import RegisterForm, ProPlayerForm, GamingGearForm, PresetForm, AIModelForm, RatingForm, LoginForm # เพิ่ม RatingForm
from .forms import UserEditForm

# สำหรับ AI และ Image Processing
import os
import cv2
import numpy as np
# import tensorflow as tf
# from tensorflow.keras.models import load_model # ตัวอย่างการโหลดโมเดล AI

# สมมติฐาน: คุณมีโมเดล AI ที่โหลดได้
# try:
#     # PATH_TO_AI_MODELS = os.path.join(settings.BASE_DIR, 'ai_models')
#     # active_model_instance = AIModel.objects.filter(is_active=True).first()
#     # if active_model_instance:
#     #     AI_MODEL = load_model(os.path.join(PATH_TO_AI_MODELS, active_model_instance.file_path))
#     # else:
#     #     AI_MODEL = None # หรือโหลด default model
#     #     print("No active AI model found. Matching features will be limited.")
#     print("AI model loading is currently commented out for initial setup.")
# except Exception as e:
#     AI_MODEL = None
#     print(f"Error loading AI model: {e}")

# Helper function เพื่อตรวจสอบว่าผู้ใช้เป็น Admin

# Helper function เพื่อตรวจสอบว่าผู้ใช้เป็น Member
def is_member(user):
    return user.is_authenticated and user.role and user.role.role_name == 'Member'

def home_guest(request):
    featured_pro_players = ProPlayer.objects.all()[:5]
    featured_gears = GamingGear.objects.all()[:5]
    context = {
        'featured_pro_players': featured_pro_players,
        'featured_gears': featured_gears,
    }
    return render(request, 'APP01/home_guest.html', context)

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST) # ใช้ฟอร์มที่เราสร้างใน forms.py
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! Please log in.')
            return redirect('login')
        else:
            messages.error(request, 'Registration failed. Please correct the errors below.')
    else:
        form = RegisterForm()
    return render(request, 'APP01/register.html', {'form': form})

def is_admin(user):
    return user.is_authenticated and (user.is_superuser or (user.role and user.role.role_name == 'Admin'))

def user_login(request):
    next_url = request.POST.get('next') or request.GET.get('next')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user) # Use 'login' instead of 'auth_login'
                messages.success(request, f'ยินดีต้อนรับกลับ, {user.username}!')
                # Respect 'next' param if safe
                if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                    return redirect(next_url)
                if is_admin(user):
                    return redirect('admin_dashboard')
                return redirect('home_member')
            else:
                 messages.error(request, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
        else:
             # กรณีที่ Validation ไม่ผ่าน (อาจเพราะบัญชีถูกแบน หรือกรอกผิด)
             username_input = request.POST.get('username')
             
             if username_input:
                try:
                    existing_user = User.objects.get(username=username_input)
                    if not existing_user.is_active:
                        banned_msg = "บัญชีของคุณถูกระงับการใช้งาน"
                        if existing_user.banned_at:
                            formatted_time = timezone.localtime(existing_user.banned_at).strftime('%d/%m/%Y %H:%M')
                            banned_msg += f" เมื่อวันที่ {formatted_time}"
                        
                        messages.error(request, banned_msg)
                    else:
                        messages.error(request, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
                except User.DoesNotExist:
                     messages.error(request, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
             else:
                messages.error(request, 'โปรดกรอกข้อมูลให้ครบถ้วน')
    else:
        form = LoginForm()
    context = {'form': form}
    if next_url:
        context['next'] = next_url
    return render(request, 'APP01/login.html', context)

def forgot_password(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(
                request=request,
                from_email=settings.EMAIL_HOST_USER, # ต้องตั้งค่าใน settings.py
                email_template_name='APP01/password_reset_email.html',
                subject_template_name='APP01/password_reset_subject.txt',
            )
            messages.success(request, 'Password reset email has been sent.')
            return redirect('login') # หรือหน้าแจ้งเตือนว่าส่งอีเมลแล้ว
        else:
            messages.error(request, 'Failed to send password reset email.')
    else:
        form = PasswordResetForm()
    return render(request, 'APP01/forgot_password.html', {'form': form})

# APP01/views.py (แก้ไขทับฟังก์ชันเดิม)

def upload_image_and_match(request):
    return _handle_upload(request, is_ajax=False)

def upload_image_ajax(request):
    return _handle_upload(request, is_ajax=True)

# สร้างฟังก์ชันกลางเพื่อลด code ซ้ำซ้อน
def _handle_upload(request, is_ajax):
    if request.method == 'POST' and request.FILES.get('image'):
        uploaded_image = request.FILES['image']
        fs = FileSystemStorage()
        filename = fs.save(uploaded_image.name, uploaded_image)
        uploaded_file_url = fs.url(filename)

        try:
            # --- AI Logic (จำลอง) ---
            # ในระบบจริง Code ส่วนนี้จะหา Best Match 1 คนจาก DB
            # แต่ในที่นี้เราจะโฟกัสที่กรณี Demo (Else)
            user_physique_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
            best_match_player = None 
            min_distance = float('inf')
            
            # ... (ข้ามส่วนค้นหา Real DB ไป หรือใส่ logic เดิมของคุณตรงนี้) ...
            
            # รับค่า Checkbox
            selected_gears = request.POST.getlist('gear_types')
            
            # สร้าง Session Data
            if best_match_player:
                # กรณีเจอ Pro Player จริง (มีคนเดียว)
                request.session['match_result'] = {
                    'mode': 'real',
                    'uploaded_image_url': uploaded_file_url,
                    'matched_player_id': best_match_player.player_id,
                    'min_distance': min_distance,
                    'selected_gears': selected_gears,
                    'temp_preset_gears': []
                }
            else:
                # === ดึงข้อมูล Pro Player จริงจาก Database ===
                # === Real Matching Logic ===
                # Simple matching: Select a ProPlayer from database
                # Future enhancement: Use ML/CV to analyze hand size and match to similar ProPlayers
                
                from random import choice
                
                # Get all ProPlayers with images and gears
                available_players = ProPlayer.objects.filter(
                    image__isnull=False,
                    proplayergear__isnull=False
                ).exclude(image='').distinct()
                
                if not available_players.exists():
                    # Fallback: Get any player with image
                    available_players = ProPlayer.objects.filter(
                        image__isnull=False
                    ).exclude(image='')
                
                if not available_players.exists():
                    messages.error(request, 'No Pro Players available in database. Please import player data first.')
                    return redirect('upload_image')
                
                # Simple matching: Choose random ProPlayer
                # TODO: Implement real matching based on hand size analysis
                matched_player = choice(list(available_players))
                
                # Store match result in session
                request.session['match_result'] = {
                    'mode': 'real',
                    'matched_player_id': matched_player.player_id,
                    'uploaded_image_url': uploaded_file_url,
                    'selected_gears': selected_gears,
                    'temp_preset_gears': [],
                    'min_distance': 0.0  # Placeholder for future ML distance metric
                }


            if is_ajax:
                return JsonResponse({'ok': True, 'redirect': reverse('matching_result'), 'uploaded_image_url': uploaded_file_url})
            else:
                return redirect('matching_result')

        except Exception as e:
            if is_ajax:
                return JsonResponse({'ok': False, 'error': str(e)}, status=500)
            messages.error(request, f"Error: {e}")
            return redirect('upload_image')
    
    if is_ajax:
        return JsonResponse({'ok': False, 'error': 'Invalid request'}, status=400)
    messages.error(request, 'Please upload an image.')
    return render(request, 'APP01/upload_image.html')


def matching_result(request):
    """Display matching result with single matched ProPlayer"""
    match_result = request.session.get('match_result')
    if not match_result:
        messages.error(request, 'No match result found. Please upload an image first.')
        return redirect('upload_image')

    # Get the matched ProPlayer from database
    matched_player_id = match_result.get('matched_player_id')
    if not matched_player_id:
        messages.error(request, 'Invalid match result.')
        return redirect('upload_image')
    
    matched_player = get_object_or_404(ProPlayer, player_id=matched_player_id)
    
    # Get all gears for this ProPlayer
    gears_qs = GamingGear.objects.filter(proplayergear__player=matched_player)
    gears_list = []
    for g in gears_qs:
        gears_list.append({
            'gear_id': g.gear_id,
            'name': g.name,
            'category': getattr(g, 'type', 'Gear'),
            'image_url': g.image.url if g.image else None,
        })
    
    # Prepare context
    selected_gears = match_result.get('selected_gears', [])
    temp_preset_ids = match_result.get('temp_preset_gears', [])

    context = {
        'uploaded_image_url': match_result['uploaded_image_url'],
        'matched_player': matched_player,
        'matched_gears': gears_list,
        'selected_gears': selected_gears,
        'temp_preset_ids': temp_preset_ids,
        'is_member': request.user.is_authenticated and request.user.role and request.user.role.role_name == 'Member',
    }
    return render(request, 'APP01/matching_result.html', context)


# ฟังก์ชันสำหรับแก้ไข Preset ชั่วคราวจากหน้าผลลัพธ์
# APP01/views.py

def edit_temp_preset(request, action, gear_id=None):
    # 1. ดึงข้อมูล Session มาตรวจสอบ
    match_result = request.session.get('match_result')
    if not match_result:
        # ถ้า Session หมดอายุหรือไม่มีข้อมูล ให้กลับไปเริ่มใหม่
        return redirect('upload_image')

    # 2. เตรียมรายการ ID อุปกรณ์ปัจจุบัน
    current_temp_gears = match_result.get('temp_preset_gears', [])
    
    # แปลง gear_id เป็น int (ถ้ามีค่าส่งมา)
    if gear_id:
        try:
            gear_id = int(gear_id)
        except ValueError:
            pass # ถ้าแปลงไม่ได้ก็ข้ามไป

    # 3. Logic การเพิ่ม/ลบ
    if action == 'add' and gear_id:
        # ถ้ายังไม่มีในลิสต์ ให้เพิ่มเข้าไป
        if gear_id not in current_temp_gears:
            current_temp_gears.append(gear_id)
            # messages.success(request, 'Item added.') # (Option) เปิดใช้ถ้ารำคาญแจ้งเตือนน้อยลง

    elif action == 'remove' and gear_id:
        # ถ้ามีในลิสต์ ให้ลบออก
        if gear_id in current_temp_gears:
            current_temp_gears.remove(gear_id)
            # ถ้าลบจนหมด ให้ตั้ง flag เพื่อไม่ให้ autofill
            if not current_temp_gears:
                match_result['user_cleared_preset'] = True
            # messages.success(request, 'Item removed.')

    # 4. บันทึกค่าใหม่กลับลง Session
    match_result['temp_preset_gears'] = current_temp_gears
    request.session['match_result'] = match_result
    # จำเป็นต้องสั่ง modified = True ในบาง config ของ Django เพื่อให้รู้ว่า dict ใน session เปลี่ยน
    request.session.modified = True 

    # 5. [สำคัญ] ตรวจสอบว่ามี parameter 'next' ส่งมาไหม?
    # ถ้ามี (เช่น ?next=/preset/save/) ให้ Redirect ไปหน้านั้น
    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)

    # 6. Default Redirect (ถ้าไม่มี next ให้กลับไปหน้าผลลัพธ์)
    return redirect('matching_result')

# APP01/views.py

def gear_detail(request, gear_id):
    gear = None
    related_gears = []

    # 1. ลองหาจาก Database จริง
    try:
        gear_obj = GamingGear.objects.get(gear_id=gear_id)
        
        # แปลงเป็น Dict พร้อม specs ทั้งหมด
        import json
        specs_dict = {}
        try:
            if gear_obj.specs:
                specs_dict = json.loads(gear_obj.specs)
        except:
            pass
            
        gear = {
            'gear_id': gear_obj.gear_id,
            'name': gear_obj.name,
            'type': gear_obj.type,
            'brand': gear_obj.brand,
            'category': gear_obj.type,  # type ใช้เป็น category
            'image_url': gear_obj.image.url if gear_obj.image else None,
            'description': getattr(gear_obj, 'description', ''),
            'price': gear_obj.price,
            'store_url': gear_obj.store_url,
            'specs': specs_dict,  # เก็บเป็น dict
        }

        # หาอุปกรณ์อื่นๆ ในประเภทเดียวกัน (ไม่รวมตัวเอง)
        related_qs = GamingGear.objects.filter(type=gear_obj.type).exclude(gear_id=gear_id)[:4]
        for r in related_qs:
            related_gears.append({
                'gear_id': r.gear_id,
                'name': r.name,
                'category': r.type,
                'image_url': r.image.url if r.image else None,
            })

    except (GamingGear.DoesNotExist, Exception):
        # 2. ถ้าไม่เจอใน DB ให้ใช้ข้อมูล Demo (รวมมิตรจาก Demo Player ทุกคน)
        # เพื่อให้สามารถคลิกดูของ Demo ได้
        all_demo_gears = [
            # Mouse
            {'gear_id': 101, 'name': 'Razer DeathAdder V3', 'category': 'Mouse', 'image_url': 'https://m.media-amazon.com/images/I/61p2-hsvjFL.jpg'},
            {'gear_id': 201, 'name': 'Endgame Gear XM2we', 'category': 'Mouse', 'image_url': 'https://m.media-amazon.com/images/I/51w+KkL-tDL._AC_UF1000,1000_QL80_.jpg'},
            {'gear_id': 301, 'name': 'Logitech G Pro X Superlight', 'category': 'Mouse', 'image_url': 'https://resource.logitechg.com/w_692,c_lpad,ar_4:3,q_auto,f_auto,dpr_1.0/d_transparent.gif/content/dam/gaming/en/products/pro-x-superlight/pro-x-superlight-black-gallery-1.png?v=1'},
            # Keyboard
            {'gear_id': 102, 'name': 'Razer Huntsman V3', 'category': 'Keyboard', 'image_url': 'https://m.media-amazon.com/images/I/71X8gC6qJAL.jpg'},
            {'gear_id': 202, 'name': 'Wooting 60HE', 'category': 'Keyboard', 'image_url': 'https://m.media-amazon.com/images/I/51u8u-YKx2L._AC_UF894,1000_QL80_.jpg'},
            # Headset
            {'gear_id': 203, 'name': 'HyperX Cloud II', 'category': 'Headset', 'image_url': 'https://m.media-amazon.com/images/I/71M-r6V1q+L.jpg'},
            {'gear_id': 302, 'name': 'Logitech G Pro X 2', 'category': 'Headset', 'image_url': 'https://resource.logitechg.com/w_692,c_lpad,ar_4:3,q_auto,f_auto,dpr_1.0/d_transparent.gif/content/dam/gaming/en/products/pro-x-2-lightspeed/gallery/pro-x-2-lightspeed-black-gallery-1.png?v=1'},
            # Monitor
            {'gear_id': 303, 'name': 'ZOWIE XL2566K', 'category': 'Monitor', 'image_url': 'https://zowie.benq.com/content/dam/game/en/product/monitor/xl2566k/gallery/xl2566k-gallery-01.png'}
        ]

        # หาตัวที่คลิกมา
        gear = next((g for g in all_demo_gears if g['gear_id'] == gear_id), None)
        
        if gear:
            # หา Related Gears ใน Demo List
            related_gears = [g for g in all_demo_gears if g['category'] == gear['category'] and g['gear_id'] != gear_id]

    # ถ้าหาไม่เจอเลยทั้ง DB และ Demo
    if not gear:
        # สร้าง Dummy ขึ้นมากัน Error หรือ Redirect ออก
        gear = {'gear_id': gear_id, 'name': 'Unknown Gear', 'category': 'Unknown', 'image_url': None}

    # เช็ค Session สำหรับปุ่ม ADD
    match_result = request.session.get('match_result', {})
    temp_preset_ids = match_result.get('temp_preset_gears', [])

    context = {
        'gear': gear,
        'related_gears': related_gears,
        'temp_preset_ids': temp_preset_ids,
        'is_member': request.user.is_authenticated and request.user.role and request.user.role.role_name == 'Member',
    }
    return render(request, 'APP01/gear_detail.html', context)

def pro_player_detail(request, player_id):
    # 1. ลองหาจาก Database จริงก่อน
    try:
        pro_player_obj = ProPlayer.objects.get(player_id=player_id)
        # ดึงอุปกรณ์จาก DB
        gears_qs = GamingGear.objects.filter(proplayergear__player=pro_player_obj)
        
        # จัด Format ข้อมูลให้ Template ใช้ง่าย
        pro_player = {
            'player_id': pro_player_obj.player_id,
            'name': pro_player_obj.name,
            'game': pro_player_obj.game,
            'bio': getattr(pro_player_obj, 'bio', ''),
            'image_url': pro_player_obj.image.url if pro_player_obj.image else None,
            'game_logo': 'https://upload.wikimedia.org/wikipedia/commons/1/14/Valorant_logo_-_pink_color_version.svg' # ตัวอย่างใส่ default
        }
        
        pro_player_gears = []
        for g in gears_qs:
            pro_player_gears.append({
                'gear_id': g.gear_id,
                'name': g.name,
                'category': getattr(g, 'category', 'Gear'),
                'image_url': g.image.url if g.image else None,
                'description': getattr(g, 'description', '')
            })

    except ProPlayer.DoesNotExist:
        # 2. ถ้าไม่เจอใน DB ให้ลองดูข้อมูล Demo (Hardcode ไว้สำหรับแสดงผล)
        # ข้อมูลชุดเดียวกับใน upload_image_ajax
        demo_players = [
            {
                'player_id': 1, 'name': 'Faker', 'bio': 'The Unkillable Demon King. T1 Mid Laner.',
                'image_url': 'https://cmsassets.rgpub.io/sanity/images/dsfx7636/news/f75586c584d20160299944d3d61e8bc715253c9d-1232x1232.jpg',
                'game_logo': 'https://upload.wikimedia.org/wikipedia/commons/2/2a/LoL_Icon.svg',
                'gears': [
                    {'gear_id': 101, 'name': 'Razer DeathAdder V3', 'category': 'Mouse', 'image_url': 'https://m.media-amazon.com/images/I/61p2-hsvjFL.jpg'},
                    {'gear_id': 102, 'name': 'Razer Huntsman V3', 'category': 'Keyboard', 'image_url': 'https://m.media-amazon.com/images/I/71X8gC6qJAL.jpg'}
                ]
            },
            {
                'player_id': 2, 'name': 'TenZ', 'bio': 'Valorant Superstar. Known for crisp aim.',
                'image_url': 'https://liquipedia.net/commons/images/thumb/6/62/Sentinels_TenZ_at_Champions_Madrid_2024.jpg/600px-Sentinels_TenZ_at_Champions_Madrid_2024.jpg',
                'game_logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Valorant_logo_-_pink_color_version.svg/1200px-Valorant_logo_-_pink_color_version.svg.png',
                'gears': [
                    {'gear_id': 201, 'name': 'Endgame Gear XM2we', 'category': 'Mouse', 'image_url': 'https://m.media-amazon.com/images/I/51w+KkL-tDL._AC_UF1000,1000_QL80_.jpg'},
                    {'gear_id': 202, 'name': 'Wooting 60HE', 'category': 'Keyboard', 'image_url': 'https://m.media-amazon.com/images/I/51u8u-YKx2L._AC_UF894,1000_QL80_.jpg'},
                    {'gear_id': 203, 'name': 'HyperX Cloud II', 'category': 'Headset', 'image_url': 'https://m.media-amazon.com/images/I/71M-r6V1q+L.jpg'}
                ]
            },
            {
                'player_id': 3, 'name': 'S1mple', 'bio': 'CS:GO/CS2 GOAT. AWPer Legend.',
                'image_url': 'https://liquipedia.net/commons/images/thumb/e/e3/S1mple_at_IEM_Katowice_2020.jpg/600px-S1mple_at_IEM_Katowice_2020.jpg',
                'game_logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/Counter-Strike_2_logo.svg/1200px-Counter-Strike_2_logo.svg.png',
                'gears': [
                    {'gear_id': 301, 'name': 'Logitech G Pro X Superlight', 'category': 'Mouse', 'image_url': 'https://resource.logitechg.com/w_692,c_lpad,ar_4:3,q_auto,f_auto,dpr_1.0/d_transparent.gif/content/dam/gaming/en/products/pro-x-superlight/pro-x-superlight-black-gallery-1.png?v=1'},
                    {'gear_id': 302, 'name': 'Logitech G Pro X 2', 'category': 'Headset', 'image_url': 'https://resource.logitechg.com/w_692,c_lpad,ar_4:3,q_auto,f_auto,dpr_1.0/d_transparent.gif/content/dam/gaming/en/products/pro-x-2-lightspeed/gallery/pro-x-2-lightspeed-black-gallery-1.png?v=1'},
                     {'gear_id': 303, 'name': 'ZOWIE XL2566K', 'category': 'Monitor', 'image_url': 'https://zowie.benq.com/content/dam/game/en/product/monitor/xl2566k/gallery/xl2566k-gallery-01.png'}
                ]
            }
        ]
        
        # ค้นหาจาก Demo List
        pro_player = next((p for p in demo_players if p['player_id'] == player_id), None)
        if not pro_player:
             # ถ้าไม่เจอเลย ให้ Redirect กลับหน้า Home หรือ 404
            from django.http import Http404
            raise Http404("Pro Player not found")
            
        pro_player_gears = pro_player['gears']

    # เช็คสถานะ Preset (Add/Remove button)
    match_result = request.session.get('match_result', {})
    temp_preset_ids = match_result.get('temp_preset_gears', [])
    
    # ส่งค่า context
    context = {
        'pro_player': pro_player,
        'pro_player_gears': pro_player_gears,
        'temp_preset_ids': temp_preset_ids,
        'is_member': request.user.is_authenticated and request.user.role and request.user.role.role_name == 'Member',
    }
    return render(request, 'APP01/pro_player_detail.html', context)

def global_search(request):
    """ค้นหาทั้ง Pro Player และ Gaming Gear พร้อมกัน"""
    query = request.GET.get('q', '').strip()
    
    pro_players = []
    gears = []
    
    if query:
        pro_players = ProPlayer.objects.filter(name__icontains=query)[:10]
        gears = GamingGear.objects.filter(name__icontains=query)[:10]
    
    context = {
        'query': query,
        'pro_players': pro_players,
        'gears': gears,
    }
    return render(request, 'APP01/search_results.html', context)

def search_gear(request):
    query = request.GET.get('q')
    gears = GamingGear.objects.all()
    if query:
        gears = gears.filter(name__icontains=query) # ค้นหาจากชื่ออุปกรณ์
    context = {
        'gears': gears,
        'query': query
    }
    return render(request, 'APP01/search_gear.html', context)

def search_pro_player(request):
    query = request.GET.get('q')
    pro_players = ProPlayer.objects.all()
    if query:
        pro_players = pro_players.filter(name__icontains=query) # ค้นหาจากชื่อ Pro Player
    context = {
        'pro_players': pro_players,
        'query': query
    }
    return render(request, 'APP01/search_pro_player.html', context)

@login_required(login_url='login')
@user_passes_test(is_member, login_url='home_guest') # ถ้าเป็น admin จะ redirect กลับไปหน้า guest
def home_member(request):
    user_presets = Preset.objects.filter(user=request.user).order_by('-created_at')[:5]
    context = {
        'user_presets': user_presets,
    }
    return render(request, 'APP01/home_member.html', context)

@login_required(login_url='login')
def user_profile(request):
    """แสดงโปรไฟล์ของ User พร้อม Dashboard Analytics"""
    from django.db.models import Count
    from django.db.models.functions import TruncMonth
    from datetime import datetime, timedelta
    import json
    
    # Basic data
    user_presets = Preset.objects.filter(user=request.user).order_by('-created_at')[:5]
    user_ratings = Rating.objects.filter(user=request.user).order_by('-rated_at')[:5]
    
    # Dashboard Analytics
    total_presets = Preset.objects.filter(user=request.user).count()
    total_ratings = Rating.objects.filter(user=request.user).count()
    
    # Preset creation timeline (by month) for chart
    preset_timeline = (
        Preset.objects.filter(user=request.user)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('preset_id'))
        .order_by('month')
    )
    
    # Format data for Chart.js
    chart_labels = []
    chart_data = []
    for item in preset_timeline:
        if item['month']:
            chart_labels.append(item['month'].strftime('%b %Y'))
            chart_data.append(item['count'])
    
    # Recent activity stats
    now = datetime.now()
    last_7_days = now - timedelta(days=7)
    last_30_days = now - timedelta(days=30)
    
    presets_last_7_days = Preset.objects.filter(
        user=request.user,
        created_at__gte=last_7_days
    ).count()
    
    presets_last_30_days = Preset.objects.filter(
        user=request.user,
        created_at__gte=last_30_days
    ).count()
    
    # Latest preset date
    latest_preset = Preset.objects.filter(user=request.user).order_by('-created_at').first()
    
    # Rating stats
    good_ratings = Rating.objects.filter(user=request.user, feedback_score='Good').count()
    neutral_ratings = Rating.objects.filter(user=request.user, feedback_score='Neutral').count()
    bad_ratings = Rating.objects.filter(user=request.user, feedback_score='Bad').count()
    
    context = {
        'user_presets': user_presets,
        'user_ratings': user_ratings,
        # Dashboard stats
        'total_presets': total_presets,
        'total_ratings': total_ratings,
        'presets_last_7_days': presets_last_7_days,
        'presets_last_30_days': presets_last_30_days,
        'latest_preset': latest_preset,
        # Chart data
        'chart_labels_json': json.dumps(chart_labels),
        'chart_data_json': json.dumps(chart_data),
        # Rating breakdown
        'good_ratings': good_ratings,
        'neutral_ratings': neutral_ratings,
        'bad_ratings': bad_ratings,
    }
    return render(request, 'APP01/profile.html', context)

@login_required(login_url='login')
def edit_profile(request):
    """แก้ไขโปรไฟล์ของ User"""
    if request.method == 'POST':
        # รับค่าจากฟอร์ม
        username = request.POST.get('username')
        email = request.POST.get('email')
        
        # ตรวจสอบว่า username ซ้ำกับคนอื่นหรือไม่
        if User.objects.filter(username=username).exclude(user_id=request.user.user_id).exists():
            messages.error(request, 'Username นี้ถูกใช้แล้ว')
            return redirect('edit_profile')
        
        # ตรวจสอบว่า email ซ้ำกับคนอื่นหรือไม่
        if User.objects.filter(email=email).exclude(user_id=request.user.user_id).exists():
            messages.error(request, 'Email นี้ถูกใช้แล้ว')
            return redirect('edit_profile')
        
        # อัพเดทข้อมูล
        request.user.username = username
        request.user.email = email
        
        # จัดการรูปโปรไฟล์
        if request.FILES.get('profile_image'):
            request.user.profile_image = request.FILES['profile_image']
        
        request.user.save()
        
        messages.success(request, 'อัพเดทโปรไฟล์สำเร็จ!')
        return redirect('user_profile')
    
    return render(request, 'APP01/edit_profile.html')

@login_required(login_url='login')
def save_preset(request):
    """
    แสดงหน้าบันทึก Preset โดยดึงอุปกรณ์จาก Session
    - ดึง temp_preset_gears จาก match_result ใน Session
    - แสดงรายการอุปกรณ์ที่เลือกไว้
    - บันทึกเป็น Preset เมื่อกด Submit
    """
    match_result = request.session.get('match_result', {})
    temp_gear_ids = match_result.get('temp_preset_gears', [])
    
    # ถ้าไม่มีอุปกรณ์ใน Session ให้กลับไปหน้า Matching Result
    if not temp_gear_ids:
        messages.warning(request, 'No gears selected. Please select gears from the matching result page.')
        return redirect('matching_result')
    
    # ดึงข้อมูลอุปกรณ์จาก Database
    gears = GamingGear.objects.filter(gear_id__in=temp_gear_ids)
    
    # สร้าง list ของ dict เพื่อส่งไปแสดงในหน้า Template
    display_gears = []
    for gear in gears:
        display_gears.append({
            'gear_id': gear.gear_id,
            'name': gear.name,
            'category': gear.type,  # ใช้ .type เนื่องจาก model ใช้ field นี้
            'image_url': gear.image.url if gear.image else None,
        })
    
    if request.method == 'POST':
        # รับชื่อ Preset จาก Form
        preset_name = request.POST.get('name', '').strip()
        
        if not preset_name:
            messages.error(request, 'Preset name is required.')
            return render(request, 'APP01/save_preset.html', {
                'display_gears': display_gears,
                'form': {'name': preset_name},
            })
        
        # สร้าง Preset ใหม่
        new_preset = Preset.objects.create(
            user=request.user,
            name=preset_name
        )
        
        # เพิ่มอุปกรณ์เข้า Preset
        for idx, gear in enumerate(gears, start=1):
            PresetGear.objects.create(
                preset=new_preset,
                gear=gear,
                order=idx
            )
        
        # ลบข้อมูลชั่วคราวออกจาก Session
        if 'match_result' in request.session:
            if 'temp_preset_gears' in request.session['match_result']:
                del request.session['match_result']['temp_preset_gears']
            request.session.modified = True
        
        messages.success(request, f'Preset "{preset_name}" saved successfully!')
        return redirect('preset_detail', preset_id=new_preset.preset_id)
    
    # GET Request: แสดงหน้าฟอร์ม
    context = {
        'display_gears': display_gears,
        'gear_ids_string': ','.join(map(str, temp_gear_ids)),  # สำหรับ hidden field (ถ้ามี)
    }
    return render(request, 'APP01/save_preset.html', context)

@login_required(login_url='login')
def submit_rating(request):
    """Submit or update rating for matched ProPlayer"""
    match_result = request.session.get('match_result')
    if not match_result:
        messages.error(request, 'No match result to rate.')
        return redirect('upload_image')

    # Get matched ProPlayer
    matched_player_id = match_result.get('matched_player_id')
    if not matched_player_id:
        messages.error(request, 'Invalid match result.')
        return redirect('matching_result')

    matched_player = get_object_or_404(ProPlayer, player_id=matched_player_id)

    if request.method == 'POST':
        # Get score from star rating
        score = request.POST.get('score')
        
        if not score:
            messages.error(request, 'Please select a rating.')
            return redirect('matching_result')
        
        try:
            score_int = int(score)
            if score_int < 1 or score_int > 5:
                messages.error(request, 'Invalid rating value.')
                return redirect('matching_result')
        except ValueError:
            messages.error(request, 'Invalid rating value.')
            return redirect('matching_result')
        
        # Map score to feedback_score
        if score_int >= 4:
            feedback_score = 'Good'
            feedback_label = 'Good' if score_int == 4 else 'Excellent'
        elif score_int == 3:
            feedback_score = 'Neutral'
            feedback_label = 'Average'
        else:
            feedback_score = 'Bad'
            feedback_label = 'Poor' if score_int == 2 else 'Bad'
        
        # Check if user already rated this ProPlayer
        existing_rating = Rating.objects.filter(user=request.user, proplayer=matched_player).first()
        if existing_rating:
            # Update existing rating
            existing_rating.feedback_score = feedback_score
            existing_rating.comment = f'Rated {score_int} stars'
            existing_rating.save()
            messages.success(request, f'You have updated your vote for this match to {score_int}★ {feedback_label}')
        else:
            # Create new rating
            rating = Rating()
            rating.user = request.user
            rating.proplayer = matched_player
            rating.feedback_score = feedback_score
            rating.comment = f'Rated {score_int} stars'
            
            # Attach metadata from session for later analysis
            try:
                rating.match_image_url = match_result.get('uploaded_image_url')
            except Exception:
                rating.match_image_url = None
            try:
                rating.selected_gears = json.dumps(match_result.get('temp_preset_gears', []))
            except Exception:
                rating.selected_gears = None
            try:
                rating.match_distance = float(match_result.get('min_distance')) if match_result.get('min_distance') is not None else None
            except Exception:
                rating.match_distance = None
            
            rating.save()
            messages.success(request, f'You have voted this match for {score_int}★ {feedback_label}')

        # Stay on matching result page (don't clear session, don't redirect to profile)
        return redirect('matching_result')
    
    # If not POST, redirect back to matching result
    return redirect('matching_result')

@login_required(login_url='login')
def manage_presets(request):
    """ดึงรายการ Presets ทั้งหมดของ User ปัจจุบันมาแสดงผล"""
    # ดึง Presets ทั้งหมดของ User ปัจจุบัน เรียงตามวันที่สร้างล่าสุด
    user_presets = Preset.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'presets': user_presets,
    }
    # จะพยายาม render template: APP01/manage_presets.html ซึ่งเราจะสร้างในขั้นตอนถัดไป
    return render(request, 'APP01/manage_presets.html', context)

@login_required(login_url='login')
def preset_detail(request, preset_id):
    # ดึงข้อมูล Preset (ต้องเป็นของ User คนปัจจุบันเท่านั้น)
    preset = get_object_or_404(Preset, preset_id=preset_id, user=request.user)
    
    # ดึงรายการอุปกรณ์ใน Preset เรียงตามลำดับ
    # โค้ดนี้จะใช้ได้ก็ต่อเมื่อ PresetGear ถูกบันทึกอย่างถูกต้องโดย save_preset
    preset_gears_objs = PresetGear.objects.filter(preset=preset).order_by('order')
    
    # เตรียมข้อมูลสำหรับแสดงผล
    detailed_items = []
    
    for pg in preset_gears_objs:
        gear = pg.gear
        
        # 1. พยายามหารูป Pro Player ที่ใช้อุปกรณ์ชิ้นนี้ (เอาคนแรกที่เจอ)
        related_pro_gear = ProPlayerGear.objects.filter(gear=gear).select_related('player').first()
        pro_img_url = None
        
        # 2. ถ้าเจอ Pro Player ให้ดึง URL รูปมา
        if related_pro_gear and related_pro_gear.player.image:
            pro_img_url = related_pro_gear.player.image.url
        
        detailed_items.append({
            'gear': gear,
            'pro_img_url': pro_img_url
        })

    context = {
        'preset': preset,
        'detailed_items': detailed_items,
    }
    return render(request, 'APP01/preset_detail.html', context)

@login_required(login_url='login')
def edit_preset(request, preset_id):
    preset = get_object_or_404(Preset, preset_id=preset_id, user=request.user)
    current_gears = list(PresetGear.objects.filter(preset=preset).order_by('order'))

    if request.method == 'POST':
        form = PresetForm(request.POST, instance=preset) # เพื่ออัปเดตชื่อ Preset
        if form.is_valid():
            form.save()
            
            # การจัดการ Gears
            # ผมแนะนำให้ใช้ JavaScript ใน frontend เพื่อส่ง list ของ gear_id ที่เลือกมา
            # ในที่นี้สมมติว่ามีการส่ง 'selected_gears' ซึ่งเป็น list ของ gear_id
            selected_gear_ids = request.POST.getlist('selected_gears') 
            
            # ลบ Gear เก่าทั้งหมดที่เชื่อมกับ Preset นี้
            PresetGear.objects.filter(preset=preset).delete()
            
            # เพิ่ม Gear ใหม่เข้าไปตามลำดับที่ส่งมา
            order_num = 1
            for gear_id in selected_gear_ids:
                gear = get_object_or_404(GamingGear, gear_id=gear_id)
                PresetGear.objects.create(preset=preset, gear=gear, order=order_num)
                order_num += 1
            
            messages.success(request, f'Preset "{preset.name}" updated successfully!')
            return redirect('preset_detail', preset_id=preset.preset_id)
        else:
            messages.error(request, 'Failed to update preset. Please correct the errors.')
    else:
        form = PresetForm(instance=preset)
    
    # Gears ทั้งหมดสำหรับให้ผู้ใช้เลือก
    all_gears = GamingGear.objects.all().order_by('name') 
    
    # IDs ของ Gears ที่อยู่ใน Preset นี้แล้ว
    current_gear_ids = [pg.gear.gear_id for pg in current_gears]

    context = {
        'form': form,
        'preset': preset,
        'current_gears': current_gears, # รายการ PresetGear objects สำหรับแสดงผล
        'all_gears': all_gears, # รายการ GamingGear objects สำหรับตัวเลือก
        'current_gear_ids': current_gear_ids, # IDs สำหรับเช็คใน template
    }
    return render(request, 'APP01/edit_preset.html', context)

# APP01/views.py (เพิ่มฟังก์ชันนี้)

@login_required(login_url='login')
def edit_preset_name(request, preset_id):
    """ฟังก์ชันสำหรับแก้ไขชื่อ Preset โดยเฉพาะ (ใช้จาก Modal ในหน้า Detail)"""
    
    # 1. ค้นหา Preset และตรวจสอบว่าเป็นของ User คนปัจจุบัน
    preset = get_object_or_404(Preset, preset_id=preset_id, user=request.user)
    
    if request.method == 'POST':
        # ใช้ PresetForm เพื่อจัดการฟอร์ม (ต้องมีฟิลด์ 'name')
        # instance=preset จะทำให้ Form อัปเดตข้อมูลของ Preset เดิม
        form = PresetForm(request.POST, instance=preset)
        
        if form.is_valid():
            # บันทึกการเปลี่ยนแปลงชื่อเท่านั้น
            form.save()
            messages.success(request, f'Preset name updated to "{preset.name}" successfully.')
            
            # Redirect กลับไปยังหน้า Detail เดิม
            return redirect('preset_detail', preset_id=preset.preset_id)
        else:
            # หากฟอร์มไม่ถูกต้อง
            messages.error(request, 'Invalid input. Please provide a valid name for your preset.')
            # Redirect กลับไปหน้า Detail เดิมพร้อม Error message
            return redirect('preset_detail', preset_id=preset.preset_id)
            
    # ป้องกันการเข้าถึงด้วย GET request
    messages.error(request, 'Method not allowed.')
    return redirect('preset_detail', preset_id=preset.preset_id)

@login_required(login_url='login')
@user_passes_test(is_member, login_url='home_guest')
def delete_preset(request, preset_id):
    preset = get_object_or_404(Preset, preset_id=preset_id, user=request.user)
    if request.method == 'POST':
        preset.delete()
        messages.success(request, f'Preset "{preset.name}" deleted successfully.')
    return redirect('manage_presets') # Redirect หลังจากลบสำเร็จ
    # return render(request, 'APP01/confirm_delete_preset.html', {'preset': preset}) # อาจทำเป็น modal

@login_required(login_url='login')
@user_passes_test(is_member, login_url='home_guest')
def share_preset(request, preset_id):
    preset = get_object_or_404(Preset, preset_id=preset_id, user=request.user)
    if not preset.share_link:
        import uuid
        preset.share_link = str(uuid.uuid4())
        preset.save()
    
    shareable_url = request.build_absolute_uri(f'/share/{preset.share_link}/') # URL สำหรับแชร์
    messages.info(request, f"Shareable link: {shareable_url}")
    return redirect('preset_detail', preset_id=preset.preset_id)

def view_shared_preset(request, share_link):
    preset = get_object_or_404(Preset, share_link=share_link)
    preset_gears = PresetGear.objects.filter(preset=preset).order_by('order')
    context = {
        'preset': preset,
        'preset_gears': preset_gears,
        'is_shared_view': True,
    }
    return render(request, 'APP01/preset_detail.html', context) # ใช้ template เดียวกัน

@login_required(login_url='login')
def user_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home_guest')

# --- Admin Views ---
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member') # Redirect non-admin to home_member
def admin_dashboard(request):
    total_users = User.objects.count()
    total_pro_players = ProPlayer.objects.count()
    total_gears = GamingGear.objects.count()
    total_presets = Preset.objects.count()
    
    # ดึง Alert ที่ยังไม่อ่าน
    unread_alerts = Alert.objects.filter(is_read=False).order_by('-created_at')[:10]

    # --- Analytics Graph Data (Last 30 Days) ---
    days = 30
    today = timezone.now().date()
    start_date = today - timedelta(days=days-1)

    # Aggregate daily new users
    users_daily = User.objects.filter(created_at__date__gte=start_date)\
        .annotate(date=TruncDate('created_at'))\
        .values('date')\
        .annotate(count=Count('user_id'))\
        .order_by('date')
    
    # Aggregate daily presets (Movement activity)
    presets_daily = Preset.objects.filter(created_at__date__gte=start_date)\
        .annotate(date=TruncDate('created_at'))\
        .values('date')\
        .annotate(count=Count('preset_id'))\
        .order_by('date')

    # Map to dictionaries
    user_dict = {item['date']: item['count'] for item in users_daily}
    preset_dict = {item['date']: item['count'] for item in presets_daily}

    # Prepare lists for Chart.js
    chart_labels = []
    chart_user_data = []
    chart_preset_data = []

    for i in range(days):
        current_date = start_date + timedelta(days=i)
        formatted_date = current_date.strftime('%d %b') # e.g. "25 Dec"
        chart_labels.append(formatted_date)
        chart_user_data.append(user_dict.get(current_date, 0))
        chart_preset_data.append(preset_dict.get(current_date, 0))

    context = {
        'total_users': total_users,
        'total_pro_players': total_pro_players,
        'total_gears': total_gears,
        'total_presets': total_presets,
        'unread_alerts': unread_alerts,
        'chart_labels': chart_labels,
        'chart_user_data': chart_user_data,
        'chart_preset_data': chart_preset_data,
    }
    return render(request, 'APP01/admin_dashboard.html', context)


# --- Admin Pro Players CRUD ---
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_pro_players(request): # S_Pro_List (เปลี่ยนชื่อจาก manage_pro_players)
    pro_players = ProPlayer.objects.all().order_by('name')
    return render(request, 'APP01/admin_pro_players.html', {'pro_players': pro_players})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_add_pro_player(request): # S_Add_Pro_Player (เปลี่ยนชื่อจาก add_pro_player)
    if request.method == 'POST':
        form = ProPlayerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save() # ProPlayerForm.save() จะจัดการ ProPlayerGear ให้
            messages.success(request, 'Pro Player added successfully!')
            return redirect('admin_pro_players')
        else:
            messages.error(request, 'Failed to add Pro Player. Please correct the errors.')
    else:
        form = ProPlayerForm()
    return render(request, 'APP01/admin_pro_player_form.html', {'form': form, 'form_title': 'Add Pro Player'}) # ใช้ form template เดียวกัน

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_edit_pro_player(request, player_id): # S_Edit_Pro_Player (เปลี่ยนชื่อจาก edit_pro_player)
    pro_player = get_object_or_404(ProPlayer, player_id=player_id)
    
    if request.method == 'POST':
        form = ProPlayerForm(request.POST, request.FILES, instance=pro_player)
        if form.is_valid():
            form.save() # ProPlayerForm.save() จะจัดการ ProPlayerGear ให้
            messages.success(request, 'Pro Player updated successfully!')
            return redirect('admin_pro_players')
        else:
            messages.error(request, 'Failed to update Pro Player. Please correct the errors.')
    else:
        form = ProPlayerForm(instance=pro_player)
    
    # สำหรับแสดงผลใน Template (ถ้า ProPlayerForm ไม่ได้จัดการทั้งหมด)
    # current_gears = GamingGear.objects.filter(proplayergear__player=pro_player)
    # all_gears = GamingGear.objects.all()

    context = {
        'form': form,
        'pro_player': pro_player,
        'form_title': 'Edit Pro Player',
        # 'current_gears': current_gears, # ตอนนี้ ProPlayerForm จัดการแล้ว ไม่จำเป็นต้องส่งไป
        # 'all_gears': all_gears,
    }
    return render(request, 'APP01/admin_pro_player_form.html', context) # ใช้ form template เดียวกัน

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_delete_pro_player(request, player_id): # (เปลี่ยนชื่อจาก delete_pro_player)
    pro_player = get_object_or_404(ProPlayer, player_id=player_id)
    if request.method == 'POST':
        name = pro_player.name
        pro_player.delete()
        messages.success(request, f'Pro Player "{name}" deleted successfully.')
    return redirect('admin_pro_players')
    # return render(request, 'APP01/admin_confirm_delete_pro_player.html', {'pro_player': pro_player}) # ทำใน template list แล้ว

# --- Admin Gaming Gears CRUD ---
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_gaming_gears(request): # (เปลี่ยนชื่อจาก admin_manage_gears)
    gaming_gears = GamingGear.objects.all().order_by('name')
    return render(request, 'APP01/admin_gaming_gears.html', {'gaming_gears': gaming_gears})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_add_gaming_gear(request): # (เปลี่ยนชื่อจาก admin_add_gear)
    if request.method == 'POST':
        form = GamingGearForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Gaming Gear added successfully!')
            return redirect('admin_gaming_gears')
        else:
            messages.error(request, 'Failed to add Gaming Gear. Please correct the errors.')
    else:
        form = GamingGearForm()
    return render(request, 'APP01/admin_gaming_gear_form.html', {'form': form, 'form_title': 'Add Gaming Gear'})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_edit_gaming_gear(request, gear_id): # (เปลี่ยนชื่อจาก admin_edit_gear)
    gaming_gear = get_object_or_404(GamingGear, gear_id=gear_id)
    if request.method == 'POST':
        form = GamingGearForm(request.POST, request.FILES, instance=gaming_gear)
        if form.is_valid():
            form.save()
            messages.success(request, 'Gaming Gear updated successfully!')
            return redirect('admin_gaming_gears')
        else:
            messages.error(request, 'Failed to update Gaming Gear. Please correct the errors.')
    else:
        form = GamingGearForm(instance=gaming_gear)
    return render(request, 'APP01/admin_gaming_gear_form.html', {'form': form, 'form_title': 'Edit Gaming Gear'})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_delete_gaming_gear(request, gear_id): # (เปลี่ยนชื่อจาก admin_delete_gear)
    gaming_gear = get_object_or_404(GamingGear, gear_id=gear_id)
    if request.method == 'POST':
        name = gaming_gear.name
        gaming_gear.delete()
        messages.success(request, f'Gaming Gear "{name}" deleted successfully.')
    return redirect('admin_gaming_gears')
    # return render(request, 'APP01/admin_confirm_delete_gear.html', {'gear': gear}) # ทำใน template list แล้ว

# --- Admin User Management ---
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_users(request): # เปลี่ยนชื่อจาก manage_members
    users = User.objects.filter(pk__isnull=False).order_by('username')
    context = {'users': users} # เปลี่ยนชื่อ key เป็น 'users'
    return render(request, 'APP01/admin_users.html', context) # ต้องสร้าง admin_users.html

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_edit_user(request, user_id):
    user_to_edit = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user_to_edit)
        if form.is_valid():
            form.save()
            messages.success(request, f'User {user_to_edit.username} updated successfully.')
            return redirect('admin_users')
        else:
            messages.error(request, 'Failed to update user. Please check errors.')
    else:
        form = UserEditForm(instance=user_to_edit)
        
    context = {
        'user_to_edit': user_to_edit,
        'form': form,
    }
    return render(request, 'APP01/admin_edit_user.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_delete_user(request, user_id): # เปลี่ยนชื่อจาก delete_member
    user_obj = get_object_or_404(User, user_id=user_id)
    if request.method == 'POST':
        username = user_obj.username
        user_obj.delete()
        messages.success(request, f'User {username} deleted successfully.')
    return redirect('admin_users')
    # return render(request, 'APP01/admin_confirm_delete_user.html', {'user_obj': user_obj})

# --- Admin AI Model Management ---
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_ai_models(request): # เปลี่ยนชื่อจาก manage_ai_models
    models = AIModel.objects.all().order_by('-created_at')
    context = {'models': models}
    return render(request, 'APP01/admin_ai_models.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_add_ai_model(request): # เปลี่ยนชื่อจาก add_ai_model
    if request.method == 'POST':
        form = AIModelForm(request.POST, request.FILES)
        if form.is_valid():
            new_model = form.save(commit=False)
            new_model.created_at = timezone.now()
            new_model.last_trained_at = timezone.now()
            new_model.is_active = False # Default to inactive, admin sets active later
            new_model.save()
            messages.success(request, f'AI Model "{new_model.name}" added successfully.')
            return redirect('admin_ai_models')
        else:
            messages.error(request, 'Failed to add AI Model.')
    else:
        form = AIModelForm()
    return render(request, 'APP01/admin_ai_model_form.html', {'form': form, 'form_title': 'Add AI Model'})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_edit_ai_model(request, model_id): # เปลี่ยนชื่อจาก edit_ai_model
    ai_model = get_object_or_404(AIModel, model_id=model_id)
    if request.method == 'POST':
        form = AIModelForm(request.POST, request.FILES, instance=ai_model)
        if form.is_valid():
            form.save()
            messages.success(request, f'AI Model "{ai_model.name}" updated successfully.')
            return redirect('admin_ai_models')
        else:
            messages.error(request, 'Failed to update AI Model.')
    else:
        form = AIModelForm(instance=ai_model)
    return render(request, 'APP01/admin_ai_model_form.html', {'form': form, 'ai_model': ai_model, 'form_title': 'Edit AI Model'})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_delete_ai_model(request, model_id): # เปลี่ยนชื่อจาก delete_ai_model
    ai_model = get_object_or_404(AIModel, model_id=model_id)
    if request.method == 'POST':
        name = ai_model.name
        ai_model.delete()
        messages.success(request, f'AI Model "{name}" deleted successfully.')
    return redirect('admin_ai_models')
    # return render(request, 'APP01/admin_confirm_delete_ai_model.html', {'ai_model': ai_model})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_train_ai_model(request, model_id):
    ai_model = get_object_or_404(AIModel, pk=model_id)
    # ในส่วนนี้คุณจะเรียกใช้ฟังก์ชันสำหรับ Train โมเดล AI ของคุณ
    # เช่น ai_model.train_model() หรือเรียกใช้ Celery task
    messages.success(request, f'กำลังทำการ Train โมเดล {ai_model.name}...')
    return redirect('manage_ai_models')

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_set_active_ai_model(request, model_id): # เปลี่ยนชื่อจาก set_active_ai_model
    if request.method == 'POST':
        AIModel.objects.update(is_active=False) # Set all to inactive
        model_to_activate = get_object_or_404(AIModel, model_id=model_id)
        model_to_activate.is_active = True
        model_to_activate.save()
        messages.success(request, f'AI Model "{model_to_activate.name}" is now active.')
    return redirect('admin_ai_models')

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_guest')
def train_ai_model(request, model_id):
    ai_model = get_object_or_404(AIModel, model_id=model_id)
    if request.method == 'POST':
        # Simulate training process (replace with actual AI training logic)
        messages.info(request, f'AI Model "{ai_model.name}" training started...')
        # In a real scenario, this would trigger a background task
        ai_model.last_trained_at = timezone.now() # Import timezone
        ai_model.save()
        messages.success(request, f'AI Model "{ai_model.name}" training simulated successfully.')
        return redirect('manage_ai_models')
    return render(request, 'APP01/admin_confirm_train_ai_model.html', {'ai_model': ai_model})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_guest')
def view_alerts(request):
    alerts = Alert.objects.all().order_by('-created_at')
    context = {'alerts': alerts}
    return render(request, 'APP01/admin_alerts.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_guest')
def mark_alert_read(request, alert_id):
    alert = get_object_or_404(Alert, alert_id=alert_id)
    if request.method == 'POST':
        alert.is_read = True
        alert.save()
        messages.success(request, 'Alert marked as read.')
    return redirect('view_alerts')

# --- Admin Gaming Gears CRUD (ส่วนต่อขยายที่แก้ไขแล้ว) ---
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_gears(request):
    # สมมติว่า Model ของคุณชื่อ Gear
    # Gear = # ... (Model ที่เกี่ยวข้อง) 
    
    # 🚨 แก้ไขบรรทัดที่ใช้ order_by หรือ filter 🚨
    # เดิม: gears = Gear.objects.all().order_by('category', 'brand', 'name')
    
    gears = GamingGear.objects.all().order_by('type', 'brand', 'name') # <--- 🟢 แก้ไขเป็น 'type'
    
    context = {
        'gaming_gears': gears,  # แก้ให้ตรงกับชื่อที่ template ใช้
        # ...
    }
    return render(request, 'APP01/admin_gaming_gears.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_add_gear(request):
    if request.method == 'POST':
        form = GamingGearForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Gaming Gear added successfully!')
            return redirect('admin_gears')
        else:
            messages.error(request, 'Failed to add gear. Please check inputs.')
    else:
        form = GamingGearForm()
    return render(request, 'APP01/admin_gaming_gear_form.html', {'form': form, 'form_title': 'Add Gaming Gear'})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_edit_gear(request, gear_id):
    gear = get_object_or_404(GamingGear, gear_id=gear_id)
    if request.method == 'POST':
        form = GamingGearForm(request.POST, request.FILES, instance=gear)
        if form.is_valid():
            form.save()
            messages.success(request, 'Gaming Gear updated successfully!')
            return redirect('admin_gears')
        else:
            messages.error(request, 'Failed to update gear.')
    else:
        form = GamingGearForm(instance=gear)
    return render(request, 'APP01/admin_gaming_gear_form.html', {'form': form, 'form_title': 'Edit Gaming Gear'})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_delete_gear(request, gear_id):
    gear = get_object_or_404(GamingGear, gear_id=gear_id)
    if request.method == 'POST':
        gear_name = gear.name
        gear.delete()
        messages.success(request, f'Gaming Gear "{gear_name}" deleted successfully.')
    return redirect('admin_gears')

# --- Admin Member Management ---
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_members(request): # S_Admin_Members
    # แสดงเฉพาะ Role Member (ไม่รวม Admin)
    members = User.objects.filter(role__role_name='Member').order_by('-created_at')
    return render(request, 'APP01/admin_members.html', {'members': members})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_toggle_user_status(request, user_id):
    user_obj = get_object_or_404(User, pk=user_id)
    
    # ป้องกันไม่ให้แก้สถานะของ Admin ด้วยกันเอง หรือ Superuser
    if user_obj.is_superuser or (user_obj.role and user_obj.role.role_name == 'Admin'):
        messages.error(request, 'Cannot modify Admin accounts.')
        return redirect('admin_members')
    
    # สลับสถานะ Active (Ban/Unban)
    # สลับสถานะ Active (Ban/Unban)
    user_obj.is_active = not user_obj.is_active
    
    status = "activated"
    if not user_obj.is_active:
        user_obj.banned_at = timezone.now()
        status = "BANNED"
        messages.warning(request, f'User {user_obj.username} has been {status}.')
    else:
        user_obj.banned_at = None
        status = "activated"
        messages.success(request, f'User {user_obj.username} has been {status}.')
        
    user_obj.save()
    
    return redirect('admin_members')

# --- Admin AI Model Management ---
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_models(request): # S_Admin_Models
    models = AIModel.objects.all().order_by('-created_at')
    return render(request, 'APP01/admin_models.html', {'models': models})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_add_model(request): # S_Train_Model (Upload/Add new version)
    if request.method == 'POST':
        form = AIModelForm(request.POST, request.FILES)
        if form.is_valid():
            new_model = form.save(commit=False)
            # ถ้าโมเดลใหม่ถูกตั้งเป็น active ให้ deactivate ตัวอื่นก่อน
            if new_model.is_active:
                AIModel.objects.update(is_active=False)
            new_model.save()
            messages.success(request, 'New AI Model uploaded successfully.')
            return redirect('admin_models')
        else:
             messages.error(request, 'Failed to upload model. Please check the file.')
    else:
        form = AIModelForm()
    return render(request, 'APP01/admin_model_form.html', {'form': form})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_set_active_model(request, model_id): # S_Set_Active_Model
    target_model = get_object_or_404(AIModel, model_id=model_id)
    
    # Deactivate all, then activate target
    AIModel.objects.update(is_active=False)
    target_model.is_active = True
    target_model.save()
    
    # หมายเหตุ: ในระบบจริงอาจต้องมีการ reload ตัวแปร AI_MODEL ใน memory ด้วย
    messages.success(request, f'Model "{target_model.version_name}" is now active.')
    return redirect('admin_models')

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def admin_delete_model(request, model_id): # S_Del_Model
    model = get_object_or_404(AIModel, model_id=model_id)
    if model.is_active:
        messages.error(request, 'Cannot delete the active model. Please activate another model first.')
    else:
        model.delete()
        messages.success(request, 'Model deleted successfully.')
    return redirect('admin_models')

# --- Admin Alerts ---
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='home_member')
def mark_alert_read(request, alert_id):
    alert = get_object_or_404(Alert, alert_id=alert_id)
    alert.is_read = True
    alert.save()
    return redirect('admin_dashboard')

# APP01/views.py

# 1. เพิ่มฟังก์ชันใหม่สำหรับปุ่ม USE ALL
@login_required(login_url='login')
def use_all_gears(request, player_id):
    # ตรวจสอบ Session
    match_result = request.session.get('match_result', {})
    
    # กรณี Demo Data (ถ้า session เป็น mode demo)
    if match_result.get('mode') == 'demo':
        demo_list = match_result.get('demo_players_data', [])
        target_player = next((p for p in demo_list if p['player_id'] == player_id), None)
        
        if target_player:
            # ดึง ID ของอุปกรณ์ทั้งหมดของคนนั้น
            new_gear_ids = [g['gear_id'] for g in target_player['gears']]
            
            # อัปเดต Session
            match_result['temp_preset_gears'] = new_gear_ids
            # บันทึก ID ของ Player ที่เราเลือก Use All เพื่อนำไปแสดงรูปในหน้า Save
            match_result['selected_pro_id'] = player_id 
            request.session['match_result'] = match_result
            
            return redirect('save_preset')
            
    # กรณี Real Database
    try:
        player = ProPlayer.objects.get(player_id=player_id)
        gears = GamingGear.objects.filter(proplayergear__player=player)
        new_gear_ids = [g.gear_id for g in gears]
        
        if not match_result:
            match_result = {}
            
        match_result['temp_preset_gears'] = new_gear_ids
        match_result['selected_pro_id'] = player.player_id
        request.session['match_result'] = match_result
        
        return redirect('save_preset')
    except ProPlayer.DoesNotExist:
        messages.error(request, "Pro Player not found.")
        return redirect('matching_result')


# 2. ปรับปรุงฟังก์ชัน save_preset ให้ส่งข้อมูลครบถ้วนสำหรับหน้าจอใหม่
@login_required(login_url='login')
def save_preset(request):
    # 1. ดึง Dictionary 'match_result' จาก Session และรายการ ID อุปกรณ์ชั่วคราว
    match_result = request.session.get('match_result', {})
    gear_ids_to_save = match_result.get('temp_preset_gears', [])
    
    # === Logic การเติมเต็มอุปกรณ์ที่แนะนำโดยอัตโนมัติ (Autofill) ===
    # เช็คว่า user ลบทิ้งไปแล้วหรือยัง ถ้าลบแล้วไม่ต้อง autofill
    user_cleared = match_result.get('user_cleared_preset', False)
    
    if not gear_ids_to_save and match_result and not user_cleared:
        suggested_gear_ids = []
        if match_result.get('mode') == 'demo':
            demo_players = match_result.get('demo_players_data', [])
            if demo_players:
                best_match_gears = demo_players[0].get('gears', [])
                suggested_gear_ids = [g['gear_id'] for g in best_match_gears if g.get('gear_id')]
        
        elif match_result.get('mode') == 'real' and match_result.get('matched_player_id'):
            try:
                # ต้องมั่นใจว่ามีการ Import ProPlayer
                matched_player = ProPlayer.objects.get(player_id=match_result['matched_player_id'])
                # ต้องมั่นใจว่ามีการ Import GamingGear
                gears_qs = GamingGear.objects.filter(proplayergear__player=matched_player)
                suggested_gear_ids = [g.gear_id for g in gears_qs]
            except ProPlayer.DoesNotExist:
                pass

        if suggested_gear_ids:
            gear_ids_to_save = suggested_gear_ids
            match_result['temp_preset_gears'] = suggested_gear_ids
            request.session['match_result'] = match_result
            request.session.modified = True 
    # ====================================================================

    # 2. ถ้าสุดท้ายยังไม่มีอุปกรณ์ให้บันทึก (ทั้งที่เลือกเองและ Autofill)
    if not gear_ids_to_save:
        messages.error(request, 'No gears found in your temporary preset to save. Please select gears first.')
        return redirect('matching_result')

    # 3. เตรียมข้อมูลสำหรับแสดงผลและบันทึก (บังคับแปลงเป็น String)
    gear_ids_to_save_str = [str(gid) for gid in gear_ids_to_save]

    # พยายามดึง Object ของอุปกรณ์จาก DB เพื่อใช้ในการแสดงผล
    gears_for_display_qs = GamingGear.objects.filter(gear_id__in=gear_ids_to_save_str).order_by('gear_id')

    # ถ้าเป็น Demo Mode และไม่มีข้อมูลใน DB ให้สร้างรายชื่อแสดงผลจาก demo_players_data
    display_gears = []
    if match_result.get('mode') == 'demo':
        demo_players = match_result.get('demo_players_data', [])
        # สร้าง map ของ gear_id -> gear_info
        demo_map = {}
        for p in demo_players:
            for g in p.get('gears', []):
                demo_map[str(g.get('gear_id'))] = {
                    'gear_id': g.get('gear_id'),
                    'name': g.get('name'),
                    'category': g.get('category'),
                    'image_url': g.get('image_url')
                }

        for gid in gear_ids_to_save_str:
            if gid in demo_map:
                display_gears.append(demo_map[gid])
            else:
                # ถ้าไม่เจอใน demo_map ให้ลองหาจาก DB result (fallback)
                obj = gears_for_display_qs.filter(gear_id=gid).first()
                if obj:
                    display_gears.append({
                        'gear_id': obj.gear_id,
                        'name': obj.name,
                        'category': getattr(obj, 'type', 'Gear'),
                        'image_url': obj.image.url if obj.image else None,
                    })
    else:
        # สำหรับโหมด Real ให้แปลง QuerySet เป็น list ของ dict เพื่อให้ Template ใช้งานได้สม่ำเสมอ
        for obj in gears_for_display_qs:
            display_gears.append({
                'gear_id': obj.gear_id,
                'name': obj.name,
                'category': getattr(obj, 'type', 'Gear'),
                'image_url': obj.image.url if obj.image else None,
            })

    # แปลง ID เป็น string คั่นด้วยจุลภาค เพื่อใช้ใน Hidden Field ของ HTML
    gear_ids_string = ','.join(gear_ids_to_save_str)

    # กำหนดค่าเริ่มต้นสำหรับชื่อ Preset
    initial_preset_name = 'PRESET ' + str(Preset.objects.filter(user=request.user).count() + 1)

    if request.method == 'POST':
        form = PresetForm(request.POST)
        if form.is_valid():
            preset_name = form.cleaned_data['name']
            
            # ดึง ID อุปกรณ์จาก Hidden Field ใน POST data
            posted_gear_ids_string = request.POST.get('gears_to_save', '')
            
            # 🚨 [CODE ADDITION] 🚨
            print(f"DEBUG: Session IDs before POST: {gear_ids_to_save_str}") # จาก Session (ตัว String)
            print(f"DEBUG: POST Data String: {posted_gear_ids_string}") # จาก Hidden Field
            # 🚨 [END ADDITION] 🚨
            
            if posted_gear_ids_string:
                final_gear_ids = [s.strip() for s in posted_gear_ids_string.split(',') if s.strip()]
            else:
                final_gear_ids = gear_ids_to_save_str
            
            if not final_gear_ids:
                messages.error(request, 'Error: Could not retrieve any gears for saving.')
                return redirect('matching_result')
            
            # 1. สร้าง Preset ใหม่
            new_preset = Preset.objects.create(user=request.user, name=preset_name)
            
            # 2. บันทึก Gear ลงใน PresetGear (ส่วนแก้ไขสำคัญ)
            order = 1
            for gear_id in final_gear_ids:
                real_gear = None

                # A) ลอง Query ด้วย ID ที่เป็น String (Char/UUID) ก่อน
                real_gear = GamingGear.objects.filter(gear_id=gear_id).first()

                # B) ถ้าไม่พบ ลองแปลงเป็น Integer THEN Query (ถ้า ID เป็น Integer)
                if not real_gear:
                    try:
                        gear_id_int = int(gear_id)
                        real_gear = GamingGear.objects.filter(gear_id=gear_id_int).first()
                    except ValueError:
                        # Skip ถ้าแปลงไม่ได้
                        continue

                # C) ถ้ายังไม่พบ และเป็น Demo Mode ให้สร้าง GamingGear ชั่วคราวจาก demo data แล้วเชื่อมต่อ
                if not real_gear and match_result.get('mode') == 'demo':
                    demo_players = match_result.get('demo_players_data', [])
                    found = None
                    for p in demo_players:
                        for g in p.get('gears', []):
                            if str(g.get('gear_id')) == str(gear_id):
                                found = g
                                break
                        if found:
                            break

                    if found:
                        # สร้างหรือดึง GamingGear โดยใช้ข้อมูลจาก demo
                        real_gear, created = GamingGear.objects.get_or_create(
                            name=found.get('name'),
                            defaults={
                                'type': found.get('category', ''),
                                'brand': '',
                                'specs': '',
                                'price': None,
                                'store_url': '',
                                'image_url': found.get('image_url')
                            }
                        )

                if real_gear:
                    PresetGear.objects.create(preset=new_preset, gear=real_gear, order=order)
                    order += 1
            
            # ตรวจสอบว่ามีอุปกรณ์ถูกบันทึกหรือไม่
            if order == 1:
                messages.warning(request, f'Preset "{preset_name}" saved, but no gears were successfully linked (0 gears).')
            else:
                messages.success(request, f'Preset "{preset_name}" saved successfully with {order - 1} gears!')
            
            # 3. ล้าง Session ชั่วคราวหลังการบันทึกสำเร็จ
            if 'match_result' in request.session:
                del request.session['match_result']
                
            # Redirect ไปยังหน้า Detail ของ Preset ที่เพิ่งสร้าง
            return redirect('preset_detail', preset_id=new_preset.preset_id)
            
        else:
            messages.error(request, 'Please provide a valid name for your preset.')
            form = form # ใช้ form ที่มี error และค่าที่ผู้ใช้กรอกไว้
    
    else: # GET request
        # 4. สำหรับ GET request ให้กำหนดค่าเริ่มต้นของชื่อ Preset
        form = PresetForm(initial={'name': initial_preset_name})
        
    # 5. เตรียม Context สำหรับ Template
    context = {
        'display_gears': display_gears,
        'form': form, 
        'gear_ids_string': gear_ids_string, 
    }

    return render(request, 'APP01/save_preset.html', context)

@login_required(login_url='login')
def delete_preset(request, preset_id):
    """ลบ Preset ที่ระบุออกจากฐานข้อมูล"""
    
    # 1. ค้นหา Preset และตรวจสอบว่าเป็นของ User คนปัจจุบันหรือไม่
    # get_object_or_404 จะจัดการกรณีหาไม่เจอให้
    # user=request.user จะเป็นการป้องกันไม่ให้ลบ Preset ของคนอื่น
    preset = get_object_or_404(Preset, preset_id=preset_id, user=request.user)
    
    # 2. ทำการลบ
    # การลบ Preset จะลบ PresetGear ที่เชื่อมโยงทั้งหมดผ่าน CASCADE Delete
    preset_name = preset.name
    preset.delete()
    
    messages.success(request, f'Preset "{preset_name}" has been deleted successfully.')
    
    # 3. Redirect กลับไปหน้า Manage Presets
    return redirect('manage_presets')


@login_required(login_url='login')
def replace_gear(request, preset_id, old_gear_id):
    preset = get_object_or_404(Preset, preset_id=preset_id, user=request.user)
    old_gear = get_object_or_404(GamingGear, gear_id=old_gear_id)
    preset_gear = get_object_or_404(PresetGear, preset=preset, gear=old_gear)
    same_type_gears = GamingGear.objects.filter(type=old_gear.type)
    gears_in_preset = preset.presetgear_set.values_list('gear_id', flat=True)
    available_gears = same_type_gears.exclude(gear_id__in=gears_in_preset)
    context = {'preset': preset, 'old_gear': old_gear, 'available_gears': available_gears}
    return render(request, 'APP01/replace_gear.html', context)

@login_required(login_url='login')
def confirm_replace(request, preset_id, old_gear_id, new_gear_id):
    preset = get_object_or_404(Preset, preset_id=preset_id, user=request.user)
    old_gear = get_object_or_404(GamingGear, gear_id=old_gear_id)
    new_gear = get_object_or_404(GamingGear, gear_id=new_gear_id)
    try:
        preset_gear = PresetGear.objects.get(preset=preset, gear=old_gear)
    except PresetGear.DoesNotExist:
        messages.error(request, 'The gear you are trying to replace is not in this preset.')
        return redirect('preset_detail', preset_id=preset.preset_id)
    if old_gear.type != new_gear.type:
        messages.error(request, 'Cannot replace ' + old_gear.type + ' with ' + new_gear.type + '. Must be same type.')
        return redirect('preset_detail', preset_id=preset.preset_id)
    if PresetGear.objects.filter(preset=preset, gear=new_gear).exists():
        messages.error(request, new_gear.name + ' is already in this preset.')
        return redirect('preset_detail', preset_id=preset.preset_id)
    preset_gear.gear = new_gear
    preset_gear.save()
    messages.success(request, 'Successfully replaced ' + old_gear.name + ' with ' + new_gear.name + '!')
    return redirect('preset_detail', preset_id=preset.preset_id)
