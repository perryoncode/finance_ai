# dashboard.py
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
import os
import pandas as pd
from services.supabase_client import authed_postgrest, get_supabase
from services.finance_tools import normalize_csv, to_transactions,normalize_budget_csv,to_budgets
from config import settings
from postgrest.exceptions import APIError

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/")

def require_login():
    return "user" in session

def get_pg_client_or_redirect():
    """
    Returns PostgREST client with valid JWT.
    Refreshes token if expired. Redirects to login if refresh fails.
    """
    token = session.get("access_token")
    refresh_token = session.get("refresh_token")
    pg = authed_postgrest(token)

    try:
        # test if token valid
        pg.table("transactions").select("id").limit(1).execute()
        return pg
    except APIError as e:
        if "JWT expired" in str(e):
            if not refresh_token:
                flash("Session expired, please log in again", "error")
                return redirect(url_for("auth.login_page"))
            # refresh
            supabase = get_supabase()
            new_session = supabase.auth.refresh_session(refresh_token)
            session["access_token"] = new_session.access_token
            session["refresh_token"] = new_session.refresh_token
            pg = authed_postgrest(new_session.access_token)
            return pg
        else:
            raise e

@dashboard_bp.get("/")
def dashboard_page():
    if not require_login():
        return redirect(url_for("auth.login_page"))

    pg = get_pg_client_or_redirect()
    if not isinstance(pg, type(authed_postgrest(None))):
        # redirect happened due to expired session
        return pg

    # recent transactions
    tx = (
        pg.table("transactions")
        .select("id,date,amount,type,description,categories(name)")
        .order("date.desc")
        .limit(20)
        .execute()
    )
    txs = tx.data or []

    income = sum(float(t["amount"]) for t in txs if t["type"] == "income")
    expense = sum(float(t["amount"]) for t in txs if t["type"] == "expense")

    # the budget
    bj = (
        pg.table("budgets")
        .select("id,month,amount,categories(name)")
        .order("categories(name).asc")
        .limit(20)
        .execute()

    )

    bjs = bj.data or []

    return render_template("dashboard.html",
                           user=session["user"],
                           txs=txs, bjs=bjs, income=income, expense=expense)

@dashboard_bp.post("/upload")
def upload_csv():
    if not require_login():
        return redirect(url_for("auth.login_page"))

    file = request.files.get("file")
    if not file:
        flash("No file uploaded", "error")
        return redirect(url_for("dashboard.dashboard_page"))

    os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
    path = os.path.join(settings.UPLOAD_FOLDER, file.filename)
    file.save(path)

    df = pd.read_csv(path)
    df = normalize_csv(df)
    rows = to_transactions(df, session["user"]["id"])

    if not rows:
        flash("No valid rows found", "error")
        return redirect(url_for("dashboard.dashboard_page"))

    pg = get_pg_client_or_redirect()
    if not isinstance(pg, type(authed_postgrest(None))):
        return pg  

    for r in rows:
        cat = r.pop("category_name", None)
        cat_id = None
        if cat:
            existing = (
                pg.table("categories")
                .select("id")
                .eq("name", cat)
                .limit(1)
                .execute()
            ).data
            if existing:
                cat_id = existing[0]["id"]
            else:
                created = (
                    pg.table("categories")
                    .insert({"user_id": session["user"]["id"], "name": cat, "type": r["type"]},returning="representation")
                    .execute()
                ).data
                cat_id = created[0]["id"] if created else None
        r["category_id"] = cat_id

    # insert transactions
    _ = pg.table("transactions").insert(rows).execute()
    flash(f"Imported {len(rows)} transactions", "success")
    return redirect(url_for("dashboard.dashboard_page"))

@dashboard_bp.post("/upload_budget")
def upload_budget_csv():
    if not require_login():
        return redirect(url_for("auth.login_page"))

    file = request.files.get("file")
    if not file:
        flash("No file uploaded", "error")
        return redirect(url_for("dashboard.dashboard_page"))

    # Save file
    os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
    path = os.path.join(settings.UPLOAD_FOLDER, file.filename)
    file.save(path)

    # Load CSV
    try:
        df = pd.read_csv(path)
    except:
        flash("Invalid CSV", "error")
        return redirect(url_for("dashboard.dashboard_page"))

    # ---- Normalization (matching your style) ----
    df = normalize_budget_csv(df)
    rows = to_budgets(df, session["user"]["id"])

    if not rows:
        flash("No valid budget rows", "error")
        return redirect(url_for("dashboard.dashboard_page"))

    # ---- DB Insert (same flow as transactions) ----
    pg = get_pg_client_or_redirect()
    if not isinstance(pg, type(authed_postgrest(None))):
        return pg  # session expired

    # Resolve categories
    for r in rows:
        cat = r.pop("category_name")

        existing = (
            pg.table("categories")
            .select("id")
            .eq("name", cat)
            .eq("user_id", session["user"]["id"])
            .limit(1)
            .execute()
        ).data

        if existing:
            cat_id = existing[0]["id"]
        else:
            created = (
                pg.table("categories")
                .insert({
                    "user_id": session["user"]["id"],
                    "name": cat,
                    "type": "expense",   # all budgets = expenses
                }, returning="representation")
                .execute()
            ).data
            cat_id = created[0]["id"]

        r["category_id"] = cat_id

    # Insert budgets
    pg.table("budgets").insert(rows).execute()

    flash(f"Imported {len(rows)} budget entries", "success")
    return redirect(url_for("dashboard.dashboard_page"))
