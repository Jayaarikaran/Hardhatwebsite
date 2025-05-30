from django.contrib.auth.signals import user_logged_in, user_logged_out, password_changed
from django.contrib.sessions.models import Session
from django.dispatch import receiver
from django.utils.timezone import now



@receiver(user_logged_in)
def set_session_last_activity_on_login(sender, request, user, **kwargs):
    """
    Set the initial 'last_activity' in session on user login.
    """
    request.session['last_activity'] = now().timestamp()

    # Force session save if no session key available
    if not request.session.session_key:
        request.session.save()

    current_session_key = request.session.session_key
    print(f"[Login] Current session key: {current_session_key}")

    # Prevent concurrent logins
    if hasattr(user, 'current_session_key') and user.current_session_key and user.current_session_key != current_session_key:
        try:
            old_session = Session.objects.get(session_key=user.current_session_key)
            old_session.delete()
            print(f"[Login] Deleted old session: {user.current_session_key}")
        except Session.DoesNotExist:
            print("[Login] Old session not found.")

    # Save new session key to user model
    user.current_session_key = current_session_key
    user.save()
 
@receiver(user_logged_out)
def clear_session_last_activity_on_logout(sender, request, user, **kwargs):
    """
    Clear the 'last_activity' session key on user logout.
    """
    if 'last_activity' in request.session:
        del request.session['last_activity']

    # Clear session tracking on logout
    if hasattr(user, 'current_session_key') and user.current_session_key == request.session.session_key:
        user.current_session_key = None
        user.save()

@receiver(password_changed)
def clear_user_sessions_on_password_change(sender, request, user, **kwargs):
    """
    Clear all sessions for a user when their password is changed/reset
    Keeps only the current session active
    """
    if not user:
        return

    # Get all sessions for user
    Session.objects.filter(
        expire_date__gte=now()
    ).exclude(
        session_key=request.session.session_key  # Exclude current session
    ).filter(
        get_decoded().get('_auth_user_id') == str(user.id)
    ).delete()

    # Update current session key
    user.current_session_key = request.session.session_key
    user.save(update_fields=['current_session_key'])

