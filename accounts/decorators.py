from functools import wraps
from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


def role_required(*roles):
  def decorator(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
      user = request.user

      if not user.is_authenticated:
        return redirect(settings.LOGIN_URL)

      if roles and user.role not in roles:
        return HttpResponseForbidden("You do not have access to this page.")

      return view_func(request, *args, **kwargs)
    return _wrapped
  return decorator


def admin_required(view_func):
  return role_required("admin")(view_func)


def judge_required(view_func):
  return role_required("judge")(view_func)


def team_required(view_func):
  return role_required("team")(view_func)


def volunteer_required(view_func):
  return role_required("volunteer")(view_func)


def hacktj_required(view_func):
  return role_required("hacktj")(view_func)
