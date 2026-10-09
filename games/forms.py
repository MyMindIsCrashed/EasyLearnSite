from django import forms
from .models import Question, AnswerOption


class QuestionForm(forms.ModelForm):
    option_1 = forms.CharField(label='Вариант 1', max_length=300)
    option_2 = forms.CharField(label='Вариант 2', max_length=300)
    option_3 = forms.CharField(label='Вариант 3', max_length=300, required=False)
    option_4 = forms.CharField(label='Вариант 4', max_length=300, required=False)

    correct = forms.ChoiceField(
        label='Правильный ответ',
        choices=[('1', 'Вариант 1'), ('2', 'Вариант 2'),
                 ('3', 'Вариант 3'), ('4', 'Вариант 4')],
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Question
        fields = ['text', 'points']
        widgets = {
            'text': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Например: Сколько будет 2+2?',
                'autofocus': True,
            }),
            'points': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 10,
                'max': 100,
                'value': 10,
            }),
        }
        labels = {
            'text': 'Вопрос',
            'points': 'Баллы за верный ответ (мин. 10)',
        }

    def __init__(self, *args, **kwargs):
        self.game = kwargs.pop('game', None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            options = list(self.instance.options.all())
            for i, opt in enumerate(options[:4], start=1):
                self.fields[f'option_{i}'].initial = opt.text
                if opt.is_correct:
                    self.fields['correct'].initial = str(i)

        for i in range(1, 5):
            self.fields[f'option_{i}'].widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Вариант {i}',
            })

    def clean_points(self):
        points = self.cleaned_data.get('points', 0)
        if points < 10:
            raise forms.ValidationError('Минимум 10 баллов за вопрос')
        return points

    def clean(self):
        cleaned = super().clean()
        correct = cleaned.get('correct')
        correct_text = cleaned.get(f'option_{correct}') if correct else None
        if correct and not correct_text:
            self.add_error(f'option_{correct}', 'Правильный вариант пустой')

        filled = [cleaned.get(f'option_{i}') for i in range(1, 5)]
        filled = [f for f in filled if f]
        if len(filled) < 2:
            raise forms.ValidationError('Заполни хотя бы 2 варианта ответа')
        return cleaned

    def save(self, commit=True):
        question = super().save(commit=False)
        if self.game:
            question.game = self.game
        if not question.pk:
            last = Question.objects.filter(game=question.game).order_by('-order').first()
            question.order = (last.order + 1) if last else 1
        if commit:
            question.save()

        if question.pk:
            question.options.all().delete()

        correct = self.cleaned_data['correct']
        for i in range(1, 5):
            text = self.cleaned_data.get(f'option_{i}')
            if text:
                AnswerOption.objects.create(
                    question=question, text=text,
                    is_correct=(str(i) == correct),
                )
        return question