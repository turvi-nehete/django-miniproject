from django.db import models

class Question(models.Model):
    STAKEHOLDER_CHOICES = [
        ('student', 'Student'),
        ('alumni', 'Alumni'),
        ('employer', 'Employer'),
    ]
    QUESTION_TYPE_CHOICES = [
        ('rating', 'Rating (1–5)'),
        ('mcq', 'Multiple Choice'),
    ]
    
    text = models.TextField()
    category = models.CharField(max_length=50)
    stakeholder_type = models.CharField(max_length=20, choices=STAKEHOLDER_CHOICES)
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES, default='rating')
    
    def __str__(self):
        return f"{self.stakeholder_type}: {self.text[:50]}"

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=255)
    
    def __str__(self):
        return self.text

class FeedbackResponse(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    response_value = models.CharField(max_length=255)  # for rating or selected option
    stakeholder = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.question.text[:30]} - {self.response_value}"
