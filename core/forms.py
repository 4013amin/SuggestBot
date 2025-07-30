# core/forms.py

from django import forms
from .models import Product, ABTest


class OTPRequestForm(forms.Form):
    phone_number = forms.CharField(max_length=11, label="شماره موبایل")


class OTPVerifyForm(forms.Form):
    code = forms.CharField(max_length=6, label="کد تایید")


class ABTestForm(forms.ModelForm):
    class Meta:
        model = ABTest
        fields = ['product', 'name', 'variable', 'variant_value']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'variable': forms.Select(attrs={'class': 'form-control'}),
            'variant_value': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'product': 'محصول مورد نظر',
            'name': 'نام تست',
            'variable': 'متغیر مورد تست',
            'variant_value': 'مقدار جدید برای تست',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['product'].queryset = Product.objects.filter(owner=user)

    def save(self, commit=True):
        instance = super().save(commit=False)
        product = self.cleaned_data['product']
        variable = self.cleaned_data['variable']

        if variable == 'PRICE':
            instance.control_value = product.price
        elif variable == 'NAME':
            instance.control_value = product.name

        if commit:
            instance.save()
        return instance