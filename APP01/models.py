# APP01/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import uuid # สำหรับ share_link ที่ไม่ซ้ำกัน

# --- Custom User Manager ---
# models.py

class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password) # <--- บรรทัดนี้สำคัญมาก
        
        # 🚨 การแก้ไขที่สำคัญ: กำหนดบทบาท 'Member' 🚨
        try:
            member_role = Role.objects.get(role_name='Member')
        except Role.DoesNotExist:
            # สร้าง Role 'Member' ถ้ายังไม่มี
            member_role = Role.objects.create(role_name='Member')
        
        # กำหนด Role ให้กับ User
        user.role = member_role 
        
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        # ส่วนนี้จัดการ Role Admin ได้ถูกต้องแล้ว
        try:
            admin_role = Role.objects.get(role_name='Admin')
        except Role.DoesNotExist:
            admin_role = Role.objects.create(role_name='Admin')
        
        # กำหนด Role 'Admin' ใน extra_fields ก่อนเรียก create_user
        extra_fields['role'] = admin_role 

        return self.create_user(email, username, password, **extra_fields)

# --- Role Model ---
class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.role_name

# --- Custom User Model ---
class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=100, unique=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True)
    profile_image = models.ImageField(upload_to='user_profiles/', blank=True, null=True) # รูปโปรไฟล์
    created_at = models.DateTimeField(default=timezone.now)
    banned_at = models.DateTimeField(null=True, blank=True) # เวลาที่ถูกแบน

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # แก้ไขตรงนี้: เพิ่มฟิลด์ groups และ user_permissions พร้อม related_name
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name="app01_user_set", # <-- เพิ่ม related_name ที่ไม่ซ้ำกัน
        related_query_name="app01_user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="app01_user_permissions_set", # <-- เพิ่ม related_name ที่ไม่ซ้ำกัน
        related_query_name="app01_user_permission",
    )
    # สังเกตว่าเราไม่ได้นำเข้า Group หรือ Permission ตรงๆ แต่ใช้สตริง 'auth.Group'

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username

    def has_perm(self, perm, obj=None):
        return self.is_superuser # หรือตรวจสอบตาม role/permission ที่ซับซ้อนกว่านี้

    def has_module_perms(self, app_label):
        return self.is_superuser # หรือตรวจสอบตาม role/permission ที่ซับซ้อนกว่านี้


# --- ProPlayer Model ---
class ProPlayer(models.Model):
    player_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    game = models.CharField(max_length=50)
    bio = models.TextField(blank=True, null=True) # เพิ่ม Bio
    settings = models.JSONField(default=dict, blank=True) # เพิ่ม Settings (JSON)
    physique_vector = models.TextField(blank=True, null=True) 
    image = models.ImageField(upload_to='pro_players/', blank=True, null=True) # เปลี่ยนจาก URL เป็น ImageField
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

# --- GamingGear Model ---
class GamingGear(models.Model):
    gear_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=50) # e.g., Mouse, Keyboard, Headset
    brand = models.CharField(max_length=50)
    specs = models.TextField(blank=True, null=True) # เก็บรายละเอียดสเปคเป็น JSON string
    description = models.TextField(blank=True, null=True) # คำอธิบายอุปกรณ์
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    store_url = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(upload_to='gaming_gears/', blank=True, null=True) # เปลี่ยนจาก URL เป็น ImageField
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.brand} {self.name} ({self.type})"

# --- Preset Model ---
class Preset(models.Model):
    preset_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    share_link = models.CharField(max_length=255, unique=True, blank=True, null=True) # สร้างเมื่อกดแชร์
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} by {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.share_link:
            self.share_link = str(uuid.uuid4()) # สร้าง UUID เมื่อสร้าง Preset
        super().save(*args, **kwargs)

# --- ProPlayerGear (Many-to-Many through) ---
class ProPlayerGear(models.Model):
    player = models.ForeignKey(ProPlayer, on_delete=models.CASCADE)
    gear = models.ForeignKey(GamingGear, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('player', 'gear') # หนึ่ง ProPlayer มี Gear ซ้ำกันไม่ได้

    def __str__(self):
        return f"{self.player.name} uses {self.gear.name}"

# --- PresetGear (Many-to-Many through) ---
class PresetGear(models.Model):
    preset = models.ForeignKey(Preset, on_delete=models.CASCADE)
    gear = models.ForeignKey(GamingGear, on_delete=models.CASCADE)
    order = models.IntegerField(default=0) # ลำดับการแสดงผล

    class Meta:
        unique_together = ('preset', 'gear') # หนึ่ง Preset มี Gear ซ้ำกันไม่ได้
        ordering = ['order'] # เรียงตามลำดับ

    def __str__(self):
        return f"{self.preset.name} includes {self.gear.name} (Order: {self.order})"

# --- Rating Model ---
class Rating(models.Model):
    rating_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    proplayer = models.ForeignKey(ProPlayer, on_delete=models.CASCADE)
    feedback_score = models.CharField(max_length=10, choices=[('Good', 'Good'), ('Neutral', 'Neutral'), ('Bad', 'Bad')]) # 'Good', 'Neutral', 'Bad'
    comment = models.TextField(blank=True, null=True)
    # Metadata to help improve matching models
    match_image_url = models.CharField(max_length=512, blank=True, null=True)
    selected_gears = models.TextField(blank=True, null=True)  # store JSON array of gear ids or names
    match_distance = models.FloatField(blank=True, null=True)
    rated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'proplayer') # ผู้ใช้ 1 คน ให้คะแนน Pro Player 1 คนได้แค่ครั้งเดียว

    def __str__(self):
        return f"Rating by {self.user.username} for {self.proplayer.name}: {self.feedback_score}"

# --- Alert Model ---
class Alert(models.Model):
    alert_id = models.AutoField(primary_key=True)
    message = models.TextField()
    type = models.CharField(max_length=50) # e.g., 'new_gear', 'new_proplayer', 'member_ban'
    created_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    related_entity_id = models.IntegerField(null=True, blank=True) # ID ของ Entity ที่เกี่ยวข้อง
    related_entity_type = models.CharField(max_length=50, null=True, blank=True) # ประเภทของ Entity ที่เกี่ยวข้อง

    def __str__(self):
        return f"Alert ({self.type}): {self.message[:50]}..."

# --- AIModel Model ---
class AIModel(models.Model):
    model_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=20)
    file_path = models.CharField(max_length=255) # Path ไปยังไฟล์โมเดล
    created_at = models.DateTimeField(default=timezone.now)
    last_trained_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False) # true ถ้าเป็นโมเดลที่ใช้งานอยู่ปัจจุบัน

    def __str__(self):
        return f"{self.name} (v{self.version}) - {'Active' if self.is_active else 'Inactive'}"