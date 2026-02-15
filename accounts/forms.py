from django import forms

from core.models import Project


MAIN_CATEGORY_CHOICES = [
  (Project.Category.CYBER, "Cybertech"),
  (Project.Category.FINANCE, "Finance"),
  (Project.Category.LIFESTYLE, "Lifestyle"),
  (Project.Category.BIOMED, "Biomedical Sciences"),
  (Project.Category.SUSTAINABILITY, "Sustainability"),
  (Project.Category.QUANTUM, "Quantum"),
]


SIDE_TRACK_LABELS = {
  "social_impact": "Vishnu Murthy Social Impact",
  "coder": "Coder",
}


class ProjectCategoryForm(forms.Form):
  team_name = forms.CharField(max_length=255, label="Team name")
  main_category = forms.ChoiceField(choices=MAIN_CATEGORY_CHOICES, label="Main category")
  side_beginner = forms.BooleanField(required=False, label="Beginner")
  side_social_impact = forms.BooleanField(required=False, label=SIDE_TRACK_LABELS["social_impact"])
  side_mobile_web = forms.ChoiceField(
    choices=(
      ("mobile", "Mobile"),
      ("web", "Web"),
    ),
    widget=forms.RadioSelect,
    label="Mobile or Web",
  )
  side_ai_ml = forms.BooleanField(required=False, label="AI/ML")
  side_roam = forms.BooleanField(required=False, label="Roam")
  side_coder = forms.BooleanField(required=False, label=SIDE_TRACK_LABELS["coder"])


class ProjectSubmissionForm(forms.ModelForm):
  class Meta:
    model = Project
    fields = [
      "preliminary_title",
      "title",
      "inspiration",
      "description",
      "ai_usage",
      "build_summary",
      "challenges",
      "accomplishments",
      "repo_url",
      "notes",
    ]
    labels = {
      "description": "What does it do?",
      "ai_usage": "Detailed generative AI usage explanation",
      "build_summary": "How did you build it?",
    }
    widgets = {
      field: forms.Textarea(attrs={"rows": 4})
      for field in [
        "inspiration",
        "description",
        "ai_usage",
        "build_summary",
        "challenges",
        "accomplishments",
        "notes",
      ]
    }
