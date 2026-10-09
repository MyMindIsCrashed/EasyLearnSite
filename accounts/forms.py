from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, SchoolClass


AVATAR_EMOJIS = [
    ('🧑', 'Ученик'),
    ('👦', 'Мальчик'),
    ('👧', 'Девочка'),
    ('🧒', 'Ребёнок'),
    ('🐱', 'Котик'),
    ('🐶', 'Собачка'),
    ('🦊', 'Лисёнок'),
    ('🐼', 'Панда'),
    ('🦁', 'Лев'),
    ('🐯', 'Тигр'),
    ('🐸', 'Лягушка'),
    ('🦄', 'Единорог'),
    ('🐉', 'Дракон'),
    ('🚀', 'Ракета'),
    ('⭐', 'Звезда'),
    ('🎓', 'Выпускник'),
    ('👩‍🏫', 'Учительница'),
    ('👨‍🏫', 'Учитель'),
    ('🧙', 'Волшебник'),
    ('🦸', 'Супергерой'),
]


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
    avatar_emoji = forms.ChoiceField(
        label='Аватар',
        choices=AVATAR_EMOJIS,
        initial='🧑',
        widget=forms.RadioSelect,
        required=False,
    )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'
        user.school_class = self.cleaned_data.get('school_class')
        if user.school_class:
            user.grade = user.school_class.grade
        user.avatar_emoji = self.cleaned_data.get('avatar_emoji') or '🧑'
        if commit:
            user.save()
        return user


class TeacherSignUpForm(BaseSignUpForm):
    avatar_emoji = forms.ChoiceField(
        label='Аватар',
        choices=AVATAR_EMOJIS,
        initial='👩‍🏫',
        widget=forms.RadioSelect,
        required=False,
    )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'teacher'
        user.avatar_emoji = self.cleaned_data.get('avatar_emoji') or '👩‍🏫'
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    avatar_emoji = forms.ChoiceField(
        label='Эмодзи-аватар',
        choices=AVATAR_EMOJIS,
        widget=forms.RadioSelect,
        required=False,
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'avatar_emoji', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'avatar': 'Своя картинка (необязательно)',
        }