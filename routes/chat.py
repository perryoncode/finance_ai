# chat.py
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from datetime import date, timedelta
from services.supabase_client import authed_postgrest, get_supabase
from services.gemini_client import ask_gemini
from postgrest.exceptions import APIError

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")

def get_pg_client_or_redirect():
    token = session.get("access_token")
    refresh_token = session.get("refresh_token")
    pg = authed_postgrest(token)
    try:
        pg.table("transactions").select("id").limit(1).execute()
        return pg
    except APIError as e:
        if "JWT expired" in str(e):
            if not refresh_token:
                return None
            supabase = get_supabase()
            new_session = supabase.auth.refresh_session(refresh_token)
            session["access_token"] = new_session.access_token
            session["refresh_token"] = new_session.refresh_token
            pg = authed_postgrest(new_session.access_token)
            return pg
        else:
            raise e

@chat_bp.get("/")
def chat_page():
    # Require login to access chat UI
    if "user" not in session:
        return redirect(url_for("auth.login_page"))
    return render_template("chat.html")

@chat_bp.post("/ask")
def ask():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(force=True) or {}
    user_msg = payload.get("message", "").strip()
    days = int(payload.get("days", 30))

    since = (date.today() - timedelta(days=days)).isoformat()
    pg = get_pg_client_or_redirect()
    if pg is None:
        return jsonify({"error": "Session expired"}), 401

    # Check if user has any transactions first
    tx_count = (pg.table("transactions")
                .select("id", count="exact")
                .execute())
    
    has_transactions = tx_count.count > 0 if hasattr(tx_count, 'count') else False
    
    # Get transactions for the specified time period
    tx = (pg.table("transactions")
            .select("date,amount,type,description,categories(name)")
            .gte("date", since)
            .order("date.desc")
            .limit(500)
            .execute()).data or []

    # Get budgets
    budgets = (pg.table("budgets")
                 .select("month,amount,category_id,categories(name)")
                 .order("month.desc")
                 .limit(100)
                 .execute()).data or []

    # Prepare context information
    timeframe_text = f"the last {days} days" if days <= 90 else f"the last {days//30} months"
    
    # Check if we have data in the selected timeframe
    has_data_in_timeframe = len(tx) > 0
    total_transaction_count = tx_count.count if hasattr(tx_count, 'count') else 0
    
    prompt = f"""
You are a helpful and strict personal finance coach. Using the provided JSON data, answer the user's question and provide practical advice.
Return a clear and concise response. Use Indian Rupee (INR) as default money.

CONTEXT:
- User is asking about their financial data for {timeframe_text}
- Total transactions in database: {total_transaction_count}
- Transactions in selected timeframe: {len(tx)}
- Budgets available: {len(budgets)}

USER QUESTION:
{user_msg}

TRANSACTIONS DATA:
{tx}

BUDGETS DATA:
{budgets}

IMPORTANT RESPONSE GUIDELINES:
1. If there are no transactions at all, inform the user they need to upload transaction data first and explain how to do that from the dashboard page.
2. If there are transactions in the database but none in the selected timeframe, suggest they try a longer timeframe.
3. If there are transactions in the selected timeframe, provide specific insights based on the real data.
4. Use specific numbers and dates from the data when giving advice.
5. Be professional in tone.
6. Keep the answer straight forward.
"""
    try:
        reply = ask_gemini(prompt, json_mode=False)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
