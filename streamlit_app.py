"""
Shri Lalita Bill Generator - COMPLETE VERSION
Features: Dashboard, Payment Tracking, Phone Normalization, Duplicate Handling
"""

import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import json

# Page configuration
st.set_page_config(
    page_title="Shri Lalita Bill Generator",
    page_icon="🥛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Password protection
def check_password():
    """Returns `True` if the user has entered the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets.get("password", "lalita2025"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("### 🔐 Shri Lalita Bill Generator")
        st.markdown("#### Enter Password to Continue")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.info("💡 Default password: **lalita2025**")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("### 🔐 Shri Lalita Bill Generator")
        st.markdown("#### Enter Password to Continue")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

# Phone normalization function
def normalize_phone(phone):
    """Normalize phone number to 10 digits, removing country code"""
    if pd.isna(phone):
        return None
    
    # Convert to string and remove decimals
    phone_str = str(int(float(phone)))
    
    # Remove country code (91) if present
    if phone_str.startswith('91') and len(phone_str) == 12:
        phone_str = phone_str[2:]  # Remove first 2 digits (91)
    
    # Ensure it's 10 digits
    if len(phone_str) == 10:
        return phone_str
    
    return phone_str  # Return as is if not standard length

# Initialize session state
def init_session_state():
    if 'df_receipts' not in st.session_state:
        st.session_state.df_receipts = None
    if 'df_items' not in st.session_state:
        st.session_state.df_items = None
    if 'payment_tracker' not in st.session_state:
        st.session_state.payment_tracker = {}
    if 'logo_bytes' not in st.session_state:
        st.session_state.logo_bytes = None
    if 'customer_payment_data' not in st.session_state:
        st.session_state.customer_payment_data = None
    
    # Load saved data on startup
    load_saved_data()

# Save data persistently
def save_data():
    """Save current data to files for persistence"""
    try:
        if st.session_state.df_receipts is not None:
            st.session_state.df_receipts.to_pickle('saved_receipts.pkl')
        if st.session_state.df_items is not None:
            st.session_state.df_items.to_pickle('saved_items.pkl')
        if st.session_state.logo_bytes is not None:
            with open('saved_logo.bin', 'wb') as f:
                f.write(st.session_state.logo_bytes)
    except Exception as e:
        st.error(f"Failed to save data: {str(e)}")

# Load saved data
def load_saved_data():
    """Load previously saved data"""
    try:
        if os.path.exists('saved_receipts.pkl'):
            st.session_state.df_receipts = pd.read_pickle('saved_receipts.pkl')
        if os.path.exists('saved_items.pkl'):
            st.session_state.df_items = pd.read_pickle('saved_items.pkl')
        if os.path.exists('saved_logo.bin'):
            with open('saved_logo.bin', 'rb') as f:
                st.session_state.logo_bytes = f.read()
    except Exception as e:
        pass  # Silently fail if files don't exist

# Load payment tracker
def load_payment_tracker():
    try:
        if os.path.exists('payment_tracker.json'):
            with open('payment_tracker.json', 'r') as f:
                st.session_state.payment_tracker = json.load(f)
    except:
        st.session_state.payment_tracker = {}

# Save payment tracker
def save_payment_tracker():
    try:
        with open('payment_tracker.json', 'w') as f:
            json.dump(st.session_state.payment_tracker, f, indent=2)
    except Exception as e:
        st.error(f"Failed to save payment tracker: {str(e)}")

# Initialize customer payment data with duplicate handling
def initialize_customer_payment_data():
    """Create payment tracking dataframe from receipts with duplicate handling"""
    if st.session_state.df_receipts is None:
        return None
    
    # Create a copy and normalize phone numbers
    df = st.session_state.df_receipts.copy()
    df['NormalizedPhone'] = df['CustomerNumber'].apply(normalize_phone)
    
    # Remove duplicates - keep first occurrence of each phone number
    # Group by normalized phone and aggregate
    customer_summary = df.groupby('NormalizedPhone', dropna=True).agg({
        'CustomerName': 'first',  # Take first name
        'CustomerNumber': 'first',  # Keep original number
        'Total': 'sum'  # Sum all transactions
    }).reset_index()
    
    # Create payment data structure
    payment_data = []
    for _, row in customer_summary.iterrows():
        phone = row['NormalizedPhone']
        name = row['CustomerName']
        amount_due = row['Total']
        
        # Check if exists in tracker
        tracker_info = st.session_state.payment_tracker.get(phone, {})
        
        # Calculate remaining amount
        previous_balance = tracker_info.get('previous_balance', 0)
        advance_amount = tracker_info.get('advance_amount', 0)
        amount_paid = tracker_info.get('amount_paid', 0)
        
        remaining = amount_due + previous_balance - advance_amount - amount_paid
        
        payment_data.append({
            'Name': name,
            'Phone': phone,
            'Address': tracker_info.get('address', ''),
            'Amount Due': amount_due,
            'Previous Balance': previous_balance,
            'Advance Given?': 'Yes' if advance_amount > 0 else 'No',
            'Advance Amount': advance_amount,
            'Payment Status': tracker_info.get('payment_status', 'Due'),
            'Amount Paid': amount_paid,
            'Remaining Amount': remaining,
            'Payment Mode': tracker_info.get('payment_mode', ''),
            'Received On': tracker_info.get('received_on', ''),
            'Cash Collected': tracker_info.get('cash_collected', False),
            'Cash Deposited': tracker_info.get('cash_deposited', False),
            'Remarks': tracker_info.get('remarks', ''),
            'Advance CF': tracker_info.get('advance_cf', 0)
        })
    
    return pd.DataFrame(payment_data)

# Create dashboard metrics
def create_dashboard():
    """Create main dashboard with summary statistics"""
    
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
    
    # Display metrics in columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("💰 Total Amount", f"₹{total_amount:,.2f}")
        st.metric("✅ Received Amount", f"₹{received_amount:,.2f}", 
                 delta=f"{recovery_percent:.1f}% recovered", delta_color="normal")
        st.metric("⏳ Remaining Amount", f"₹{remaining_amount:,.2f}")
    
    with col2:
        st.metric("✔️ Paid", paid_count, delta=f"{(paid_count/total_customers*100):.1f}%", delta_color="off")
        st.metric("❌ Unpaid", unpaid_count, delta=f"{(unpaid_count/total_customers*100):.1f}%", delta_color="off")
        st.metric("💵 Advance", advance_count)
        st.metric("⚠️ Partial", partial_count)
        st.metric("📊 Total Customers", total_customers)
    
    with col3:
        st.metric("📱 UPI %", f"{upi_percent:.2f}%")
        st.metric("💵 Cash %", f"{cash_percent:.2f}%")
        st.metric("📱 Total UPI (Amount)", f"₹{upi_amount:,.2f}")
        st.metric("💵 Total Cash (Amount)", f"₹{cash_amount:,.2f}")
        st.metric("📱 UPI Count", upi_count)
        st.metric("💵 Cash Count", cash_count)
        st.metric("📈 Total Recovery %", f"{recovery_percent:.2f}%")
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💳 Payment Status Distribution")
        status_counts = df['Payment Status'].value_counts()
        st.bar_chart(status_counts)
    
    with col2:
        st.subheader("🔝 Top 10 Outstanding Customers")
        top_outstanding = df.nlargest(10, 'Remaining Amount')[['Name', 'Phone', 'Remaining Amount']]
        top_outstanding['Remaining Amount'] = top_outstanding['Remaining Amount'].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(top_outstanding, use_container_width=True, hide_index=True)

# Create payment tracking PDF
def create_payment_tracking_pdf():
    """Create PDF with all customer payment details"""
    
    if st.session_state.customer_payment_data is None:
        return None
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=15*mm, bottomMargin=15*mm)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'], fontSize=18,
        textColor=colors.HexColor('#1a5490'), spaceAfter=10,
        alignment=TA_CENTER, fontName='Helvetica-Bold'
    )
    
    # Title
    story.append(Paragraph("MONTHLY PAYMENT TRACKING REPORT", title_style))
    story.append(Paragraph(f"Shri Lalita - By Maharani Farm", styles['Normal']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    story.append(Spacer(1, 8*mm))
    
    # Summary section
    df = st.session_state.customer_payment_data.copy()
    
    total_amt = df['Amount Due'].sum()
    received_amt = df['Amount Paid'].sum()
    remaining_amt = df['Remaining Amount'].sum()
    
    summary_data = [
        ['SUMMARY', ''],
        ['Total Customers:', str(len(df))],
        ['Total Amount Due:', f"₹{total_amt:,.2f}"],
        ['Amount Received:', f"₹{received_amt:,.2f}"],
        ['Amount Remaining:', f"₹{remaining_amt:,.2f}"],
        ['Recovery %:', f"{(received_amt/total_amt*100 if total_amt > 0 else 0):.2f}%"],
    ]
    
    summary_table = Table(summary_data, colWidths=[80*mm, 80*mm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 8*mm))
    
    # Customer details table
    story.append(Paragraph("CUSTOMER PAYMENT DETAILS", styles['Heading2']))
    story.append(Spacer(1, 5*mm))
    
    table_data = [['#', 'Name', 'Phone', 'Due', 'Advance', 'Status', 'Paid', 'Remaining', 'Mode', 'Date']]
    
    for idx, row in df.iterrows():
        table_data.append([
            str(idx + 1),
            row['Name'][:18],  # Truncate long names
            row['Phone'],
            f"₹{row['Amount Due']:,.0f}",
            f"₹{row['Advance Amount']:,.0f}" if row['Advance Amount'] > 0 else '-',
            row['Payment Status'][:8],
            f"₹{row['Amount Paid']:,.0f}" if row['Amount Paid'] > 0 else '-',
            f"₹{row['Remaining Amount']:,.0f}",
            row['Payment Mode'][:6] if row['Payment Mode'] else '-',
            str(row['Received On'])[:10] if row['Received On'] else '-'
        ])
    
    # Create table
    table = Table(table_data, colWidths=[10*mm, 35*mm, 25*mm, 22*mm, 18*mm, 18*mm, 20*mm, 22*mm, 18*mm, 20*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 6),
        ('ALIGN', (3, 1), (7, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
    ]))
    
    story.append(table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# Create individual bill PDF
def create_bill_pdf(customer_name, phone, df_receipts, df_items, payment_info=None):
    """Create PDF bill and return bytes"""
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'], fontSize=20,
        textColor=colors.HexColor('#1a5490'), spaceAfter=6,
        alignment=TA_CENTER, fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle', parent=styles['Normal'], fontSize=12,
        textColor=colors.HexColor('#1a5490'), spaceAfter=20,
        alignment=TA_CENTER, fontName='Helvetica'
    )
    
    # Add logo if available
    if st.session_state.logo_bytes:
        try:
            logo_buffer = io.BytesIO(st.session_state.logo_bytes)
            logo = Image(logo_buffer, width=100*mm, height=100*mm)
            story.append(logo)
            story.append(Spacer(1, 10*mm))
        except:
            pass
    
    # Title
    story.append(Paragraph("MONTHLY CREDIT BILL", title_style))
    story.append(Paragraph("Shri Lalita - Pure and Natural Milk", subtitle_style))
    story.append(Spacer(1, 5*mm))
    
    # Customer info table
    date_range = f"{df_receipts['Date'].min()} to {df_receipts['Date'].max()}"
    
    customer_data = [
        ['Customer Information', ''],
        ['Name:', customer_name],
        ['Phone:', phone],
        ['Billing Period:', date_range],
    ]
    
    customer_table = Table(customer_data, colWidths=[120*mm, 60*mm])
    customer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(customer_table)
    story.append(Spacer(1, 8*mm))
    
    # Payment summary
    total_amount = df_receipts['Total'].sum()
    
    summary_data = [
        ['Payment Summary', ''],
        ['Total Transactions:', str(len(df_receipts))],
        ['Total Amount:', f'Rs. {total_amount:.2f}'],
    ]
    
    if payment_info:
        if payment_info.get('previous_balance', 0) != 0:
            summary_data.append(['Previous Balance:', f"Rs. {payment_info['previous_balance']:.2f}"])
        if payment_info.get('advance_amount', 0) != 0:
            summary_data.append(['Advance Paid:', f"Rs. {payment_info['advance_amount']:.2f}"])
        if payment_info.get('amount_paid', 0) != 0:
            summary_data.append(['Amount Paid:', f"Rs. {payment_info['amount_paid']:.2f}"])
        
        final_amount = total_amount + payment_info.get('previous_balance', 0) - payment_info.get('advance_amount', 0) - payment_info.get('amount_paid', 0)
        summary_data.append(['', ''])
        summary_data.append(['FINAL AMOUNT DUE:', f'Rs. {final_amount:.2f}'])
    
    summary_table = Table(summary_data, colWidths=[120*mm, 60*mm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#ffffcc')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#90EE90')),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 13),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(summary_table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# Main app
def main():
    if not check_password():
        return
    
    init_session_state()
    load_payment_tracker()
    
    # Header
    st.title("🥛 Shri Lalita - Monthly Bill Generator")
    st.markdown("**Complete Version - Dashboard, Payment Tracking & Bill Generation**")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("📁 Data Management")
        
        # Show data stats if loaded
        if st.session_state.df_receipts is not None:
            st.success("✅ Data Loaded")
            st.info(f"📊 {len(st.session_state.df_receipts)} transactions\n\n👥 {len(st.session_state.customer_payment_data)} unique customers")
        
        # Excel upload
        excel_file = st.file_uploader("Upload POS Data (Excel)", type=['xlsx', 'xls'], 
                                     help="Upload your monthly POS data")
        
        if excel_file:
            try:
                with st.spinner("Processing data..."):
                    # Read data
                    df_receipts_raw = pd.read_excel(excel_file, sheet_name='receipts')
                    df_items_raw = pd.read_excel(excel_file, sheet_name='receiptsWithItems')
                    
                    # Normalize phone numbers BEFORE filtering
                    df_receipts_raw['NormalizedPhone'] = df_receipts_raw['CustomerNumber'].apply(normalize_phone)
                    
                    # Filter for credit only
                    df_receipts_filtered = df_receipts_raw[
                        df_receipts_raw['PaymentMode'] == 'Credit'
                    ].copy()
                    
                    # Update CustomerNumber to normalized phone
                    df_receipts_filtered['CustomerNumber'] = df_receipts_filtered['NormalizedPhone']
                    
                    st.session_state.df_receipts = df_receipts_filtered
                    
                    # Filter items
                    receipt_ids = df_receipts_filtered['ReceiptId'].tolist()
                    st.session_state.df_items = df_items_raw[
                        df_items_raw['ReceiptId'].isin(receipt_ids)
                    ]
                    st.session_state.df_items = st.session_state.df_items[
                        st.session_state.df_items['EntryType'] == 'Item'
                    ]
                    
                    # Initialize payment data
                    st.session_state.customer_payment_data = initialize_customer_payment_data()
                    
                    # Save data
                    save_data()
                    
                    st.success(f"✅ Loaded {len(df_receipts_filtered)} credit transactions from {len(st.session_state.customer_payment_data)} customers")
                    st.rerun()
                    
            except Exception as e:
                st.error(f"❌ Error loading file: {str(e)}")
                st.info("Make sure your Excel has 'receipts' and 'receiptsWithItems' sheets")
        
        # Check if data exists from previous session
        elif st.session_state.df_receipts is not None:
            st.info("📂 Using saved data from previous session")
            if st.button("🔄 Clear Saved Data", help="Remove all saved data and start fresh"):
                st.session_state.df_receipts = None
                st.session_state.df_items = None
                st.session_state.customer_payment_data = None
                # Delete saved files
                for file in ['saved_receipts.pkl', 'saved_items.pkl', 'saved_logo.bin']:
                    if os.path.exists(file):
                        os.remove(file)
                st.success("✅ Data cleared!")
                st.rerun()
        
        st.markdown("---")
        
        # Logo upload
        logo_file = st.file_uploader("Upload Logo (Optional)", type=['png', 'jpg', 'jpeg'],
                                    help="Upload your company logo for bills")
        if logo_file:
            st.session_state.logo_bytes = logo_file.read()
            save_data()
            st.success("✅ Logo saved!")
        
        st.markdown("---")
        st.info("💡 **Data persists!** Upload once, use anytime. No re-upload after app sleep.")
    
    # Main content
    if st.session_state.df_receipts is None:
        st.info("👆 **Please upload your Excel file to begin**")
        
        st.markdown("---")
        st.markdown("""
        ## 🎯 Features:
        
        ### 📊 Dashboard
        - View summary statistics
        - Total amounts, received, remaining
        - Payment status breakdown
        - UPI vs Cash analysis
        - Recovery percentage
        
        ### 📋 Payment Tracking
        - **Full customer list** with all details
        - **Edit payment status** directly
        - Track advances, partial payments
        - Add payment dates and modes
        - Export to Excel or PDF
        
        ### 📄 Bill Generation
        - Individual customer bills
        - Professional PDF format
        - Auto-calculated final amounts
        - Download and share via WhatsApp
        
        ### 🔒 Security & Data
        - **Password protected**
        - **Data persists** - no re-upload needed
        - **Phone normalization** - handles duplicates
        - **10-digit phone numbers** - removes country code
        """)
        return
    
    # Initialize payment data if not done
    if st.session_state.customer_payment_data is None:
        st.session_state.customer_payment_data = initialize_customer_payment_data()
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📋 Full Customer List & Payments", "📄 Generate Bills", "ℹ️ Help"])
    
    with tab1:
        create_dashboard()
    
    with tab2:
        st.header("📋 Complete Payment Tracking")
        st.markdown("**View and edit all customer payment details**")
        
        df = st.session_state.customer_payment_data
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_status = st.multiselect(
                "Filter by Status",
                options=['All'] + df['Payment Status'].unique().tolist(),
                default=['All']
            )
        
        with col2:
            search_name = st.text_input("🔍 Search by Name", "")
        
        with col3:
            search_phone = st.text_input("🔍 Search by Phone", "")
        
        # Apply filters
        filtered_df = df.copy()
        
        if 'All' not in filter_status:
            filtered_df = filtered_df[filtered_df['Payment Status'].isin(filter_status)]
        
        if search_name:
            filtered_df = filtered_df[filtered_df['Name'].str.contains(search_name, case=False, na=False)]
        
        if search_phone:
            filtered_df = filtered_df[filtered_df['Phone'].str.contains(search_phone, na=False)]
        
        st.info(f"📊 Showing {len(filtered_df)} of {len(df)} customers")
        
        # Display editable dataframe
        edited_df = st.data_editor(
            filtered_df,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "Amount Due": st.column_config.NumberColumn(format="₹%.2f"),
                "Previous Balance": st.column_config.NumberColumn(format="₹%.2f"),
                "Advance Amount": st.column_config.NumberColumn(format="₹%.2f"),
                "Amount Paid": st.column_config.NumberColumn(format="₹%.2f"),
                "Remaining Amount": st.column_config.NumberColumn(format="₹%.2f"),
                "Advance CF": st.column_config.NumberColumn(format="₹%.2f"),
                "Payment Status": st.column_config.SelectboxColumn(
                    options=["Due", "Partial", "Settled", "Advance"]
                ),
                "Cash Collected": st.column_config.CheckboxColumn(),
                "Cash Deposited": st.column_config.CheckboxColumn(),
                "Phone": st.column_config.TextColumn(disabled=True),
            },
            hide_index=True
        )
        
        st.markdown("---")
        
        # Action buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("💾 Save All Changes", type="primary", use_container_width=True):
                # Update the main dataframe
                for idx, row in edited_df.iterrows():
                    phone = row['Phone']
                    
                    # Update payment tracker
                    st.session_state.payment_tracker[phone] = {
                        'customer_name': row['Name'],
                        'address': row['Address'],
                        'previous_balance': row['Previous Balance'],
                        'advance_amount': row['Advance Amount'],
                        'payment_status': row['Payment Status'],
                        'amount_paid': row['Amount Paid'],
                        'payment_mode': row['Payment Mode'],
                        'received_on': row['Received On'],
                        'cash_collected': row['Cash Collected'],
                        'cash_deposited': row['Cash Deposited'],
                        'remarks': row['Remarks'],
                        'advance_cf': row['Advance CF'],
                        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                
                # Update customer payment data
                st.session_state.customer_payment_data = edited_df
                
                save_payment_tracker()
                st.success("✅ All changes saved successfully!")
                st.balloons()
                st.rerun()
        
        with col2:
            # Export to Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                edited_df.to_excel(writer, sheet_name='Payment Tracking', index=False)
            
            st.download_button(
                "📥 Export to Excel",
                buffer.getvalue(),
                f"payment_tracking_{datetime.now().strftime('%Y%m%d')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col3:
            # Export to PDF
            if st.button("📄 Export to PDF", use_container_width=True):
                with st.spinner("Generating PDF..."):
                    pdf_bytes = create_payment_tracking_pdf()
                    if pdf_bytes:
                        st.download_button(
                            "⬇️ Download PDF",
                            pdf_bytes,
                            f"payment_tracking_{datetime.now().strftime('%Y%m%d')}.pdf",
                            "application/pdf",
                            use_container_width=True
                        )
        
        with col4:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.session_state.customer_payment_data = initialize_customer_payment_data()
                st.rerun()
    
    with tab3:
        st.header("📄 Generate Individual Customer Bills")
        
        # Get unique customers
        df = st.session_state.customer_payment_data
        
        # Create customer selection dropdown
        customer_options = {}
        for _, row in df.iterrows():
            display_text = f"{row['Name']} - {row['Phone']} (₹{row['Remaining Amount']:,.2f} due)"
            customer_options[display_text] = row['Phone']
        
        selected_display = st.selectbox(
            "Select Customer",
            options=list(customer_options.keys()),
            help="Shows: Name - Phone - Remaining Amount"
        )
        
        if selected_display:
            selected_phone = customer_options[selected_display]
            
            # Get customer data
            customer_receipts = st.session_state.df_receipts[
                st.session_state.df_receipts['CustomerNumber'] == selected_phone
            ]
            customer_items = st.session_state.df_items[
                st.session_state.df_items['ReceiptId'].isin(customer_receipts['ReceiptId'])
            ]
            
            customer_row = df[df['Phone'] == selected_phone].iloc[0]
            customer_name = customer_row['Name']
            
            # Display customer details
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Amount", f"₹{customer_row['Amount Due']:,.2f}")
            with col2:
                st.metric("Amount Paid", f"₹{customer_row['Amount Paid']:,.2f}")
            with col3:
                st.metric("Remaining", f"₹{customer_row['Remaining Amount']:,.2f}")
            
            # Payment info from tracker
            payment_info = st.session_state.payment_tracker.get(selected_phone, {})
            payment_info.update({
                'previous_balance': customer_row['Previous Balance'],
                'advance_amount': customer_row['Advance Amount'],
                'amount_paid': customer_row['Amount Paid']
            })
            
            st.markdown("---")
            
            # Generate bill
            if st.button("📥 Generate PDF Bill", type="primary", use_container_width=True):
                with st.spinner("Generating professional bill..."):
                    pdf_bytes = create_bill_pdf(
                        customer_name,
                        selected_phone,
                        customer_receipts,
                        customer_items,
                        payment_info
                    )
                    
                    safe_name = customer_name.replace(' ', '_').replace('/', '_')
                    filename = f"{safe_name}_Bill_{datetime.now().strftime('%Y%m')}.pdf"
                    
                    st.success("✅ Bill generated successfully!")
                    
                    st.download_button(
                        label="📄 Download Bill PDF",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary"
                    )
                    
                    st.info(f"💡 **Tip:** Share this PDF via WhatsApp with {customer_name}")
    
    with tab4:
        st.header("ℹ️ Help & Instructions")
        
        st.markdown("""
        ## 🎯 Key Features Explained
        
        ### 1. Phone Number Normalization
        - ✅ Automatically removes country code (91)
        - ✅ Converts all numbers to 10 digits
        - ✅ Handles duplicates intelligently
        - **Example:** 917234002022 → 7234002022
        
        ### 2. Duplicate Handling
        - System checks for same phone numbers
        - Combines transactions from duplicate entries
        - Uses first customer name found
        - Sums all amounts
        
        ### 3. Data Persistence
        - Upload data once per month
        - Data saved automatically
        - Survives app sleep/restart
        - Click "Clear Saved Data" for fresh start
        
        ### 4. Dashboard
        - Real-time summary statistics
        - Payment status breakdown
        - UPI vs Cash analysis
        - Top outstanding customers
        
        ### 5. Payment Tracking
        - **Full customer list** - see everyone at once
        - **Edit directly** - click any cell to edit
        - **Filter & search** - find customers quickly
        - **Save changes** - one click to save all
        - **Export** - Excel or PDF
        
        ### 6. Bill Generation
        - Select any customer
        - View their details
        - Generate professional PDF
        - Download and share
        
        ## 📝 Monthly Workflow
        
        **Start of Month:**
        1. Clear old data (if new month)
        2. Upload POS Excel file
        3. System normalizes phones & removes duplicates
        4. Review Dashboard
        
        **During Month:**
        1. Go to "Full Customer List & Payments"
        2. As payments come in, edit:
           - Payment Status
           - Amount Paid
           - Payment Mode
           - Received On date
        3. Click "Save All Changes"
        
        **End of Month:**
        1. Review Dashboard (recovery %)
        2. Generate bills for each customer
        3. Export Payment Tracking (Excel/PDF)
        4. Archive reports
        
        ## 💡 Pro Tips
        
        - 🔍 **Search:** Use search boxes to find customers quickly
        - 🎯 **Filter:** Filter by payment status to focus on pending
        - 💾 **Save Often:** Click save after updating multiple customers
        - 📥 **Export:** Export to Excel weekly for backup
        - 🔄 **Refresh:** Click refresh if data looks outdated
        
        ## ❓ FAQs
        
        **Q: Do I need to re-upload data every time?**  
        A: No! Data persists between sessions.
        
        **Q: What if I have duplicate phone numbers?**  
        A: System automatically combines them.
        
        **Q: What about phone numbers with 91?**  
        A: Automatically removed and normalized to 10 digits.
        
        **Q: Can I edit multiple customers at once?**  
        A: Yes! Edit as many as needed, then click "Save All Changes".
        
        **Q: What if I make a mistake?**  
        A: Just edit the cell again and save. Or click refresh to reload from saved data.
        
        ## 🔒 Security
        
        - Password protected
        - Data stored securely
        - Private deployment (if repo is private)
        - Can clear data anytime
        
        ## 📞 Need Help?
        
        Check these guides:
        - **QUICKSTART.md** - Initial deployment
        - **UPDATE_GUIDE.md** - Update existing app
        - **FINAL_SUMMARY.md** - Complete overview
        """)

if __name__ == "__main__":
    main()
