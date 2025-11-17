from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Admin Dashboard
    path('dashboard/', views.admin_dashboard, name='home'),
    
    # User Management
    path('add-user/', views.add_user_view, name='add_user'),
    path('manage-users/', views.manage_users_view, name='manage_users'),
    path('delete-user/<int:user_id>/', views.delete_user_view, name='delete_user'),
    
    # Question Management
    path('add-question/', views.add_question_view, name='add_question'),
    
    # Analytics
    path('analytics/', views.analytics_dashboard_view, name='analytics_dashboard'),
    
    # Public Feedback Forms (No login required)
    path('feedback/student/', views.student_feedback_view, name='student_feedback'),
    path('feedback/alumni/', views.alumni_feedback_view, name='alumni_feedback'),
    path('feedback/employer/', views.employer_feedback_view, name='employer_feedback'),
    path('feedback/thanks/', views.thank_you_view, name='thank_you'),
]
