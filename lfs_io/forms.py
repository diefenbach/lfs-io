from django import forms


class ImportForm(forms.Form):
    my_file = forms.FileField()
