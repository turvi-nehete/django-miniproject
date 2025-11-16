from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.db.models import Avg
from django.contrib.auth.models import User
from .models import Question, FeedbackResponse,Option

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

    user, created = User.objects.get_or_create(username="anonymous_alumni")

    if request.method == 'POST':
        for question in questions:
            rating = request.POST.get(f'rating_{question.id}')
            comment = request.POST.get(f'comment_{question.id}', '')

            if rating:
                FeedbackResponse.objects.create(
                    user=user,
                    question=question,
                    rating=int(rating),
                    comment=comment
                )
        return redirect('thank_you')

    return render(request, 'feedback/alumni_feedback.html', {'questions': questions})


# Feedback form for employers
def employer_feedback_view(request):
    questions = Question.objects.filter(stakeholder_type='employer')

    user, created = User.objects.get_or_create(username="anonymous_employer")

    if request.method == 'POST':
        for question in questions:
            rating = request.POST.get(f'rating_{question.id}')
            comment = request.POST.get(f'comment_{question.id}', '')

            if rating:
                FeedbackResponse.objects.create(
                    user=user,
                    question=question,
                    rating=int(rating),
                    comment=comment
                )
        return redirect('thank_you')

    return render(request, 'feedback/employer_feedback.html', {'questions': questions})


# Thank you page
def thank_you_view(request):
    return render(request, 'feedback/thank_you.html')


# Simple analytics dashboard: average rating per question
def analytics_dashboard_view(request):
    stakeholders = ['student', 'alumni', 'employer']  # groups
    grouped_data = []

    for st in stakeholders:
        # Questions by type and stakeholder
        rating_qs = Question.objects.filter(stakeholder_type=st, question_type='rating')
        mcq_qs = Question.objects.filter(stakeholder_type=st, question_type='mcq')

        # Rating data
        rating_data = []
        for q in rating_qs:
            responses = FeedbackResponse.objects.filter(question=q)
            ratings = [int(r.response_value) for r in responses if r.response_value.isdigit()]
            avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else "No data"
            rating_data.append({
                'question': q.text,
                'category': q.category,
                'avg_rating': avg_rating
            })

        # MCQ data
        mcq_data = []
        for q in mcq_qs:
            options = []
            total = FeedbackResponse.objects.filter(question=q).count()
            for opt in q.options.all():
                count = FeedbackResponse.objects.filter(question=q, response_value=opt.text).count()
                percent = f"{(count / total * 100):.1f}%" if total else "0%"
                options.append({'option': opt.text, 'count': count, 'percent': percent})
            mcq_data.append({
                'question': q.text,
                'category': q.category,
                'options': options
            })

        # Add to final grouped result
        grouped_data.append({
            'stakeholder': st,
            'rating_data': rating_data,
            'mcq_data': mcq_data
        })

    return render(request, 'feedback/analytics_dashboard.html', {'grouped_data': grouped_data})



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
                options = request.POST.get('options')  # comma-separated values
                if options:
                    for opt in options.split(','):
                        Option.objects.create(question=question, text=opt.strip())

            return redirect('home')

    return render(request, 'feedback/add_question.html')