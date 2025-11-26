import pandas as pd
from datetime import datetime
from dateutil.parser import parse as parse_date

REQUIRED_COLUMNS = ["date", "amount", "type"]  # category, description optional

def normalize_csv(df: pd.DataFrame) -> pd.DataFrame:
    # unify column names
    df.columns = [c.strip().lower() for c in df.columns]
    # rename common variants
    aliases = {
        "txn_date": "date",
        "posted_date": "date",
        "credit": "amount",
        "debit": "amount",
    }
    df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})

    # ensure required cols exist
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # parse date
    def safe_date(x):
        try:
            return parse_date(str(x)).date().isoformat()
        except Exception:
            return None

    df["date"] = df["date"].apply(safe_date)

    # amount numeric
    def to_amount(row):
        amt = row.get("amount")
        # If separate credit/debit existed earlier, you can custom-handle here
        try:
            return float(str(amt).replace(",", "").replace("₹", "").strip())
        except Exception:
            return None

    df["amount"] = df.apply(to_amount, axis=1)

    # type -> income/expense
    def norm_type(x):
        s = str(x).lower()
        if s in ["income", "credit", "cr", "in"]:
            return "income"
        return "expense"

    df["type"] = df["type"].apply(norm_type)
    return df

def to_transactions(df: pd.DataFrame, user_id: str):
    rows = []
    for _, r in df.iterrows():
        if not r["date"] or r["amount"] is None or r["type"] not in ("income", "expense"):
            continue
        rows.append({
            "user_id": user_id,
            "date": r["date"],
            "amount": r["amount"],
            "type": r["type"],
            "description": (r.get("description") or r.get("narration") or None),
            "category_name": r.get("category") or None,
        })
    return rows

def normalize_budget_csv(df: pd.DataFrame) -> pd.DataFrame:
    # unify column names
    df.columns = [c.strip().lower() for c in df.columns]

    # rename if needed
    aliases = {
        "budget": "amount",
        "limit": "amount",
        "category_name": "category",
    }
    df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})

    # Ensure columns
    required = ["category", "amount", "month"]
    for col in required:
        if col not in df.columns:
            df[col] = None

    # Clean category
    df["category"] = df["category"].astype(str).str.strip().str.title()

    # Amount numeric (same style as transactions)
    def to_amount(x):
        try:
            return float(str(x).replace(",", "").replace("₹", "").strip())
        except:
            return None

    df["amount"] = df["amount"].apply(to_amount)

    # Convert Month (YYYY-MM) → YYYY-MM-01 (date)
    def parse_month(value):
        try:
            # Input can be "2025-11" or "2025-11-01"
            s = str(value)
            parts = s.split("-")
            if len(parts) == 2:  # YYYY-MM
                return f"{parts[0]}-{parts[1]}-01"
            parsed = parse_date(s).date()
            return parsed.isoformat()
        except:
            return None

    df["month"] = df["month"].apply(parse_month)

    return df


def to_budgets(df: pd.DataFrame, user_id: str):
    rows = []
    for _, r in df.iterrows():
        if not r["category"] or r["amount"] is None or not r["month"]:
            continue

        rows.append({
            "user_id": user_id,
            "category_name": r["category"],
            "month": r["month"],       # date string (YYYY-MM-01)
            "amount": r["amount"],      # numeric
        })
    return rows
