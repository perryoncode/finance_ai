from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from services.supabase_client import get_supabase

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.get("/login")
def login_page():
    return render_template("login.html")

@auth_bp.post("/login")
def login_post():
    email = request.form.get("email")
    password = request.form.get("password")
    if not email or not password:
        flash("Email and password required", "error")
        return redirect(url_for("auth.login_page"))

    sb = get_supabase()
    try:
        # Supabase-py v2:
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        session["user"] = {
            "id": res.user.id,
            "email": res.user.email,
        }
        # store access token to apply RLS on server-side queries
        session["access_token"] = res.session.access_token
        session["refresh_token"] = res.session.refresh_token
        return redirect(url_for("dashboard.dashboard_page"))
    except Exception as e:
        flash(f"Login failed: {e}", "error")
        return redirect(url_for("auth.login_page"))

@auth_bp.get("/register")
def register_page():
    return render_template("login.html", register=True)

@auth_bp.post("/register")
def register_post():
    email = request.form.get("email")
    password = request.form.get("password")
    sb = get_supabase()
    try:
        sb.auth.sign_up({"email": email, "password": password})
        flash("Check your email to confirm. Then log in.", "info")
        return redirect(url_for("auth.login_page"))
    except Exception as e:
        flash(f"Register failed: {e}", "error")
        return redirect(url_for("auth.register_page"))

@auth_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))
