from django.urls import path
from . import views
urlpatterns = [
     path('', views.home_view, name='home'),

     path('feedback/student/', views.student_feedback_view, name='student_feedback'),
     path('feedback/alumni/', views.alumni_feedback_view, name='alumni_feedback'),
     path('feedback/employer/', views.employer_feedback_view, name='employer_feedback'),

     path('add-question/', views.add_question_view, name='add_question'),

     path('analytics/', views.analytics_dashboard_view, name='analytics_dashboard'),
        
     path('feedback/thanks/', views.thank_you_view, name='thank_you'),
 ]



