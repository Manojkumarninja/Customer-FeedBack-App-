import os
import streamlit as st
import pandas as pd
import mysql.connector
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv()  # loads .env for local dev; no-op on Streamlit Cloud

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Customer Feedback", page_icon="📋", layout="wide")

# ── DB config — st.secrets (Streamlit Cloud) with .env fallback ───────────────
def _secret(key: str) -> str:
    try:
        return st.secrets["database"][key]
    except Exception:
        return os.getenv(key, "")

DB_CONFIG = {
    "host":     _secret("DB_HOST"),
    "port":     int(_secret("DB_PORT") or 3306),
    "user":     _secret("DB_USER"),
    "password": _secret("DB_PASSWORD"),
    "database": _secret("DB_NAME"),
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def ensure_table():
    """Create table if it doesn't exist."""
    ddl = """
    CREATE TABLE IF NOT EXISTS FnV_Customer_Feedback (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        CustomerId      BIGINT,
        VisitDate       DATE,
        CustomerNature          VARCHAR(50),
        Ninjacart_Issue_Category VARCHAR(50),
        Shop_Potential          VARCHAR(50),
        OrderPlaced             VARCHAR(10),
        Customer_Reorder_Intent VARCHAR(10),
        NotOrder_Reason         VARCHAR(50),
        ReMark                  TEXT,
        CreatedBy       VARCHAR(100),
        CreatedAt       DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy       VARCHAR(100),
        UpdatedAt       DATETIME ON UPDATE CURRENT_TIMESTAMP
    )
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(ddl)
    conn.commit()
    cur.close()
    conn.close()


def insert_feedback(record: dict):
    sql = """
    INSERT INTO FnV_Customer_Feedback
        (CustomerId, VisitDate, CustomerNature, Ninjacart_Issue_Category,
         Shop_Potential, OrderPlaced, Customer_Reorder_Intent,
         NotOrder_Reason, ReMark, CreatedBy, CreatedAt, UpdatedBy, UpdatedAt)
    VALUES
        (%(CustomerId)s, %(VisitDate)s, %(CustomerNature)s,
         %(Ninjacart_Issue_Category)s, %(Shop_Potential)s,
         %(OrderPlaced)s, %(Customer_Reorder_Intent)s,
         %(NotOrder_Reason)s, %(ReMark)s,
         %(CreatedBy)s, %(CreatedAt)s, %(UpdatedBy)s, %(UpdatedAt)s)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, record)
    conn.commit()
    cur.close()
    conn.close()


def fetch_feedback(start: date, end: date) -> pd.DataFrame:
    sql = """
    SELECT CustomerId, VisitDate, CustomerNature, Ninjacart_Issue_Category,
           Shop_Potential, OrderPlaced, Customer_Reorder_Intent,
           NotOrder_Reason, ReMark,
           CreatedBy, CreatedAt, UpdatedBy, UpdatedAt
    FROM FnV_Customer_Feedback
    WHERE VisitDate BETWEEN %s AND %s
    ORDER BY VisitDate DESC, CreatedAt DESC
    """
    conn = get_connection()
    df = pd.read_sql(sql, conn, params=(start, end))
    conn.close()
    return df


# ── Login ─────────────────────────────────────────────────────────────────────
USERS = {
    "rohitdinakar@ninjacart.com": "123456",
    "admin@ninjacart.com": "admin@123",
}


def login_page():
    st.markdown(
        """
        <style>
        .login-box {
            max-width: 380px;
            margin: 80px auto;
            padding: 2rem 2.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.12);
            background: #ffffff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 📋 Customer Feedback App")
        st.markdown("---")
        email = st.text_input("Email ID", placeholder="Enter your email")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        if st.button("Login", use_container_width=True, type="primary"):
            if email.strip().lower() in USERS and USERS[email.strip().lower()] == password:
                st.session_state["logged_in"] = True
                st.session_state["username"] = email.strip().lower()
                st.rerun()
            else:
                st.error("Invalid email or password.")


# ── Main App ──────────────────────────────────────────────────────────────────
def main_app():
    st.sidebar.markdown(f"### Welcome, {st.session_state['username'].capitalize()} 👋")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.sidebar.markdown("---")
    tab = st.sidebar.radio("Navigation", ["➕ Add Feedback", "📊 View Records"], label_visibility="collapsed")

    # ── ADD FEEDBACK ──────────────────────────────────────────────────────────
    if tab == "➕ Add Feedback":
        st.title("📋 Customer Feedback Form")
        st.markdown("Fill in the details below and click **Submit**.")

        with st.form("feedback_form", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                customer_id_raw = st.text_input(
                    "Customer ID *",
                    placeholder="Enter numeric Customer ID",
                )
                visit_date = st.date_input("Visit Date *", value=date.today())
                customer_nature = st.selectbox(
                    "Customer Nature *",
                    ["Pg", "Horeca", "PushCart", "General Trade","Others"],
                )
                ninjacart_issue = st.selectbox(
                    "Ninjacart Issue Category *",
                    ["Price", "Quality", "Dp Issue", "Delivery","Others","No Issue"],
                )
                shop_potential = st.selectbox(
                    "Shop Potential *",
                    ["less than 50", "50 to 100", "100 to 200", "more than 200"],
                )

            with col2:
                order_placed = st.selectbox("Order Placed *", ["yes", "no"])
                reorder_intent = st.selectbox(
                    "Customer Reorder Intent *", ["yes", "no"]
                )
                not_order_reason = st.selectbox(
                    "Not Order Reason",
                    ["","Price", "Quality", "Dp Issue", "Delivery","Others"],
                )
                remark = st.text_area("Remark", placeholder="Any additional remarks...", height=120)

            submitted = st.form_submit_button("Submit Feedback", type="primary", use_container_width=True)

        if submitted:
            # Validation
            errors = []
            if not customer_id_raw.strip():
                errors.append("Customer ID is required.")
            elif not customer_id_raw.strip().isdigit():
                errors.append("Customer ID must be numeric.")
            if not customer_nature:
                errors.append("Customer Nature is required.")
            if not ninjacart_issue:
                errors.append("Ninjacart Issue Category is required.")
            if not shop_potential:
                errors.append("Shop Potential is required.")
            if not order_placed:
                errors.append("Order Placed is required.")
            if not reorder_intent:
                errors.append("Customer Reorder Intent is required.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                now = datetime.now()
                logged_user = st.session_state["username"]
                record = {
                    "CustomerId": int(customer_id_raw.strip()),
                    "VisitDate": visit_date,
                    "CustomerNature": customer_nature,
                    "Ninjacart_Issue_Category": ninjacart_issue,
                    "Shop_Potential": shop_potential,
                    "OrderPlaced": order_placed,
                    "Customer_Reorder_Intent": reorder_intent,
                    "NotOrder_Reason": not_order_reason if not_order_reason else None,
                    "ReMark": remark.strip() if remark.strip() else None,
                    "CreatedBy": logged_user,
                    "CreatedAt": now,
                    "UpdatedBy": logged_user,
                    "UpdatedAt": now,
                }
                try:
                    insert_feedback(record)
                    st.success("Feedback submitted successfully!")
                except Exception as ex:
                    st.error(f"Database error: {ex}")

    # ── VIEW RECORDS ──────────────────────────────────────────────────────────
    else:
        st.title("📊 Feedback Records")

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            start_date = st.date_input("From Date", value=date(date.today().year, date.today().month, 1))
        with col2:
            end_date = st.date_input("To Date", value=date.today())
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            fetch_btn = st.button("🔍 Load Records", type="primary", use_container_width=True)

        if fetch_btn or "view_df" in st.session_state:
            if fetch_btn:
                if start_date > end_date:
                    st.error("'From Date' cannot be after 'To Date'.")
                else:
                    try:
                        df = fetch_feedback(start_date, end_date)
                        st.session_state["view_df"] = df
                        st.session_state["view_range"] = (start_date, end_date)
                    except Exception as ex:
                        st.error(f"Database error: {ex}")

            if "view_df" in st.session_state:
                df = st.session_state["view_df"]
                s, e = st.session_state["view_range"]
                st.markdown(f"Showing **{len(df)}** record(s) from **{s}** to **{e}**")
                if df.empty:
                    st.info("No records found for the selected date range.")
                else:
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    # Download
                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "⬇ Download CSV",
                        data=csv,
                        file_name=f"feedback_{s}_{e}.csv",
                        mime="text/csv",
                    )


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login_page()
    else:
        try:
            ensure_table()
        except Exception as ex:
            st.error(f"Could not connect to database: {ex}")
            st.stop()
        main_app()


if __name__ == "__main__":
    main()
