from django import forms
from django.contrib.auth.password_validation import validate_password

from .models import Company


class CompanyOnboardingForm(forms.Form):
    company_name = forms.CharField(
        label='Όνομα εταιρείας',
        max_length=255
    )
    branch_name = forms.CharField(
        label='Όνομα πρώτου υποκαταστήματος',
        max_length=150
    )
    branch_address = forms.CharField(
        label='Διεύθυνση υποκαταστήματος',
        max_length=255,
        required=False
    )
    branch_latitude = forms.DecimalField(
        label='Latitude',
        required=False,
        max_digits=9,
        decimal_places=6
    )
    branch_longitude = forms.DecimalField(
        label='Longitude',
        required=False,
        max_digits=9,
        decimal_places=6
    )
    admin_username = forms.CharField(
        label='Username admin',
        max_length=150
    )
    admin_password = forms.CharField(
        label='Password admin',
        widget=forms.PasswordInput
    )
    default_category_name = forms.CharField(
        label='Προεπιλεγμένη κατηγορία',
        max_length=100,
        initial='Γενικά'
    )
    default_unit_name = forms.CharField(
        label='Προεπιλεγμένη μονάδα',
        max_length=100,
        initial='Τεμάχιο'
    )
    default_unit_code = forms.CharField(
        label='Κωδικός μονάδας',
        max_length=20,
        initial='pcs'
    )


class CompanySettingsForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['display_name', 'support_email', 'support_phone', 'primary_color']
        widgets = {
            'display_name': forms.TextInput(attrs={'class': 'w-full rounded-2xl border border-slate-300 px-4 py-3'}),
            'support_email': forms.EmailInput(attrs={'class': 'w-full rounded-2xl border border-slate-300 px-4 py-3'}),
            'support_phone': forms.TextInput(attrs={'class': 'w-full rounded-2xl border border-slate-300 px-4 py-3'}),
            'primary_color': forms.TextInput(attrs={'class': 'w-full rounded-2xl border border-slate-300 px-4 py-3', 'placeholder': '#0f172a'}),
        }


class ForcePasswordChangeForm(forms.Form):
    new_password1 = forms.CharField(
        label='Νέος κωδικός',
        widget=forms.PasswordInput(attrs={'class': 'w-full rounded-2xl border border-slate-300 px-4 py-3'})
    )
    new_password2 = forms.CharField(
        label='Επιβεβαίωση νέου κωδικού',
        widget=forms.PasswordInput(attrs={'class': 'w-full rounded-2xl border border-slate-300 px-4 py-3'})
    )

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Οι δύο κωδικοί δεν ταιριάζουν.')

        if password1 and self.user:
            validate_password(password1, self.user)

        return cleaned_data


class AdminResetPasswordForm(forms.Form):
    new_temporary_password = forms.CharField(
        label='Νέος προσωρινός κωδικός',
        widget=forms.PasswordInput(attrs={'class': 'w-full rounded-2xl border border-slate-300 px-4 py-3'})
    )

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_temporary_password(self):
        password = self.cleaned_data['new_temporary_password']
        if self.user:
            validate_password(password, self.user)
        return password