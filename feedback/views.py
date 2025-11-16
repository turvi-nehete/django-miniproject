from django.shortcuts import render, redirect
from django.db.models import Avg
from django.contrib.auth.models import User
from .models import Question, FeedbackResponse, Option
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
import io
import base64

# Homepage view
def home_view(request):
    return render(request, 'feedback/home.html')


# Feedback form for students
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


# Feedback form for alumni
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


# Feedback form for employers
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


# Thank you page
def thank_you_view(request):
    return render(request, 'feedback/thank_you.html')


# Add question view
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
            # Handle MCQ options if provided
            if question_type == "mcq":
                options = request.POST.get('options')
                if options:
                    for opt in options.split(','):
                        Option.objects.create(question=question, text=opt.strip())

            return redirect('home')

    return render(request, 'feedback/add_question.html')


# Analytics dashboard with charts
def analytics_dashboard_view(request):
    stakeholders = ['student', 'alumni', 'employer']
    grouped_data = []

    for st in stakeholders:
        # Questions by type and stakeholder
        rating_qs = Question.objects.filter(stakeholder_type=st, question_type='rating')
        mcq_qs = Question.objects.filter(stakeholder_type=st, question_type='mcq')

        # Rating data
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
                question_labels.append(q.text)  # Full question text, no truncation
                avg_ratings.append(avg_rating)

        # Generate Bar Chart for Ratings
        rating_chart = None
        if avg_ratings:
            rating_chart = generate_bar_chart(question_labels, avg_ratings, 
                                              f'{st.title()} - Average Ratings',
                                              'Questions', 'Average Rating (out of 5)')

        # MCQ data
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
            
            # Generate Pie Chart for each MCQ
            if total > 0:
                pie_chart = generate_pie_chart(option_labels, option_counts, q.text)  # Full question text
                mcq_charts.append({
                    'question': q.text,
                    'category': q.category,
                    'chart': pie_chart
                })

        # Add to final grouped result
        grouped_data.append({
            'stakeholder': st,
            'rating_data': rating_data,
            'mcq_data': mcq_data,
            'rating_chart': rating_chart,
            'mcq_charts': mcq_charts
        })

    # Generate Overall Comparison Chart
    overall_chart = generate_overall_comparison(stakeholders)

    return render(request, 'feedback/analytics_dashboard.html', {
        'grouped_data': grouped_data,
        'overall_chart': overall_chart
    })


def generate_bar_chart(labels, values, title, xlabel, ylabel):
    """Generate a bar chart and return as base64 encoded image"""
    # Wrap long labels into multiple lines
    wrapped_labels = []
    for label in labels:
        if len(label) > 25:
            # Split into multiple lines, max 25 chars per line
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
            
            wrapped_labels.append('\n'.join(lines[:3]))  # Max 3 lines
        else:
            wrapped_labels.append(label)
    
    # Adjust figure size based on number of items and label length
    width = min(14, max(10, len(labels) * 1.5))
    height = 6.5  # Increased height for wrapped labels
    plt.figure(figsize=(width, height))
    
    # Create color gradient based on values
    colors = ['#f56565' if v < 3 else '#ed8936' if v < 4 else '#48bb78' for v in values]
    
    bars = plt.bar(range(len(wrapped_labels)), values, color=colors, alpha=0.85, 
                   edgecolor='#2d3748', linewidth=1.2, width=0.65)
    
    # Add value labels on top of bars
    for i, (bar, val) in enumerate(zip(bars, values)):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{val:.2f}',
                ha='center', va='bottom', fontweight='bold', fontsize=10, color='#2d3748')
    
    plt.xlabel(xlabel, fontsize=11, fontweight='600', color='#4a5568', labelpad=10)
    plt.ylabel(ylabel, fontsize=11, fontweight='600', color='#4a5568')
    plt.title(title, fontsize=12, fontweight='bold', pad=15, color='#2d3748')
    
    # Set x-axis with wrapped labels
    plt.xticks(range(len(wrapped_labels)), wrapped_labels, 
               rotation=0, ha='center', fontsize=9, multialignment='center')
    plt.yticks(fontsize=9)
    plt.ylim(0, 5.5)
    plt.grid(axis='y', alpha=0.2, linestyle='--', linewidth=0.8)
    
    # Add more space at bottom for labels
    plt.subplots_adjust(bottom=0.3)
    plt.tight_layout()
    
    # Convert plot to base64 string
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight', facecolor='white', edgecolor='none')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()
    
    graphic = base64.b64encode(image_png).decode('utf-8')
    return graphic


def generate_pie_chart(labels, values, title):
    """Generate a pie chart and return as base64 encoded image"""
    if sum(values) == 0:
        return None
    
    # Wrap long title into multiple lines
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
        
        wrapped_title = '\n'.join(lines[:3])  # Max 3 lines
    else:
        wrapped_title = title
        
    plt.figure(figsize=(7, 7))
    
    colors = ['#667eea', '#764ba2', '#48bb78', '#ed8936', '#f56565', '#4299e1']
    
    # Create pie chart with better text visibility
    wedges, texts, autotexts = plt.pie(values, labels=labels, autopct='%1.1f%%',
                                        colors=colors, startangle=90,
                                        textprops={'fontsize': 9, 'fontweight': '600'},
                                        pctdistance=0.85)
    
    # Make percentage text white and bold
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(9)
    
    # Make labels darker and more readable
    for text in texts:
        text.set_color('#2d3748')
        text.set_fontsize(8.5)
        text.set_fontweight('600')
    
    plt.title(wrapped_title, fontsize=10, fontweight='bold', pad=20, color='#2d3748')
    plt.axis('equal')
    plt.tight_layout(pad=2)
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight', facecolor='white', edgecolor='none')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()
    
    graphic = base64.b64encode(image_png).decode('utf-8')
    return graphic


def generate_overall_comparison(stakeholders):
    """Generate overall comparison chart across all stakeholders"""
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
    
    # Add value labels
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