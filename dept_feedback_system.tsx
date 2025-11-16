# Department Feedback & Improvement System - Django Project

## Complete Step-by-Step Setup Guide

### Step 1: Install Required Software

Open Command Prompt/Terminal and run:

```bash
# Install Python (if not installed) - Download from python.org
# Then install Django and Pillow
pip install django pillow
```

### Step 2: Create Project Structure

```bash
# Navigate to where you want to create the project
cd Desktop  # or any folder you prefer

# Create Django project
django-admin startproject feedback_system
cd feedback_system

# Create Django app
python manage.py startapp feedback
```

### Step 3: Configure settings.py

Open `feedback_system/settings.py` and make these changes:

```python
# Find INSTALLED_APPS and add 'feedback' to it:
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'feedback',  # Add this line
]

# At the bottom of the file, add:
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'
```

### Step 4: Create Models

Create/Replace `feedback/models.py`:

```python
from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('alumni', 'Alumni'),
        ('employer', 'Employer'),
        ('admin', 'Admin/HOD'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    department = models.CharField(max_length=100, blank=True)
    batch = models.CharField(max_length=10, blank=True)
    company = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"

class Question(models.Model):
    STAKEHOLDER_CHOICES = [
        ('student', 'Student'),
        ('alumni', 'Alumni'),
        ('employer', 'Employer'),
    ]
    
    text = models.TextField()
    category = models.CharField(max_length=50)
    stakeholder_type = models.CharField(max_length=20, choices=STAKEHOLDER_CHOICES)
    
    def __str__(self):
        return f"{self.stakeholder_type}: {self.text[:50]}"

class FeedbackResponse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    department = models.CharField(max_length=100)
    batch = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.question.text[:30]}"
```

### Step 5: Create Views

Create/Replace `feedback/views.py`:

```python
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg, Count
from django.http import HttpResponse
from .models import UserProfile, Question, FeedbackResponse
import csv
from datetime import datetime

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'feedback/login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'feedback/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role == 'admin':
        # Admin dashboard with analytics
        total_responses = FeedbackResponse.objects.count()
        total_students = UserProfile.objects.filter(role='student').count()
        total_alumni = UserProfile.objects.filter(role='alumni').count()
        total_employers = UserProfile.objects.filter(role='employer').count()
        
        # Average ratings by category
        categories = Question.objects.values_list('category', flat=True).distinct()
        category_ratings = []
        for cat in categories:
            avg = FeedbackResponse.objects.filter(
                question__category=cat
            ).aggregate(Avg('rating'))['rating__avg']
            if avg:
                category_ratings.append({'category': cat, 'rating': round(avg, 2)})
        
        # Top and bottom performing areas
        question_ratings = []
        for q in Question.objects.all():
            avg = FeedbackResponse.objects.filter(question=q).aggregate(Avg('rating'))['rating__avg']
            if avg:
                question_ratings.append({
                    'question': q.text,
                    'category': q.category,
                    'rating': round(avg, 2)
                })
        
        question_ratings.sort(key=lambda x: x['rating'])
        weak_areas = question_ratings[:3]
        strong_areas = question_ratings[-3:][::-1]
        
        # Monthly trend
        monthly_data = FeedbackResponse.objects.extra(
            select={'month': "strftime('%%Y-%%m', created_at)"}
        ).values('month').annotate(avg_rating=Avg('rating')).order_by('month')
        
        context = {
            'profile': profile,
            'total_responses': total_responses,
            'total_students': total_students,
            'total_alumni': total_alumni,
            'total_employers': total_employers,
            'category_ratings': category_ratings,
            'weak_areas': weak_areas,
            'strong_areas': strong_areas,
            'monthly_data': list(monthly_data),
        }
        return render(request, 'feedback/admin_dashboard.html', context)
    else:
        # User dashboard
        my_responses = FeedbackResponse.objects.filter(user=request.user).count()
        context = {
            'profile': profile,
            'my_responses': my_responses,
        }
        return render(request, 'feedback/user_dashboard.html', context)

@login_required
def submit_feedback(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role == 'admin':
        return redirect('dashboard')
    
    questions = Question.objects.filter(stakeholder_type=profile.role)
    
    if request.method == 'POST':
        for question in questions:
            rating = request.POST.get(f'rating_{question.id}')
            comment = request.POST.get(f'comment_{question.id}', '')
            
            if rating:
                FeedbackResponse.objects.create(
                    user=request.user,
                    question=question,
                    rating=int(rating),
                    comment=comment,
                    department=profile.department,
                    batch=profile.batch if profile.batch else ''
                )
        
        return render(request, 'feedback/feedback_success.html')
    
    context = {
        'profile': profile,
        'questions': questions,
    }
    return render(request, 'feedback/submit_feedback.html', context)

@login_required
def export_report(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.role != 'admin':
        return redirect('dashboard')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="feedback_report_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Question', 'Category', 'Stakeholder', 'Average Rating', 'Total Responses'])
    
    for question in Question.objects.all():
        avg = FeedbackResponse.objects.filter(question=question).aggregate(Avg('rating'))['rating__avg']
        count = FeedbackResponse.objects.filter(question=question).count()
        
        writer.writerow([
            question.text,
            question.category,
            question.stakeholder_type,
            round(avg, 2) if avg else 'N/A',
            count
        ])
    
    return response
```

### Step 6: Create URLs

Create `feedback/urls.py`:

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('submit-feedback/', views.submit_feedback, name='submit_feedback'),
    path('export-report/', views.export_report, name='export_report'),
]
```

Update `feedback_system/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('feedback.urls')),
]
```

### Step 7: Create Templates

Create folder structure: `feedback/templates/feedback/`

**Create `feedback/templates/feedback/base.html`:**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Feedback System{% endblock %}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .navbar {
            background: rgba(255, 255, 255, 0.95);
            padding: 1rem 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .navbar h1 {
            color: #667eea;
            font-size: 1.5rem;
        }
        
        .navbar-right {
            display: flex;
            gap: 1rem;
            align-items: center;
        }
        
        .navbar-right span {
            color: #333;
            font-weight: 500;
        }
        
        .btn {
            padding: 0.6rem 1.5rem;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1rem;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: #667eea;
            color: white;
        }
        
        .btn-primary:hover {
            background: #5568d3;
            transform: translateY(-2px);
        }
        
        .btn-secondary {
            background: #48bb78;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #38a169;
        }
        
        .btn-danger {
            background: #f56565;
            color: white;
        }
        
        .btn-danger:hover {
            background: #e53e3e;
        }
        
        .container {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 1rem;
        }
        
        .card {
            background: white;
            border-radius: 10px;
            padding: 2rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 1.5rem;
        }
        
        .card h2 {
            color: #667eea;
            margin-bottom: 1rem;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 10px;
            text-align: center;
        }
        
        .stat-card h3 {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        
        .stat-card p {
            opacity: 0.9;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }
        
        table th, table td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        
        table th {
            background: #f7fafc;
            color: #2d3748;
            font-weight: 600;
        }
        
        table tr:hover {
            background: #f7fafc;
        }
        
        .form-group {
            margin-bottom: 1.5rem;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            color: #2d3748;
            font-weight: 500;
        }
        
        .form-group input, .form-group select, .form-group textarea {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #cbd5e0;
            border-radius: 5px;
            font-size: 1rem;
        }
        
        .form-group textarea {
            resize: vertical;
            min-height: 80px;
        }
        
        .rating-group {
            display: flex;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }
        
        .rating-group input[type="radio"] {
            display: none;
        }
        
        .rating-group label {
            width: 40px;
            height: 40px;
            background: #e2e8f0;
            border-radius: 5px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .rating-group input[type="radio"]:checked + label {
            background: #667eea;
            color: white;
            transform: scale(1.1);
        }
        
        .alert {
            padding: 1rem;
            border-radius: 5px;
            margin-bottom: 1rem;
        }
        
        .alert-success {
            background: #c6f6d5;
            color: #22543d;
            border: 1px solid #9ae6b4;
        }
        
        .alert-error {
            background: #fed7d7;
            color: #742a2a;
            border: 1px solid #fc8181;
        }
        
        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        .badge-high {
            background: #c6f6d5;
            color: #22543d;
        }
        
        .badge-medium {
            background: #feebc8;
            color: #7c2d12;
        }
        
        .badge-low {
            background: #fed7d7;
            color: #742a2a;
        }
    </style>
</head>
<body>
    {% if user.is_authenticated %}
    <nav class="navbar">
        <h1>🎓 Feedback System</h1>
        <div class="navbar-right">
            <span>{{ user.first_name }} ({{ profile.role|title }})</span>
            <a href="{% url 'dashboard' %}" class="btn btn-primary">Dashboard</a>
            {% if profile.role != 'admin' %}
            <a href="{% url 'submit_feedback' %}" class="btn btn-secondary">Submit Feedback</a>
            {% endif %}
            <a href="{% url 'logout' %}" class="btn btn-danger">Logout</a>
        </div>
    </nav>
    {% endif %}
    
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
```

**Create `feedback/templates/feedback/login.html`:**

```html
{% extends 'feedback/base.html' %}

{% block title %}Login - Feedback System{% endblock %}

{% block content %}
<div style="max-width: 400px; margin: 5rem auto;">
    <div class="card">
        <h2 style="text-align: center; margin-bottom: 2rem;">🎓 Department Feedback System</h2>
        
        {% if error %}
        <div class="alert alert-error">{{ error }}</div>
        {% endif %}
        
        <form method="post">
            {% csrf_token %}
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" required>
            </div>
            
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required>
            </div>
            
            <button type="submit" class="btn btn-primary" style="width: 100%;">Login</button>
        </form>
        
        <div style="margin-top: 2rem; padding: 1rem; background: #f7fafc; border-radius: 5px;">
            <p style="font-weight: 600; margin-bottom: 0.5rem;">Demo Credentials:</p>
            <p><strong>Admin:</strong> admin / admin123</p>
            <p><strong>Student:</strong> student1 / student123</p>
            <p><strong>Alumni:</strong> alumni1 / alumni123</p>
            <p><strong>Employer:</strong> employer1 / employer123</p>
        </div>
    </div>
</div>
{% endblock %}
```

**Create `feedback/templates/feedback/admin_dashboard.html`:**

```html
{% extends 'feedback/base.html' %}

{% block title %}Admin Dashboard{% endblock %}

{% block content %}
<h1 style="color: white; margin-bottom: 2rem;">📊 Analytics Dashboard</h1>

<div class="stats-grid">
    <div class="stat-card">
        <h3>{{ total_responses }}</h3>
        <p>Total Responses</p>
    </div>
    <div class="stat-card">
        <h3>{{ total_students }}</h3>
        <p>Students</p>
    </div>
    <div class="stat-card">
        <h3>{{ total_alumni }}</h3>
        <p>Alumni</p>
    </div>
    <div class="stat-card">
        <h3>{{ total_employers }}</h3>
        <p>Employers</p>
    </div>
</div>

<div class="card">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <h2>📈 Performance Analysis</h2>
        <a href="{% url 'export_report' %}" class="btn btn-secondary">⬇ Export Report (CSV)</a>
    </div>
</div>

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
    <div class="card">
        <h2>🌟 Top Performing Areas</h2>
        <table>
            <thead>
                <tr>
                    <th>Area</th>
                    <th>Category</th>
                    <th>Rating</th>
                </tr>
            </thead>
            <tbody>
                {% for area in strong_areas %}
                <tr>
                    <td>{{ area.question|truncatewords:8 }}</td>
                    <td>{{ area.category }}</td>
                    <td><span class="badge badge-high">{{ area.rating }}/5</span></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    <div class="card">
        <h2>⚠️ Areas Needing Improvement</h2>
        <table>
            <thead>
                <tr>
                    <th>Area</th>
                    <th>Category</th>
                    <th>Rating</th>
                </tr>
            </thead>
            <tbody>
                {% for area in weak_areas %}
                <tr>
                    <td>{{ area.question|truncatewords:8 }}</td>
                    <td>{{ area.category }}</td>
                    <td><span class="badge badge-low">{{ area.rating }}/5</span></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<div class="card">
    <h2>📊 Average Ratings by Category</h2>
    <table>
        <thead>
            <tr>
                <th>Category</th>
                <th>Average Rating</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {% for cat in category_ratings %}
            <tr>
                <td>{{ cat.category }}</td>
                <td>{{ cat.rating }}/5</td>
                <td>
                    {% if cat.rating >= 4 %}
                    <span class="badge badge-high">Excellent</span>
                    {% elif cat.rating >= 3 %}
                    <span class="badge badge-medium">Good</span>
                    {% else %}
                    <span class="badge badge-low">Needs Work</span>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<div class="card">
    <h2>📅 Monthly Trend</h2>
    <table>
        <thead>
            <tr>
                <th>Month</th>
                <th>Average Rating</th>
            </tr>
        </thead>
        <tbody>
            {% for month in monthly_data %}
            <tr>
                <td>{{ month.month }}</td>
                <td>{{ month.avg_rating|floatformat:2 }}/5</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
```

**Create `feedback/templates/feedback/user_dashboard.html`:**

```html
{% extends 'feedback/base.html' %}

{% block title %}Dashboard{% endblock %}

{% block content %}
<h1 style="color: white; margin-bottom: 2rem;">👋 Welcome, {{ user.first_name }}!</h1>

<div class="card">
    <h2>Your Profile</h2>
    <p><strong>Role:</strong> {{ profile.role|title }}</p>
    <p><strong>Department:</strong> {{ profile.department }}</p>
    {% if profile.batch %}
    <p><strong>Batch:</strong> {{ profile.batch }}</p>
    {% endif %}
    {% if profile.company %}
    <p><strong>Company:</strong> {{ profile.company }}</p>
    {% endif %}
</div>

<div class="card">
    <h2>Your Feedback Status</h2>
    <p>You have submitted <strong>{{ my_responses }}</strong> feedback responses.</p>
    <a href="{% url 'submit_feedback' %}" class="btn btn-primary" style="margin-top: 1rem;">Submit New Feedback</a>
</div>

<div class="card">
    <h2>Why Your Feedback Matters</h2>
    <p>Your feedback helps the department identify areas of improvement and maintain high quality education. Thank you for contributing to continuous quality enhancement!</p>
</div>
{% endblock %}
```

**Create `feedback/templates/feedback/submit_feedback.html`:**

```html
{% extends 'feedback/base.html' %}

{% block title %}Submit Feedback{% endblock %}

{% block content %}
<h1 style="color: white; margin-bottom: 2rem;">📝 Submit Feedback</h1>

<div class="card">
    <h2>Feedback Form - {{ profile.role|title }}</h2>
    <p style="color: #718096; margin-bottom: 2rem;">Please rate each aspect on a scale of 1-5 (1 = Poor, 5 = Excellent)</p>
    
    <form method="post">
        {% csrf_token %}
        
        {% for question in questions %}
        <div style="padding: 1.5rem; background: #f7fafc; border-radius: 5px; margin-bottom: 1.5rem;">
            <h3 style="color: #2d3748; margin-bottom: 1rem;">{{ question.text }}</h3>
            <p style="color: #718096; font-size: 0.875rem; margin-bottom: 0.5rem;">Category: {{ question.category }}</p>
            
            <div class="form-group">
                <label>Rating *</label>
                <div class="rating-group">
                    {% for i in "12345" %}
                    <input type="radio" name="rating_{{ question.id }}" id="rating_{{ question.id }}_{{ i }}" value="{{ i }}" required>
                    <label for="rating_{{ question.id }}_{{ i }}">{{ i }}</label>
                    {% endfor %}
                </div>
            </div>
            
            <div class="form-group">
                <label>Comments (Optional)</label>
                <textarea name="comment_{{ question.id }}" placeholder="Share your thoughts..."></textarea>
            </div>
        </div>
        {% endfor %}
        
        <button type="submit" class="btn btn-primary" style="width: 100%; padding: 1rem; font-size: 1.1rem;">Submit Feedback</button>
    </form>
</div>
{% endblock %}
```

**Create `feedback/templates/feedback/feedback_success.html`:**

```html
{% extends 'feedback/base.html' %}

{% block title %}Feedback Submitted{% endblock %}

{% block content %}
<div style="max-width: 600px; margin: 5rem auto;">
    <div class="card" style="text-align: center;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">✅</div>
        <h2>Thank You for Your Feedback!</h2>
        <p style="color: #718096; margin: 1rem 0;">Your responses have been successfully submitted and will help us improve our services.</p>
        <a href="{% url 'dashboard' %}" class="btn btn-primary" style="margin-top: 1rem;">Back to Dashboard</a>
    </div>
</div>
{% endblock %}
```

### Step 8: Create Admin Interface

Create/Replace `feedback/admin.py`:

```python
from django.contrib import admin
from .models import UserProfile, Question, FeedbackResponse

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'department', 'batch']
    list_filter = ['role', 'department']
    search_fields = ['user__username', 'department']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'category', 'stakeholder_type']
    list_filter = ['stakeholder_type', 'category']
    search_fields = ['text', 'category']

@admin.register(FeedbackResponse)
class FeedbackResponseAdmin(admin.ModelAdmin):
    list_display = ['user', 'question', 'rating', 'department', 'created_at']
    list_filter = ['rating', 'department', 'created_at']
    search_fields = ['user__username', 'comment']
    date_hierarchy = 'created_at'
```

### Step 9: Run Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 10: Create Superuser and Sample Data

```bash
# Create admin superuser
python manage.py createsuperuser
# Username: admin
# Email: admin@example.com  
# Password: admin123
```

### Step 11: Add Sample Data via Django Shell

```bash
python manage.py shell
```

Then paste this code:

```python
from django.contrib.auth.models import User
from feedback.models import UserProfile, Question

# Create sample users
users_data = [
    {'username': 'student1', 'password': 'student123', 'first_name': 'John', 'last_name': 'Doe'},
    {'username': 'alumni1', 'password': 'alumni123', 'first_name': 'Jane', 'last_name': 'Smith'},
    {'username': 'employer1', 'password': 'employer123', 'first_name': 'HR', 'last_name': 'Manager'},
]

for data in users_data:
    user = User.objects.create_user(
        username=data['username'],
        password=data['password'],
        first_name=data['first_name'],
        last_name=data['last_name']
    )

# Create admin profile
admin_user = User.objects.get(username='admin')
UserProfile.objects.create(user=admin_user, role='admin', department='Computer Science')

# Create other profiles
student = User.objects.get(username='student1')
UserProfile.objects.create(user=student, role='student', department='Computer Science', batch='2024')

alumni = User.objects.get(username='alumni1')
UserProfile.objects.create(user=alumni, role='alumni', department='Computer Science', batch='2022')

employer = User.objects.get(username='employer1')
UserProfile.objects.create(user=employer, role='employer', company='Tech Corp')

# Create questions for students
student_questions = [
    {'text': 'Quality of teaching', 'category': 'Teaching', 'type': 'student'},
    {'text': 'Course content relevance', 'category': 'Curriculum', 'type': 'student'},
    {'text': 'Lab facilities and equipment', 'category': 'Infrastructure', 'type': 'student'},
    {'text': 'Faculty availability and support', 'category': 'Teaching', 'type': 'student'},
    {'text': 'Learning resources (library, online)', 'category': 'Resources', 'type': 'student'},
]

# Create questions for alumni
alumni_questions = [
    {'text': 'Curriculum prepared me for career', 'category': 'Curriculum', 'type': 'alumni'},
    {'text': 'Placement assistance quality', 'category': 'Placements', 'type': 'alumni'},
    {'text': 'Industry connections and exposure', 'category': 'Industry', 'type': 'alumni'},
    {'text': 'Skill development programs', 'category': 'Skills', 'type': 'alumni'},
    {'text': 'Overall educational experience', 'category': 'Overall', 'type': 'alumni'},
]

# Create questions for employers
employer_questions = [
    {'text': 'Technical skills of graduates', 'category': 'Skills', 'type': 'employer'},
    {'text': 'Problem-solving abilities', 'category': 'Skills', 'type': 'employer'},
    {'text': 'Work readiness and professionalism', 'category': 'Professionalism', 'type': 'employer'},
    {'text': 'Communication skills', 'category': 'Communication', 'type': 'employer'},
    {'text': 'Adaptability to workplace', 'category': 'Adaptability', 'type': 'employer'},
]

all_questions = student_questions + alumni_questions + employer_questions

for q in all_questions:
    Question.objects.create(
        text=q['text'],
        category=q['category'],
        stakeholder_type=q['type']
    )

print("Sample data created successfully!")
exit()
```

Press Ctrl+D (or Ctrl+Z on Windows) to exit the shell.

### Step 12: Run the Development Server

```bash
python manage.py runserver
```

You should see:
```
Starting development server at http://127.0.0.1:8000/
```

### Step 13: Access Your Application

Open your web browser and go to:
- **Main Application:** http://127.0.0.1:8000/
- **Admin Panel:** http://127.0.0.1:8000/admin/

### Step 14: Test the System

**Login Credentials:**
- **Admin:** username: `admin`, password: `admin123`
- **Student:** username: `student1`, password: `student123`
- **Alumni:** username: `alumni1`, password: `alumni123`
- **Employer:** username: `employer1`, password: `employer123`

### Step 15: Add More Sample Feedback (Optional)

To see analytics, add some sample feedback:

```bash
python manage.py shell
```

Paste this code:

```python
from django.contrib.auth.models import User
from feedback.models import Question, FeedbackResponse
import random

# Get users
student = User.objects.get(username='student1')
alumni = User.objects.get(username='alumni1')
employer = User.objects.get(username='employer1')

# Add student feedback
student_questions = Question.objects.filter(stakeholder_type='student')
for q in student_questions:
    FeedbackResponse.objects.create(
        user=student,
        question=q,
        rating=random.randint(3, 5),
        comment="Sample feedback from student",
        department="Computer Science",
        batch="2024"
    )

# Add alumni feedback
alumni_questions = Question.objects.filter(stakeholder_type='alumni')
for q in alumni_questions:
    FeedbackResponse.objects.create(
        user=alumni,
        question=q,
        rating=random.randint(3, 5),
        comment="Sample feedback from alumni",
        department="Computer Science",
        batch="2022"
    )

# Add employer feedback
employer_questions = Question.objects.filter(stakeholder_type='employer')
for q in employer_questions:
    FeedbackResponse.objects.create(
        user=employer,
        question=q,
        rating=random.randint(2, 5),
        comment="Sample feedback from employer",
        department="Computer Science"
    )

print("Sample feedback added!")
exit()
```

## Project Structure Summary

```
feedback_system/
│
├── feedback_system/
│   ├── __init__.py
│   ├── settings.py          # Django settings
│   ├── urls.py              # Main URL configuration
│   └── wsgi.py
│
├── feedback/
│   ├── migrations/
│   ├── templates/
│   │   └── feedback/
│   │       ├── base.html
│   │       ├── login.html
│   │       ├── admin_dashboard.html
│   │       ├── user_dashboard.html
│   │       ├── submit_feedback.html
│   │       └── feedback_success.html
│   ├── __init__.py
│   ├── admin.py             # Admin interface
│   ├── models.py            # Database models
│   ├── views.py             # View functions
│   └── urls.py              # App URLs
│
├── db.sqlite3               # Database file
└── manage.py                # Django management script
```

## Features Implemented

✅ **User Roles & Authentication**
- Student, Alumni, Employer, Admin roles
- Secure login/logout system
- Role-based access control

✅ **Feedback Forms**
- Separate questions for each stakeholder type
- 1-5 rating scale
- Optional comments
- Category-based questions

✅ **Admin Dashboard**
- Total response statistics
- Category-wise average ratings
- Top 3 performing areas
- Bottom 3 areas needing improvement
- Monthly trend analysis
- Export to CSV functionality

✅ **User Dashboard**
- Profile information
- Feedback submission status
- Easy navigation

✅ **Responsive Design**
- Clean, modern UI
- Mobile-friendly
- Purple gradient theme
- Smooth animations

## How to Use

### For Students/Alumni/Employers:
1. Login with credentials
2. Go to "Submit Feedback"
3. Rate each question (1-5)
4. Add optional comments
5. Submit

### For Admin/HOD:
1. Login with admin credentials
2. View analytics dashboard
3. Identify strong and weak areas
4. Export reports for documentation
5. Track trends over time

## Troubleshooting

**If you get "No such table" error:**
```bash
python manage.py makemigrations
python manage.py migrate
```

**If static files don't load:**
```bash
python manage.py collectstatic
```

**To reset the database:**
```bash
# Delete db.sqlite3 file
# Then run:
python manage.py migrate
python manage.py createsuperuser
# Add sample data again
```

**Port already in use:**
```bash
python manage.py runserver 8080
```

## Adding More Users

Via Admin Panel (http://127.0.0.1:8000/admin/):
1. Login as admin
2. Go to "Users" → "Add User"
3. Create user
4. Go to "User Profiles" → "Add User Profile"
5. Link to user and set role, department, etc.

## Customization

**To add more departments:**
Edit `views.py` line with departments list:
```python
departments = ['Computer Science', 'Electronics', 'Mechanical', 'Civil', 'Your Department']
```

**To add more questions:**
Via Admin Panel → Questions → Add Question

**To change colors:**
Edit the CSS in `base.html` (gradient, button colors, etc.)

## Next Steps for Production

1. Use PostgreSQL instead of SQLite
2. Set `DEBUG = False` in settings.py
3. Configure proper ALLOWED_HOSTS
4. Use environment variables for SECRET_KEY
5. Set up proper email notifications
6. Add more advanced analytics (charts with Chart.js)
7. Implement pagination for large datasets
8. Add data export in Excel format
9. Set up automated backup system

---

Your project is now complete and ready to use! 🎉