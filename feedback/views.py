from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Avg
from .models import Question, FeedbackResponse, Option
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

# ==================== AUTHENTICATION ====================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'feedback/login.html')

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('login')

# ==================== ADMIN DASHBOARD ====================

@login_required
def admin_dashboard(request):
    total_users = User.objects.count()
    total_questions = Question.objects.count()
    total_responses = FeedbackResponse.objects.count()
    
    recent_responses = FeedbackResponse.objects.all().order_by('-created_at')[:5]
    
    context = {
        'total_users': total_users,
        'total_questions': total_questions,
        'total_responses': total_responses,
        'recent_responses': recent_responses,
    }
    return render(request, 'feedback/admin_dashboard.html', context)

# ==================== USER MANAGEMENT ====================

@login_required
def add_user_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        else:
            User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            messages.success(request, f'User "{username}" created successfully!')
            return redirect('manage_users')
    
    return render(request, 'feedback/add_user.html')

@login_required
def manage_users_view(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'feedback/manage_users.html', {'users': users})

@login_required
def delete_user_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if user == request.user:
        messages.error(request, 'You cannot delete yourself')
    else:
        username = user.username
        user.delete()
        messages.success(request, f'User "{username}" deleted successfully')
    
    return redirect('manage_users')

# ==================== PUBLIC FEEDBACK FORMS (No Login) ====================

def student_feedback_view(request):
    questions = Question.objects.filter(stakeholder_type='student')
    
    if request.method == 'POST':
        for q in questions:
            answer = request.POST.get(f'q_{q.id}')
            if answer:
                FeedbackResponse.objects.create(
                    question=q,
                    response_value=answer,
                    stakeholder='student',
                )
        return redirect('thank_you')
    
    return render(request, 'feedback/student_feedback.html', {'questions': questions})

def alumni_feedback_view(request):
    questions = Question.objects.filter(stakeholder_type='alumni')
    
    if request.method == 'POST':
        for q in questions:
            answer = request.POST.get(f'q_{q.id}')
            if answer:
                FeedbackResponse.objects.create(
                    question=q,
                    response_value=answer,
                    stakeholder='alumni',
                )
        return redirect('thank_you')
    
    return render(request, 'feedback/alumni_feedback.html', {'questions': questions})

def employer_feedback_view(request):
    questions = Question.objects.filter(stakeholder_type='employer')
    
    if request.method == 'POST':
        for q in questions:
            answer = request.POST.get(f'q_{q.id}')
            if answer:
                FeedbackResponse.objects.create(
                    question=q,
                    response_value=answer,
                    stakeholder='employer',
                )
        return redirect('thank_you')
    
    return render(request, 'feedback/employer_feedback.html', {'questions': questions})

def thank_you_view(request):
    return render(request, 'feedback/thank_you.html')

# ==================== QUESTION MANAGEMENT ====================

@login_required
def add_question_view(request):
    if request.method == "POST":
        text = request.POST.get('text')
        category = request.POST.get('category')
        stakeholder_type = request.POST.get('stakeholder_type')
        question_type = request.POST.get('question_type')

        if text and category and stakeholder_type and question_type:
            question = Question.objects.create(
                text=text,
                category=category,
                stakeholder_type=stakeholder_type,
                question_type=question_type
            )
            
            if question_type == "mcq":
                options = request.POST.get('options')
                if options:
                    for opt in options.split(','):
                        Option.objects.create(question=question, text=opt.strip())
            
            messages.success(request, 'Question added successfully!')
            return redirect('home')

    return render(request, 'feedback/add_question.html')

# ==================== ANALYTICS ====================

@login_required
def analytics_dashboard_view(request):
    stakeholders = ['student', 'alumni', 'employer']
    grouped_data = []

    for st in stakeholders:
        rating_qs = Question.objects.filter(stakeholder_type=st, question_type='rating')
        mcq_qs = Question.objects.filter(stakeholder_type=st, question_type='mcq')

        rating_data = []
        question_labels = []
        avg_ratings = []
        
        for q in rating_qs:
            responses = FeedbackResponse.objects.filter(question=q)
            ratings = [int(r.response_value) for r in responses if r.response_value.isdigit()]
            avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0
            
            rating_data.append({
                'question': q.text,
                'category': q.category,
                'avg_rating': avg_rating if ratings else "No data"
            })
            
            if ratings:
                question_labels.append(q.text)
                avg_ratings.append(avg_rating)

        rating_chart = None
        if avg_ratings:
            rating_chart = generate_bar_chart(question_labels, avg_ratings, 
                                              f'{st.title()} - Average Ratings',
                                              'Questions', 'Average Rating (out of 5)')

        mcq_data = []
        mcq_charts = []
        
        for q in mcq_qs:
            options = []
            option_labels = []
            option_counts = []
            total = FeedbackResponse.objects.filter(question=q).count()
            
            for opt in q.options.all():
                count = FeedbackResponse.objects.filter(question=q, response_value=opt.text).count()
                percent = f"{(count / total * 100):.1f}%" if total else "0%"
                options.append({'option': opt.text, 'count': count, 'percent': percent})
                option_labels.append(opt.text)
                option_counts.append(count)
            
            mcq_data.append({
                'question': q.text,
                'category': q.category,
                'options': options
            })
            
            if total > 0:
                pie_chart = generate_pie_chart(option_labels, option_counts, q.text)
                mcq_charts.append({
                    'question': q.text,
                    'category': q.category,
                    'chart': pie_chart
                })

        grouped_data.append({
            'stakeholder': st,
            'rating_data': rating_data,
            'mcq_data': mcq_data,
            'rating_chart': rating_chart,
            'mcq_charts': mcq_charts
        })

    overall_chart = generate_overall_comparison(stakeholders)

    return render(request, 'feedback/analytics_dashboard.html', {
        'grouped_data': grouped_data,
        'overall_chart': overall_chart
    })

# ==================== CHART GENERATION ====================

def generate_bar_chart(labels, values, title, xlabel, ylabel):
    wrapped_labels = []
    for label in labels:
        if len(label) > 25:
            words = label.split()
            lines = []
            current_line = []
            current_length = 0
            
            for word in words:
                if current_length + len(word) + 1 <= 25:
                    current_line.append(word)
                    current_length += len(word) + 1
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = len(word)
            
            if current_line:
                lines.append(' '.join(current_line))
            
            wrapped_labels.append('\n'.join(lines[:3]))
        else:
            wrapped_labels.append(label)
    
    width = min(14, max(10, len(labels) * 1.5))
    height = 6.5
    plt.figure(figsize=(width, height))
    
    colors = ['#f56565' if v < 3 else '#ed8936' if v < 4 else '#48bb78' for v in values]
    
    bars = plt.bar(range(len(wrapped_labels)), values, color=colors, alpha=0.85, 
                   edgecolor='#2d3748', linewidth=1.2, width=0.65)
    
    for i, (bar, val) in enumerate(zip(bars, values)):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{val:.2f}',
                ha='center', va='bottom', fontweight='bold', fontsize=10, color='#2d3748')
    
    plt.xlabel(xlabel, fontsize=11, fontweight='600', color='#4a5568', labelpad=10)
    plt.ylabel(ylabel, fontsize=11, fontweight='600', color='#4a5568')
    plt.title(title, fontsize=12, fontweight='bold', pad=15, color='#2d3748')
    
    plt.xticks(range(len(wrapped_labels)), wrapped_labels, 
               rotation=0, ha='center', fontsize=9, multialignment='center')
    plt.yticks(fontsize=9)
    plt.ylim(0, 5.5)
    plt.grid(axis='y', alpha=0.2, linestyle='--', linewidth=0.8)
    
    plt.subplots_adjust(bottom=0.3)
    plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight', facecolor='white', edgecolor='none')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()
    
    graphic = base64.b64encode(image_png).decode('utf-8')
    return graphic

def generate_pie_chart(labels, values, title):
    if sum(values) == 0:
        return None
    
    if len(title) > 50:
        words = title.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= 50:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        wrapped_title = '\n'.join(lines[:3])
    else:
        wrapped_title = title
        
    plt.figure(figsize=(8, 8))
    
    colors = ['#667eea', '#764ba2', '#48bb78', '#ed8936', '#f56565', '#4299e1']
    
    wedges, texts, autotexts = plt.pie(values, autopct='%1.1f%%',
                                        colors=colors, startangle=90,
                                        textprops={'fontsize': 10, 'fontweight': 'bold'},
                                        pctdistance=0.85, labeldistance=1.15)
    
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(11)
    
    plt.legend(wedges, labels, 
              title="Options",
              loc="center left",
              bbox_to_anchor=(1, 0, 0.5, 1),
              fontsize=10,
              title_fontsize=11,
              frameon=True,
              fancybox=True,
              shadow=True)
    
    plt.title(wrapped_title, fontsize=11, fontweight='bold', pad=25, color='#2d3748')
    plt.axis('equal')
    
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight', facecolor='white', edgecolor='none')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()
    
    graphic = base64.b64encode(image_png).decode('utf-8')
    return graphic

def generate_overall_comparison(stakeholders):
    stakeholder_avgs = []
    labels = []
    
    for st in stakeholders:
        rating_qs = Question.objects.filter(stakeholder_type=st, question_type='rating')
        all_ratings = []
        
        for q in rating_qs:
            responses = FeedbackResponse.objects.filter(question=q)
            ratings = [int(r.response_value) for r in responses if r.response_value.isdigit()]
            all_ratings.extend(ratings)
        
        if all_ratings:
            avg = round(sum(all_ratings) / len(all_ratings), 2)
            stakeholder_avgs.append(avg)
            labels.append(st.title())
    
    if not stakeholder_avgs:
        return None
    
    plt.figure(figsize=(8, 4))
    
    colors = ['#667eea', '#48bb78', '#ed8936']
    bars = plt.barh(labels, stakeholder_avgs, color=colors, alpha=0.85, 
                    edgecolor='#2d3748', linewidth=1.2, height=0.6)
    
    for i, (bar, val) in enumerate(zip(bars, stakeholder_avgs)):
        plt.text(val + 0.08, bar.get_y() + bar.get_height()/2, 
                f'{val:.2f}/5',
                va='center', fontweight='bold', fontsize=9, color='#2d3748')
    
    plt.xlabel('Average Rating (out of 5)', fontsize=10, fontweight='600', color='#4a5568')
    plt.title('Overall Satisfaction by Stakeholder', fontsize=11, fontweight='bold', pad=15, color='#2d3748')
    plt.xlim(0, 5.5)
    plt.xticks(fontsize=8)
    plt.yticks(fontsize=9, fontweight='600')
    plt.grid(axis='x', alpha=0.2, linestyle='--', linewidth=0.8)
    plt.tight_layout(pad=1.5)
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight', facecolor='white', edgecolor='none')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()
    
    graphic = base64.b64encode(image_png).decode('utf-8')
    return graphic