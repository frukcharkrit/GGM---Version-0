from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.urls import reverse

class BannedUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ตรวจสอบว่า user login อยู่หรือไม่ และถูกแบนหรือไม่
        if request.user.is_authenticated and not request.user.is_active:
            # ดึงเวลาที่ถูกแบน
            banned_time = getattr(request.user, 'banned_at', None)
            
            # Logout ผู้ใช้
            logout(request)
            
            # สร้างข้อความแจ้งเตือน
            msg = "บัญชีของคุณถูกระงับการใช้งาน"
            if banned_time:
                # จัดรูปแบบวันที่และเวลา (แปลงเป็น Local Time)
                from django.utils import timezone
                local_time = timezone.localtime(banned_time)
                formatted_time = local_time.strftime('%d/%m/%Y %H:%M')
                msg += f" เมื่อวันที่ {formatted_time}"
            
            # ส่งข้อความแจ้งเตือน (ควรแสดงในหน้า Login)
            messages.error(request, msg)
            
            # Redirect ไปหน้า Login
            return redirect('login') 

        response = self.get_response(request)
        return response
