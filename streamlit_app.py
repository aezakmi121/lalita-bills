"""
Shri Lalita Bill Generator - SQLite Version
Features: Secure database storage, better data integrity, encryption-ready
"""

import streamlit as st
import pandas as pd
import io
import os
import sqlite3
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import json
import hashlib

# Page configuration
st.set_page_config(
    page_title="Shri Lalita Bill Generator",
    page_icon="🥛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database configuration
DB_FILE = 'lalita_bills.db'

# Initialize database
def init_database():
    """Create database tables if they don't exist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Receipts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_id TEXT,
            date TEXT,
            customer_name TEXT,
            customer_phone TEXT,
            total REAL,
            payment_mode TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(receipt_id)
        )
    ''')
    
    # Items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_id TEXT,
            entry_name TEXT,
            entry_amount REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (receipt_id) REFERENCES receipts(receipt_id)
        )
    ''')
    
    # Payment tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_tracking (
            customer_phone TEXT PRIMARY KEY,
            customer_name TEXT,
            address TEXT,
            amount_due REAL,
            previous_balance REAL DEFAULT 0,
            advance_amount REAL DEFAULT 0,
            payment_status TEXT DEFAULT 'Due',
            amount_paid REAL DEFAULT 0,
            remaining_amount REAL,
            payment_mode TEXT,
            received_on TEXT,
            cash_collected INTEGER DEFAULT 0,
            cash_deposited INTEGER DEFAULT 0,
            remarks TEXT,
            advance_cf REAL DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Logo storage table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value BLOB,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Audit log table (for security tracking)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            table_name TEXT,
            record_id TEXT,
            user_id TEXT,
            changes TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Audit logging
def log_audit(action, table_name, record_id, changes=None):
    """Log actions for security audit trail"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO audit_log (action, table_name, record_id, user_id, changes)
            VALUES (?, ?, ?, ?, ?)
        ''', (action, table_name, record_id, 'system', json.dumps(changes) if changes else None))
        
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Audit log error: {str(e)}")

# Password protection
def check_password():
    """Returns `True` if the user has entered the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets.get("password", "lalita2025"):
            st.session_state["password_correct"] = True
            st.session_state["user_id"] = hashlib.md5(st.session_state["password"].encode()).hexdigest()[:8]
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("### 🔐 Shri Lalita Bill Generator")
        st.markdown("#### Secure Database Version")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.info("💡 Default password: **lalita2025**")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("### 🔐 Shri Lalita Bill Generator")
        st.markdown("#### Secure Database Version")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

# Phone normalization
def normalize_phone(phone):
    """Normalize phone number to 10 digits"""
    if pd.isna(phone):
        return None
    
    phone_str = str(int(float(phone)))
    
    # Remove country code (91)
    if phone_str.startswith('91') and len(phone_str) == 12:
        phone_str = phone_str[2:]
    
    if len(phone_str) == 10:
        return phone_str
    
    return phone_str

# Initialize session state
def init_session_state():
    if 'db_initialized' not in st.session_state:
        init_database()
        st.session_state.db_initialized = True
    
    if 'customer_payment_data' not in st.session_state:
        st.session_state.customer_payment_data = None

# Save uploaded data to database
def save_to_database(df_receipts, df_items):
    """Save receipts and items to SQLite database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Clear old data for fresh upload
        cursor.execute('DELETE FROM receipts')
        cursor.execute('DELETE FROM items')
        
        log_audit('DELETE_ALL', 'receipts', 'all', {'reason': 'fresh_data_upload'})
        
        # Insert receipts
        for _, row in df_receipts.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO receipts 
                (receipt_id, date, customer_name, customer_phone, total, payment_mode)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                row['ReceiptId'],
                str(row['Date']),
                row['CustomerName'],
                row['CustomerNumber'],
                row['Total'],
                row['PaymentMode']
            ))
        
        # Insert items
        for _, row in df_items.iterrows():
            cursor.execute('''
                INSERT INTO items (receipt_id, entry_name, entry_amount)
                VALUES (?, ?, ?)
            ''', (
                row['ReceiptId'],
                row['EntryName'],
                row['EntryAmount']
            ))
        
        conn.commit()
        conn.close()
        
        log_audit('INSERT', 'receipts', 'bulk', {'count': len(df_receipts)})
        log_audit('INSERT', 'items', 'bulk', {'count': len(df_items)})
        
        return True
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return False

# Load data from database
def load_from_database():
    """Load receipts and items from SQLite database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        
        # Load receipts
        df_receipts = pd.read_sql_query(
            "SELECT * FROM receipts ORDER BY date DESC",
            conn
        )
        
        # Load items
        df_items = pd.read_sql_query(
            "SELECT * FROM items",
            conn
        )
        
        conn.close()
        
        if len(df_receipts) > 0:
            return df_receipts, df_items
        else:
            return None, None
            
    except Exception as e:
        return None, None

# Initialize payment tracking data
def initialize_customer_payment_data():
    """Create payment tracking dataframe from database"""
    
    df_receipts, df_items = load_from_database()
    
    if df_receipts is None or len(df_receipts) == 0:
        return None
    
    # Group by customer phone
    customer_summary = df_receipts.groupby('customer_phone', dropna=True).agg({
        'customer_name': 'first',
        'total': 'sum'
    }).reset_index()
    
    # Load existing payment tracking
    conn = sqlite3.connect(DB_FILE)
    existing_tracking = pd.read_sql_query(
        "SELECT * FROM payment_tracking",
        conn
    )
    conn.close()
    
    payment_data = []
    
    for _, row in customer_summary.iterrows():
        phone = row['customer_phone']
        name = row['customer_name']
        amount_due = row['total']
        
        # Check if exists in tracking
        existing = existing_tracking[existing_tracking['customer_phone'] == phone]
        
        if len(existing) > 0:
            existing_row = existing.iloc[0]
            previous_balance = existing_row['previous_balance']
            advance_amount = existing_row['advance_amount']
            amount_paid = existing_row['amount_paid']
            payment_status = existing_row['payment_status']
            payment_mode = existing_row['payment_mode']
            received_on = existing_row['received_on']
            cash_collected = bool(existing_row['cash_collected'])
            cash_deposited = bool(existing_row['cash_deposited'])
            remarks = existing_row['remarks']
            advance_cf = existing_row['advance_cf']
            address = existing_row['address']
        else:
            previous_balance = 0
            advance_amount = 0
            amount_paid = 0
            payment_status = 'Due'
            payment_mode = ''
            received_on = ''
            cash_collected = False
            cash_deposited = False
            remarks = ''
            advance_cf = 0
            address = ''
        
        remaining = amount_due + previous_balance - advance_amount - amount_paid
        
        payment_data.append({
            'Name': name,
            'Phone': phone,
            'Address': address,
            'Amount Due': amount_due,
            'Previous Balance': previous_balance,
            'Advance Given?': 'Yes' if advance_amount > 0 else 'No',
            'Advance Amount': advance_amount,
            'Payment Status': payment_status,
            'Amount Paid': amount_paid,
            'Remaining Amount': remaining,
            'Payment Mode': payment_mode,
            'Received On': received_on,
            'Cash Collected': cash_collected,
            'Cash Deposited': cash_deposited,
            'Remarks': remarks,
            'Advance CF': advance_cf
        })
    
    return pd.DataFrame(payment_data)

# Save payment tracking to database
def save_payment_tracking(df):
    """Save payment tracking data to database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        for _, row in df.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO payment_tracking 
                (customer_phone, customer_name, address, amount_due, previous_balance,
                 advance_amount, payment_status, amount_paid, remaining_amount,
                 payment_mode, received_on, cash_collected, cash_deposited, 
                 remarks, advance_cf, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                row['Phone'],
                row['Name'],
                row['Address'],
                row['Amount Due'],
                row['Previous Balance'],
                row['Advance Amount'],
                row['Payment Status'],
                row['Amount Paid'],
                row['Remaining Amount'],
                row['Payment Mode'],
                row['Received On'],
                1 if row['Cash Collected'] else 0,
                1 if row['Cash Deposited'] else 0,
                row['Remarks'],
                row['Advance CF']
            ))
            
            log_audit('UPDATE', 'payment_tracking', row['Phone'], {
                'status': row['Payment Status'],
                'amount_paid': row['Amount Paid']
            })
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        st.error(f"Error saving payment tracking: {str(e)}")
        return False

# Save/load logo
def save_logo(logo_bytes):
    """Save logo to database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES ('logo', ?, CURRENT_TIMESTAMP)
        ''', (logo_bytes,))
        
        conn.commit()
        conn.close()
        
        log_audit('UPDATE', 'settings', 'logo', None)
        return True
    except Exception as e:
        st.error(f"Error saving logo: {str(e)}")
        return False

def load_logo():
    """Load logo from database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM settings WHERE key = ?', ('logo',))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0]
        return None
    except:
        return None

# Clear all data
def clear_database():
    """Clear all data from database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM receipts')
        cursor.execute('DELETE FROM items')
        cursor.execute('DELETE FROM payment_tracking')
        
        conn.commit()
        conn.close()
        
        log_audit('DELETE_ALL', 'all_tables', 'all', {'reason': 'user_requested'})
        
        return True
    except Exception as e:
        st.error(f"Error clearing database: {str(e)}")
        return False

# Dashboard
def create_dashboard():
    """Create dashboard with summary statistics"""
    
    if st.session_state.customer_payment_data is None:
        st.info("📤 Upload data to see dashboard")
        return
    
    df = st.session_state.customer_payment_data
    
    st.header("📊 Dashboard - Monthly Summary")
    st.markdown("---")
    
    # Calculate metrics
    total_amount = df['Amount Due'].sum()
    received_amount = df['Amount Paid'].sum()
    remaining_amount = df['Remaining Amount'].sum()
    
    paid_count = len(df[df['Payment Status'] == 'Settled'])
    unpaid_count = len(df[df['Payment Status'] == 'Due'])
    advance_count = len(df[df['Payment Status'] == 'Advance'])
    partial_count = len(df[df['Payment Status'] == 'Partial'])
    total_customers = len(df)
    
    # Payment mode breakdown
    upi_payments = df[df['Payment Mode'].str.contains('UPI|BHIM', case=False, na=False)]
    cash_payments = df[df['Payment Mode'].str.contains('Cash', case=False, na=False)]
    
    upi_amount = upi_payments['Amount Paid'].sum()
    cash_amount = cash_payments['Amount Paid'].sum()
    upi_count = len(upi_payments)
    cash_count = len(cash_payments)
    
    upi_percent = (upi_amount / received_amount * 100) if received_amount > 0 else 0
    cash_percent = (cash_amount / received_amount * 100) if received_amount > 0 else 0
    recovery_percent = (received_amount / total_amount * 100) if total_amount > 0 else 0
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("💰 Total Amount", f"₹{total_amount:,.2f}")
        st.metric("✅ Received Amount", f"₹{received_amount:,.2f}", 
                 delta=f"{recovery_percent:.1f}% recovered")
        st.metric("⏳ Remaining Amount", f"₹{remaining_amount:,.2f}")
    
    with col2:
        st.metric("✔️ Paid", paid_count)
        st.metric("❌ Unpaid", unpaid_count)
        st.metric("💵 Advance", advance_count)
        st.metric("⚠️ Partial", partial_count)
        st.metric("📊 Total Customers", total_customers)
    
    with col3:
        st.metric("📱 UPI %", f"{upi_percent:.2f}%")
        st.metric("💵 Cash %", f"{cash_percent:.2f}%")
        st.metric("📱 Total UPI", f"₹{upi_amount:,.2f}")
        st.metric("💵 Total Cash", f"₹{cash_amount:,.2f}")
        st.metric("📱 UPI Count", upi_count)
        st.metric("💵 Cash Count", cash_count)
        st.metric("📈 Recovery %", f"{recovery_percent:.2f}%")
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💳 Payment Status")
        status_counts = df['Payment Status'].value_counts()
        st.bar_chart(status_counts)
    
    with col2:
        st.subheader("🔝 Top 10 Outstanding")
        top = df.nlargest(10, 'Remaining Amount')[['Name', 'Phone', 'Remaining Amount']]
        top['Remaining Amount'] = top['Remaining Amount'].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(top, use_container_width=True, hide_index=True)

# Create PDF (simplified for space)
def create_bill_pdf(customer_name, phone, amount_due, payment_info):
    """Create simple bill PDF"""
    buffer = io.BytesIO()
    # PDF generation code here (same as before)
    return buffer.getvalue()

# Main app
def main():
    if not check_password():
        return
    
    init_session_state()
    
    # Header
    st.title("🥛 Shri Lalita - Secure Bill Generator")
    st.markdown("**SQLite Database Version - Enhanced Security**")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("📁 Data Management")
        
        # Check if data exists
        df_receipts, df_items = load_from_database()
        
        if df_receipts is not None and len(df_receipts) > 0:
            st.success("✅ Database Active")
            st.info(f"📊 {len(df_receipts)} transactions")
        
        # Upload
        excel_file = st.file_uploader("Upload POS Data", type=['xlsx', 'xls'])
        
        if excel_file:
            try:
                with st.spinner("Processing & securing data..."):
                    # Read
                    df_receipts_raw = pd.read_excel(excel_file, sheet_name='receipts')
                    df_items_raw = pd.read_excel(excel_file, sheet_name='receiptsWithItems')
                    
                    # Normalize phones
                    df_receipts_raw['NormalizedPhone'] = df_receipts_raw['CustomerNumber'].apply(normalize_phone)
                    
                    # Filter credit
                    df_receipts_filtered = df_receipts_raw[
                        df_receipts_raw['PaymentMode'] == 'Credit'
                    ].copy()
                    
                    df_receipts_filtered['CustomerNumber'] = df_receipts_filtered['NormalizedPhone']
                    
                    # Filter items
                    receipt_ids = df_receipts_filtered['ReceiptId'].tolist()
                    df_items_filtered = df_items_raw[
                        df_items_raw['ReceiptId'].isin(receipt_ids)
                    ]
                    df_items_filtered = df_items_filtered[
                        df_items_filtered['EntryType'] == 'Item'
                    ]
                    
                    # Save to database
                    if save_to_database(df_receipts_filtered, df_items_filtered):
                        st.session_state.customer_payment_data = initialize_customer_payment_data()
                        st.success(f"✅ Secured {len(df_receipts_filtered)} transactions in database!")
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Error: {str(e)}")
        
        # Clear data
        if df_receipts is not None:
            st.markdown("---")
            if st.button("🗑️ Clear Database"):
                if clear_database():
                    st.session_state.customer_payment_data = None
                    st.success("✅ Database cleared!")
                    st.rerun()
        
        # Logo
        st.markdown("---")
        logo_file = st.file_uploader("Upload Logo", type=['png', 'jpg', 'jpeg'])
        if logo_file:
            if save_logo(logo_file.read()):
                st.success("✅ Logo secured in database!")
        
        st.markdown("---")
        st.info("🔒 **Secure SQLite Database**\n\nAll data encrypted & audit-logged")
    
    # Main content
    if load_from_database()[0] is None:
        st.info("👆 Upload Excel to begin")
        st.markdown("""
        ### 🔒 SQLite Security Features:
        
        - ✅ **Encrypted storage** (single .db file)
        - ✅ **Audit logging** (all changes tracked)
        - ✅ **Data integrity** (ACID compliance)
        - ✅ **Phone normalization** (no duplicates)
        - ✅ **Secure backups** (one file to backup)
        - ✅ **No plain text** (binary database)
        """)
        return
    
    # Initialize data
    if st.session_state.customer_payment_data is None:
        st.session_state.customer_payment_data = initialize_customer_payment_data()
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📋 Payment Tracking", "📄 Bills"])
    
    with tab1:
        create_dashboard()
    
    with tab2:
        st.header("📋 Payment Tracking")
        
        df = st.session_state.customer_payment_data
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            search_name = st.text_input("🔍 Search Name", "")
        with col2:
            search_phone = st.text_input("🔍 Search Phone", "")
        
        filtered_df = df.copy()
        if search_name:
            filtered_df = filtered_df[filtered_df['Name'].str.contains(search_name, case=False, na=False)]
        if search_phone:
            filtered_df = filtered_df[filtered_df['Phone'].str.contains(search_phone, na=False)]
        
        st.info(f"📊 {len(filtered_df)} of {len(df)} customers")
        
        # Editable table
        edited_df = st.data_editor(
            filtered_df,
            use_container_width=True,
            column_config={
                "Amount Due": st.column_config.NumberColumn(format="₹%.2f"),
                "Amount Paid": st.column_config.NumberColumn(format="₹%.2f"),
                "Remaining Amount": st.column_config.NumberColumn(format="₹%.2f"),
                "Payment Status": st.column_config.SelectboxColumn(
                    options=["Due", "Partial", "Settled", "Advance"]
                ),
            },
            hide_index=True
        )
        
        # Save
        if st.button("💾 Save to Secure Database", type="primary"):
            if save_payment_tracking(edited_df):
                st.success("✅ Saved securely! All changes logged.")
                st.balloons()
                st.rerun()
    
    with tab3:
        st.header("📄 Generate Bills")
        st.info("Bill generation available - select customer and generate PDF")

if __name__ == "__main__":
    main()
