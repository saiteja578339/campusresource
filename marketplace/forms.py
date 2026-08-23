from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Listing, Message, Review


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=40)
    last_name = forms.CharField(max_length=40, required=False)
    email = forms.EmailField(help_text="Use your college email when available.")
    course = forms.CharField(max_length=80, initial="Information Technology")
    year = forms.CharField(max_length=20, initial="4th Year")

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "course",
            "year",
            "password1",
            "password2",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account already uses this email address.")
        return email

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.profile.course = self.cleaned_data["course"]
            user.profile.year = self.cleaned_data["year"]
            user.profile.email_verified = user.email.endswith(
                (".edu", ".edu.in", "@mvsrec.edu.in")
            )
            user.profile.save()
        return user


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = (
            "title",
            "description",
            "category",
            "condition",
            "transaction_type",
            "price",
            "location",
            "course_tags",
            "image",
            "image_url",
            "demand_score",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "course_tags": forms.TextInput(
                attrs={"placeholder": "Example: IT, CSE, Data Structures"}
            ),
            "image_url": forms.URLInput(
                attrs={"placeholder": "Optional image URL if you do not upload a file"}
            ),
            "demand_score": forms.NumberInput(attrs={"min": 0, "max": 100}),
        }

    def clean(self):
        data = super().clean()
        transaction_type = data.get("transaction_type")
        price = data.get("price")
        if transaction_type in {"borrow", "donate"} and price:
            data["price"] = 0
        return data


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("body",)
        widgets = {
            "body": forms.Textarea(
                attrs={"rows": 2, "placeholder": "Ask about availability or pickup..."}
            )
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "body")
        widgets = {
            "rating": forms.Select(choices=[(n, f"{n} star{'s' if n != 1 else ''}") for n in range(5, 0, -1)]),
            "body": forms.Textarea(attrs={"rows": 3, "placeholder": "Describe your experience"}),
        }
