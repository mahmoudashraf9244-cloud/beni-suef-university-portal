from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import get_language, gettext_lazy as _

from .models import StudentProfile


class ActivityFilterForm(forms.Form):
    q = forms.CharField(required=False)
    category = forms.IntegerField(
        required=False,
        min_value=1,
        # SQLite integer IDs must fit in a signed 64-bit integer.
        max_value=2**63 - 1,
    )


class UserRegisterForm(UserCreationForm):
    first_name = forms.CharField(label=_('First name'), max_length=150, required=True)
    last_name = forms.CharField(label=_('Last name'), max_length=150, required=True)
    email = forms.EmailField(label=_('Email'), required=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            message = (
                'يوجد حساب مسجل بهذا البريد الإلكتروني بالفعل.'
                if get_language().startswith('ar')
                else 'An account with this email address already exists.'
            )
            raise forms.ValidationError(message)
        return email


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ('phone_number', 'university', 'faculty', 'academic_year')
        labels = {'phone_number': _('Phone number'), 'university': _('University'),
                  'faculty': _('Faculty'), 'academic_year': _('Academic year')}
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'university': forms.TextInput(attrs={'class': 'form-control'}),
            'faculty': forms.TextInput(attrs={'class': 'form-control'}),
            'academic_year': forms.TextInput(attrs={'class': 'form-control'}),
        }
