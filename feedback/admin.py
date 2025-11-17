from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Question, Option, FeedbackResponse

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'category', 'stakeholder_type', 'question_type']
    list_filter = ['stakeholder_type', 'question_type', 'category']
    search_fields = ['text', 'category']

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ['text', 'question']
    list_filter = ['question']

@admin.register(FeedbackResponse)
class FeedbackResponseAdmin(admin.ModelAdmin):
    list_display = ['question', 'response_value', 'stakeholder', 'created_at']
    list_filter = ['stakeholder', 'created_at']
    date_hierarchy = 'created_at'