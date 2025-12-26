# APP01/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # --- Guest & Common Features ---
    path('', views.home_guest, name='home_guest'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    
    # Matching Core
    path('upload-image/', views.upload_image_and_match, name='upload_image'),
    path('upload-image-ajax/', views.upload_image_ajax, name='upload_image_ajax'),
    path('matching-result/', views.matching_result, name='matching_result'),
    path('matching-result/submit-rating/', views.submit_rating, name='submit_rating'), # ใช้ตัวนี้แทน rate_match
    
    # Temporary Preset Editing (Session based)
    path('matching-result/edit-preset/<str:action>/<int:gear_id>/', views.edit_temp_preset, name='edit_temp_preset_with_id'),
    path('matching-result/edit-preset/<str:action>/', views.edit_temp_preset, name='edit_temp_preset_no_id'),

    # Information & Search
    path('search/', views.global_search, name='global_search'),
    path('gear/<int:gear_id>/', views.gear_detail, name='gear_detail'),
    path('pro-player/<int:player_id>/', views.pro_player_detail, name='pro_player_detail'),
    path('search/gear/', views.search_gear, name='search_gear'),
    path('search/pro-player/', views.search_pro_player, name='search_pro_player'),

    # --- Member Features ---
    path('member/home/', views.home_member, name='home_member'),
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # Presets Management (Database)
    path('presets/', views.manage_presets, name='manage_presets'),
    path('preset/save/', views.save_preset, name='save_preset'),
    path('preset/<int:preset_id>/', views.preset_detail, name='preset_detail'),
    path('preset/<int:preset_id>/edit/', views.edit_preset, name='edit_preset'),
    path('preset/<int:preset_id>/edit-name/', views.edit_preset_name, name='edit_preset_name'),
    path('preset/<int:preset_id>/delete/', views.delete_preset, name='delete_preset'),
    path('preset/use-all/<int:player_id>/', views.use_all_gears, name='use_all_gears'),
    
    # Replace Gear in Preset
    path('preset/<int:preset_id>/replace-gear/<int:old_gear_id>/', views.replace_gear, name='replace_gear'),
    path('preset/<int:preset_id>/replace-gear/<int:old_gear_id>/with/<int:new_gear_id>/', views.confirm_replace, name='confirm_replace'),
    
    # Share Preset
    path('preset/<int:preset_id>/share/', views.share_preset, name='share_preset'),
    path('share/<str:share_link>/', views.view_shared_preset, name='view_shared_preset'),

    # --- Admin Features ---
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/users/', views.admin_users, name='admin_users'),
    path('admin-dashboard/users/edit/<int:user_id>/', views.admin_edit_user, name='admin_edit_user'),

    # Admin: Pro Players
    path('admin-dashboard/pro-players/', views.admin_pro_players, name='admin_pro_players'),
    path('admin-dashboard/pro-players/add/', views.admin_add_pro_player, name='admin_add_pro_player'),
    path('admin-dashboard/pro-players/<int:player_id>/edit/', views.admin_edit_pro_player, name='admin_edit_pro_player'),
    path('admin-dashboard/pro-players/<int:player_id>/delete/', views.admin_delete_pro_player, name='admin_delete_pro_player'),

    # Admin: Gaming Gears (แก้ไขชื่อให้ตรงกับ views.py)
    path('admin-dashboard/gears/', views.admin_gears, name='admin_gears'),
    path('admin-dashboard/gears/add/', views.admin_add_gear, name='admin_add_gear'),
    path('admin-dashboard/gears/<int:gear_id>/edit/', views.admin_edit_gear, name='admin_edit_gear'),
    path('admin-dashboard/gears/<int:gear_id>/delete/', views.admin_delete_gear, name='admin_delete_gear'),
    
    # Admin: AI Models (แก้ไขชื่อให้ตรงกับ views.py)
    path('admin-dashboard/models/', views.admin_models, name='admin_models'),
    path('admin-dashboard/models/add/', views.admin_add_model, name='admin_add_model'),
    path('admin-dashboard/models/<int:model_id>/delete/', views.admin_delete_model, name='admin_delete_model'),
    path('admin-dashboard/models/<int:model_id>/set-active/', views.admin_set_active_model, name='admin_set_active_model'),
    
    # Admin: Members Management (แก้ไขให้ตรงกับ views.py)
    path('admin-dashboard/members/', views.admin_members, name='admin_members'),
    path('admin-dashboard/members/<int:user_id>/toggle-status/', views.admin_toggle_user_status, name='admin_toggle_user_status'),

    # Admin: Alerts
    path('admin-dashboard/alerts/<int:alert_id>/mark-read/', views.mark_alert_read, name='mark_alert_read'),
]