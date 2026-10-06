from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, SchoolClass


class BaseSignUpForm(UserCreationForm):
    first_name = forms.CharField(label='Имя', max_length=50)
    last_name = forms.CharField(label='Фамилия', max_length=50)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'password1', 'password2')


class StudentSignUpForm(BaseSignUpForm):
    school_class = forms.ModelChoiceField(
        label='Класс',
        queryset=SchoolClass.objects.all(),
        required=False,
        empty_label='— выберите класс —'
    )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'
        user.school_class = self.cleaned_data.get('school_class')
        if user.school_class:
            user.grade = user.school_class.grade
        if commit:
            user.save()
        return user


class TeacherSignUpForm(BaseSignUpForm):
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'teacher'
        if commit:
            user.save()
        return user