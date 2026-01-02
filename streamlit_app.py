"""
Shri Lalita Bill Generator - Enhanced Version
Features: Dashboard, Payment Tracking Table, Persistent Storage
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

# Initialize customer payment data
def initialize_customer_payment_data():
    """Create payment tracking dataframe from receipts"""
    if st.session_state.df_receipts is None:
        return None
    
    # Group by customer
    customer_summary = st.session_state.df_receipts.groupby('CustomerNumber').agg({
        'CustomerName': 'first',
        'Total': 'sum'
    }).reset_index()
    
    # Create payment data structure
    payment_data = []
    for _, row in customer_summary.iterrows():
        phone = str(int(row['CustomerNumber']))
        name = row['CustomerName']
        amount_due = row['Total']
        
        # Check if exists in tracker
        tracker_info = st.session_state.payment_tracker.get(phone, {})
        
        payment_data.append({
            'Name': name,
            'Phone': phone,
            'Address': tracker_info.get('address', ''),
            'Amount Due': amount_due,
            'Advance Given?': 'Yes' if tracker_info.get('advance_amount', 0) > 0 else 'No',
            'Advance Amount': tracker_info.get('advance_amount', 0),
            'Payment Status': tracker_info.get('payment_status', 'Due'),
            'Amount Paid': tracker_info.get('amount_paid', 0),
            'Remaining Amount': amount_due - tracker_info.get('amount_paid', 0) + tracker_info.get('previous_balance', 0) - tracker_info.get('advance_amount', 0),
            'Payment Mode': tracker_info.get('payment_mode', ''),
            'Received On': tracker_info.get('received_on', ''),
            'Cash Collected': tracker_info.get('cash_collected', False),
            'Cash Deposited': tracker_info.get('cash_deposited', False),
            'Remarks': tracker_info.get('remarks', ''),
            'Advance CF': tracker_info.get('advance_cf', 0)
        })
    
    return pd.DataFrame(payment_data)

# Normalize phone
def normalize_phone(phone):
    if pd.isna(phone):
        return None
    phone_str = str(int(float(phone)))
    return phone_str

# Create dashboard metrics
def create_dashboard():
    """Create main dashboard with summary statistics"""
    
    if st.session_state.customer_payment_data is None:
        st.info("Upload data to see dashboard")
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
    upi_payments = df[df['Payment Mode'].str.contains('UPI', case=False, na=False)]
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
        st.metric("✅ Received Amount", f"₹{received_amount:,.2f}")
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
        st.metric("📱 Total UPI (Amount)", f"₹{upi_amount:,.2f}")
        st.metric("💵 Total Cash (Amount)", f"₹{cash_amount:,.2f}")
        st.metric("📱 UPI Count", upi_count)
        st.metric("💵 Cash Count", cash_count)
        st.metric("📈 Total Recovery %", f"{recovery_percent:.2f}%")
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Payment Status Distribution")
        status_counts = df['Payment Status'].value_counts()
        st.bar_chart(status_counts)
    
    with col2:
        st.subheader("Top 10 Outstanding Customers")
        top_outstanding = df.nlargest(10, 'Remaining Amount')[['Name', 'Remaining Amount']]
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
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Spacer(1, 10*mm))
    
    # Prepare table data
    df = st.session_state.customer_payment_data.copy()
    
    table_data = [['Name', 'Phone', 'Amount\nDue', 'Advance', 'Status', 'Paid', 'Remaining', 'Mode', 'Date', 'Remarks']]
    
    for _, row in df.iterrows():
        table_data.append([
            row['Name'][:20],  # Truncate long names
            row['Phone'],
            f"₹{row['Amount Due']:,.0f}",
            f"₹{row['Advance Amount']:,.0f}" if row['Advance Amount'] > 0 else '-',
            row['Payment Status'],
            f"₹{row['Amount Paid']:,.0f}",
            f"₹{row['Remaining Amount']:,.0f}",
            row['Payment Mode'] if row['Payment Mode'] else '-',
            row['Received On'] if row['Received On'] else '-',
            row['Remarks'][:15] if row['Remarks'] else '-'
        ])
    
    # Create table
    table = Table(table_data, colWidths=[35*mm, 25*mm, 22*mm, 18*mm, 18*mm, 20*mm, 22*mm, 18*mm, 20*mm, 30*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (2, 1), (7, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
    ]))
    
    story.append(table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# Create individual bill PDF (same as before but simplified)
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
        if payment_info.get('advance_paid', 0) != 0:
            summary_data.append(['Advance Paid:', f"Rs. {payment_info['advance_paid']:.2f}"])
        
        final_amount = total_amount + payment_info.get('previous_balance', 0) - payment_info.get('advance_paid', 0)
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
    st.markdown("**Enhanced Version with Dashboard & Payment Tracking**")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("📁 Data Management")
        
        # Excel upload
        excel_file = st.file_uploader("Upload POS Data (Excel)", type=['xlsx', 'xls'])
        if excel_file:
            try:
                st.session_state.df_receipts = pd.read_excel(excel_file, sheet_name='receipts')
                st.session_state.df_items = pd.read_excel(excel_file, sheet_name='receiptsWithItems')
                
                # Filter for credit only
                st.session_state.df_receipts = st.session_state.df_receipts[
                    st.session_state.df_receipts['PaymentMode'] == 'Credit'
                ]
                
                # Filter items
                receipt_ids = st.session_state.df_receipts['ReceiptId'].tolist()
                st.session_state.df_items = st.session_state.df_items[
                    st.session_state.df_items['ReceiptId'].isin(receipt_ids)
                ]
                st.session_state.df_items = st.session_state.df_items[
                    st.session_state.df_items['EntryType'] == 'Item'
                ]
                
                # Initialize payment data
                st.session_state.customer_payment_data = initialize_customer_payment_data()
                
                # Save data
                save_data()
                
                st.success(f"✅ Loaded {len(st.session_state.df_receipts)} credit transactions")
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")
        
        # Check if data exists from previous session
        elif st.session_state.df_receipts is not None:
            st.info("📂 Using previously uploaded data")
            if st.button("🔄 Clear Saved Data"):
                st.session_state.df_receipts = None
                st.session_state.df_items = None
                st.session_state.customer_payment_data = None
                # Delete saved files
                for file in ['saved_receipts.pkl', 'saved_items.pkl', 'saved_logo.bin']:
                    if os.path.exists(file):
                        os.remove(file)
                st.rerun()
        
        # Logo upload
        logo_file = st.file_uploader("Upload Logo (Optional)", type=['png', 'jpg', 'jpeg'])
        if logo_file:
            st.session_state.logo_bytes = logo_file.read()
            save_data()
            st.success("✅ Logo uploaded")
        
        st.markdown("---")
        st.info("💡 **Data persists between sessions!** No need to re-upload.")
    
    # Main content
    if st.session_state.df_receipts is None:
        st.info("👆 Please upload your Excel file to begin")
        st.markdown("""
        ### Features:
        - 📊 **Dashboard** - Summary statistics & recovery tracking
        - 📋 **Payment Tracking** - Editable table with all customer details
        - 📄 **Individual Bills** - Generate PDFs for each customer
        - 💾 **Persistent Storage** - Data saved between sessions
        """)
        return
    
    # Initialize payment data if not done
    if st.session_state.customer_payment_data is None:
        st.session_state.customer_payment_data = initialize_customer_payment_data()
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📋 Payment Tracking", "📄 Generate Bills", "ℹ️ Help"])
    
    with tab1:
        create_dashboard()
    
    with tab2:
        st.header("📋 Payment Tracking")
        st.markdown("Track all customer payments, advances, and balances")
        
        # Display editable dataframe
        edited_df = st.data_editor(
            st.session_state.customer_payment_data,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "Amount Due": st.column_config.NumberColumn(format="₹%.2f"),
                "Advance Amount": st.column_config.NumberColumn(format="₹%.2f"),
                "Amount Paid": st.column_config.NumberColumn(format="₹%.2f"),
                "Remaining Amount": st.column_config.NumberColumn(format="₹%.2f"),
                "Advance CF": st.column_config.NumberColumn(format="₹%.2f"),
                "Payment Status": st.column_config.SelectboxColumn(
                    options=["Due", "Partial", "Settled", "Advance"]
                ),
                "Cash Collected": st.column_config.CheckboxColumn(),
                "Cash Deposited": st.column_config.CheckboxColumn(),
            }
        )
        
        # Save changes
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Save Changes", type="primary"):
                st.session_state.customer_payment_data = edited_df
                
                # Update payment tracker
                for _, row in edited_df.iterrows():
                    phone = row['Phone']
                    st.session_state.payment_tracker[phone] = {
                        'customer_name': row['Name'],
                        'address': row['Address'],
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
                
                save_payment_tracker()
                st.success("✅ Changes saved!")
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
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col3:
            # Export to PDF
            if st.button("📄 Export to PDF"):
                pdf_bytes = create_payment_tracking_pdf()
                if pdf_bytes:
                    st.download_button(
                        "Download PDF",
                        pdf_bytes,
                        f"payment_tracking_{datetime.now().strftime('%Y%m%d')}.pdf",
                        "application/pdf"
                    )
    
    with tab3:
        st.header("📄 Generate Customer Bills")
        
        # Get credit customers
        credit_customers = st.session_state.df_receipts.groupby('CustomerNumber').agg({
            'CustomerName': 'first',
            'Total': 'sum'
        }).reset_index()
        
        # Customer selection
        customer_options = [
            f"{row['CustomerName']} - {normalize_phone(row['CustomerNumber'])} (Rs. {row['Total']:.2f})"
            for _, row in credit_customers.iterrows()
        ]
        
        selected_customer = st.selectbox("Select Customer", options=customer_options)
        
        if selected_customer:
            selected_phone = selected_customer.split(' - ')[1].split(' ')[0]
            
            # Get customer data
            customer_receipts = st.session_state.df_receipts[
                st.session_state.df_receipts['CustomerNumber'] == float(selected_phone)
            ]
            customer_items = st.session_state.df_items[
                st.session_state.df_items['ReceiptId'].isin(customer_receipts['ReceiptId'])
            ]
            
            customer_name = customer_receipts.iloc[0]['CustomerName']
            total_amount = customer_receipts['Total'].sum()
            
            # Get payment info from tracker
            payment_info = st.session_state.payment_tracker.get(selected_phone, {})
            
            st.metric("Total Amount", f"Rs. {total_amount:.2f}")
            
            # Generate bill
            if st.button("📥 Generate PDF Bill", type="primary"):
                with st.spinner("Generating bill..."):
                    pdf_bytes = create_bill_pdf(
                        customer_name,
                        selected_phone,
                        customer_receipts,
                        customer_items,
                        payment_info
                    )
                    
                    safe_name = customer_name.replace(' ', '_').replace('/', '_')
                    filename = f"{safe_name}_Bill_{datetime.now().strftime('%Y%m')}.pdf"
                    
                    st.download_button(
                        label="📄 Download Bill PDF",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf"
                    )
    
    with tab4:
        st.header("ℹ️ Help & Instructions")
        st.markdown("""
        ### 🎯 Key Features
        
        #### 1. Data Persistence
        - Data is **automatically saved** when you upload
        - **No need to re-upload** after app sleep
        - Click "Clear Saved Data" to remove old data
        
        #### 2. Dashboard
        - View total amounts, received, remaining
        - Track payment status (Paid/Unpaid/Advance/Partial)
        - See UPI vs Cash breakdown
        - Monitor recovery percentage
        
        #### 3. Payment Tracking
        - Edit customer payment details directly
        - Track advances, partial payments
        - Add remarks and payment dates
        - Export to Excel or PDF
        
        #### 4. Bill Generation
        - Generate individual customer bills
        - Automatic calculation of final amounts
        - Professional PDF with logo
        
        ### 📝 Monthly Workflow
        
        1. Upload POS data (once per month)
        2. Review Dashboard for overview
        3. Update Payment Tracking table
        4. Generate bills for customers
        5. Export reports for records
        
        ### 💡 Tips
        
        - Save changes in Payment Tracking regularly
        - Export data before clearing
        - Upload logo once (it persists)
        """)

if __name__ == "__main__":
    main()
