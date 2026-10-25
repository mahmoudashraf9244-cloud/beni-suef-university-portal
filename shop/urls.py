from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),

    path('activities/', views.activity_list, name='activity_list'),

    path('activities/<int:activity_id>/', views.activity_detail, name='activity_detail'),
    path('activities/<int:activity_id>/enroll/', views.enroll_activity, name='enroll_activity'),

    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='shop/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='shop:home'), name='logout'),

    path('profile/', views.student_profile, name='student_profile'),
    path('profile/edit/', views.edit_student_profile, name='edit_student_profile'),
]
