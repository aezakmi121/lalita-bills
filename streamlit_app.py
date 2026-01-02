"""
Shri Lalita Bill Generator - Streamlit Web App
Monthly billing system for credit customers with payment tracking
"""

import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
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
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.markdown("### 🔐 Shri Lalita Bill Generator")
        st.markdown("#### Enter Password to Continue")
        st.text_input(
            "Password", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.info("💡 Default password: **lalita2025**")
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input again
        st.markdown("### 🔐 Shri Lalita Bill Generator")
        st.markdown("#### Enter Password to Continue")
        st.text_input(
            "Password", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct
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

# Load payment tracker from file
def load_payment_tracker():
    try:
        if os.path.exists('payment_tracker.json'):
            with open('payment_tracker.json', 'r') as f:
                st.session_state.payment_tracker = json.load(f)
    except:
        st.session_state.payment_tracker = {}

# Save payment tracker to file
def save_payment_tracker():
    try:
        with open('payment_tracker.json', 'w') as f:
            json.dump(st.session_state.payment_tracker, f, indent=2)
    except Exception as e:
        st.error(f"Failed to save payment tracker: {str(e)}")

# Normalize phone number
def normalize_phone(phone):
    if pd.isna(phone):
        return None
    phone_str = str(int(float(phone)))
    return phone_str

# Create PDF bill
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
    
    heading_style = ParagraphStyle(
        'CustomHeading', parent=styles['Heading2'], fontSize=14,
        textColor=colors.HexColor('#1a5490'), spaceAfter=10,
        spaceBefore=15, fontName='Helvetica-Bold'
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
    
    # Customer Information
    date_range = f"{df_receipts['Date'].min()} to {df_receipts['Date'].max()}"
    
    customer_data = [
        ['Customer Information', ''],
        ['Name:', customer_name],
        ['Phone:', phone],
        ['Payment Mode:', 'Credit'],
        ['Billing Period:', date_range],
    ]
    
    customer_table = Table(customer_data, colWidths=[120*mm, 60*mm])
    customer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(customer_table)
    story.append(Spacer(1, 8*mm))
    
    # Transaction table
    story.append(Paragraph("Transaction Details", heading_style))
    
    trans_data = [['Date', 'Receipt ID', 'Items', 'Amount (Rs.)']]
    
    for idx, row in df_receipts.iterrows():
        receipt_id = row['ReceiptId']
        date_str = str(row['Date'])
        total = f"Rs. {row['Total']:.2f}"
        
        items = df_items[df_items['ReceiptId'] == receipt_id]
        if len(items) > 0:
            items_str = '\n'.join(items['EntryName'].tolist())
        else:
            items_str = 'No items'
        
        trans_data.append([date_str, receipt_id, items_str, total])
    
    trans_table = Table(trans_data, colWidths=[38*mm, 28*mm, 84*mm, 30*mm])
    trans_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
    ]))
    
    story.append(trans_table)
    story.append(Spacer(1, 8*mm))
    
    # Payment Summary
    total_amount = df_receipts['Total'].sum()
    
    summary_data = [
        ['Payment Summary', ''],
        ['Total Transactions:', str(len(df_receipts))],
        ['Total Amount:', f'Rs. {total_amount:.2f}'],
    ]
    
    # Add payment tracking info if available
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
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#ffffcc')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#90EE90')),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('FONTSIZE', (0, -1), (-1, -1), 13),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 10*mm))
    
    # Product summary on new page
    story.append(PageBreak())
    story.append(Paragraph("Product Summary", heading_style))
    story.append(Spacer(1, 5*mm))
    
    product_summary = df_items.groupby('EntryName').agg({
        'EntryAmount': ['sum', 'count']
    }).reset_index()
    product_summary.columns = ['Product', 'Total Amount', 'Quantity']
    product_summary = product_summary.sort_values('Total Amount', ascending=False)
    
    product_data = [['Product', 'Quantity', 'Total Amount (Rs.)']]
    for _, row in product_summary.iterrows():
        product_data.append([
            row['Product'],
            int(row['Quantity']),
            f"Rs. {row['Total Amount']:.2f}"
        ])
    
    product_table = Table(product_data, colWidths=[110*mm, 35*mm, 35*mm])
    product_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
    ]))
    
    story.append(product_table)
    story.append(Spacer(1, 10*mm))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'], fontSize=9,
        textColor=colors.grey, alignment=TA_CENTER
    )
    
    story.append(Spacer(1, 15*mm))
    story.append(Paragraph("Thank you for your business!", footer_style))
    story.append(Paragraph("Shri Lalita - By Maharani Farm", footer_style))
    story.append(Paragraph(f"Bill Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", footer_style))
    
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
    st.markdown("**For Credit Payment Customers**")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("📁 Upload Files")
        
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
                
                st.success(f"✅ Loaded {len(st.session_state.df_receipts)} credit transactions")
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")
        
        # Logo upload
        logo_file = st.file_uploader("Upload Logo (Optional)", type=['png', 'jpg', 'jpeg'])
        if logo_file:
            st.session_state.logo_bytes = logo_file.read()
            st.success("✅ Logo uploaded")
        
        st.markdown("---")
        st.info("💡 **Tip:** Upload your monthly POS data to get started")
    
    # Main content
    if st.session_state.df_receipts is None:
        st.info("👆 Please upload your Excel file to begin")
        st.markdown("""
        ### How to use:
        1. Upload your POS data Excel file
        2. Select a customer
        3. Review/adjust payment details
        4. Generate and download PDF bill
        """)
        return
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Generate Bills", "💰 Payment Tracker", "📊 Summary", "ℹ️ Help"])
    
    with tab1:
        st.header("Generate Customer Bills")
        
        # Get credit customers
        credit_customers = st.session_state.df_receipts.groupby('CustomerNumber').agg({
            'CustomerName': 'first',
            'Total': 'sum'
        }).reset_index()
        credit_customers = credit_customers.sort_values('Total', ascending=False)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Customer selection
            customer_options = [
                f"{row['CustomerName']} - {normalize_phone(row['CustomerNumber'])} (Rs. {row['Total']:.2f})"
                for _, row in credit_customers.iterrows()
            ]
            
            selected_customer = st.selectbox(
                "Select Customer",
                options=customer_options,
                help="Shows: Name - Phone - Total Amount"
            )
            
            if selected_customer:
                # Extract phone from selection
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
                
                # Payment tracking
                st.markdown("### Payment Details")
                
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    previous_balance = st.number_input(
                        "Previous Balance (Rs.)",
                        value=st.session_state.payment_tracker.get(selected_phone, {}).get('previous_balance', 0.0),
                        step=10.0,
                        help="Any pending amount from last month"
                    )
                
                with col_b:
                    advance_paid = st.number_input(
                        "Advance Paid (Rs.)",
                        value=st.session_state.payment_tracker.get(selected_phone, {}).get('advance_paid', 0.0),
                        step=10.0,
                        help="Any advance payment received this month"
                    )
                
                with col_c:
                    final_amount = total_amount + previous_balance - advance_paid
                    st.metric("Final Amount Due", f"Rs. {final_amount:.2f}")
                
                # Save payment info
                if st.button("💾 Save Payment Info"):
                    st.session_state.payment_tracker[selected_phone] = {
                        'customer_name': customer_name,
                        'previous_balance': previous_balance,
                        'advance_paid': advance_paid,
                        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    save_payment_tracker()
                    st.success("Payment info saved!")
                
                # Transaction preview
                st.markdown("### Transaction Preview")
                st.dataframe(
                    customer_receipts[['Date', 'ReceiptId', 'Total']],
                    use_container_width=True
                )
                
                # Generate bill
                if st.button("📥 Generate PDF Bill", type="primary"):
                    with st.spinner("Generating bill..."):
                        payment_info = {
                            'previous_balance': previous_balance,
                            'advance_paid': advance_paid
                        }
                        
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
                        
                        st.success(f"✅ Bill generated for {customer_name}!")
                        st.info(f"Total: Rs. {total_amount:.2f} | Final Due: Rs. {final_amount:.2f}")
        
        with col2:
            st.markdown("### Quick Stats")
            st.metric("Transactions", len(customer_receipts))
            st.metric("Total Amount", f"Rs. {total_amount:.2f}")
            st.metric("Avg per Transaction", f"Rs. {customer_receipts['Total'].mean():.2f}")
    
    with tab2:
        st.header("💰 Payment Tracker")
        st.markdown("Track payment status for all credit customers")
        
        if st.session_state.payment_tracker:
            tracker_df = pd.DataFrame([
                {
                    'Phone': phone,
                    'Customer': info['customer_name'],
                    'Previous Balance': info.get('previous_balance', 0),
                    'Advance Paid': info.get('advance_paid', 0),
                    'Last Updated': info.get('last_updated', 'N/A')
                }
                for phone, info in st.session_state.payment_tracker.items()
            ])
            
            st.dataframe(tracker_df, use_container_width=True)
            
            # Export tracker
            csv = tracker_df.to_csv(index=False)
            st.download_button(
                "📥 Export Payment Tracker (CSV)",
                csv,
                f"payment_tracker_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
            
            # Clear tracker
            if st.button("🗑️ Clear All Payment Data", type="secondary"):
                if st.checkbox("Confirm deletion"):
                    st.session_state.payment_tracker = {}
                    save_payment_tracker()
                    st.success("Payment tracker cleared")
                    st.rerun()
        else:
            st.info("No payment tracking data yet. Add payment details when generating bills.")
    
    with tab3:
        st.header("📊 Monthly Summary")
        
        # Overall stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Credit Customers",
                len(credit_customers)
            )
        
        with col2:
            st.metric(
                "Total Transactions",
                len(st.session_state.df_receipts)
            )
        
        with col3:
            total_revenue = st.session_state.df_receipts['Total'].sum()
            st.metric(
                "Total Credit Amount",
                f"Rs. {total_revenue:.2f}"
            )
        
        with col4:
            avg_bill = total_revenue / len(credit_customers)
            st.metric(
                "Avg Bill per Customer",
                f"Rs. {avg_bill:.2f}"
            )
        
        st.markdown("---")
        
        # Top customers
        st.subheader("Top 10 Credit Customers")
        top_customers = credit_customers.head(10).copy()
        top_customers['Phone'] = top_customers['CustomerNumber'].apply(normalize_phone)
        st.dataframe(
            top_customers[['CustomerName', 'Phone', 'Total']].rename(columns={'Total': 'Amount (Rs.)'}),
            use_container_width=True
        )
        
        # Product summary
        st.markdown("---")
        st.subheader("Product Sales Summary")
        product_summary = st.session_state.df_items.groupby('EntryName').agg({
            'EntryAmount': ['sum', 'count']
        }).reset_index()
        product_summary.columns = ['Product', 'Revenue', 'Quantity']
        product_summary = product_summary.sort_values('Revenue', ascending=False)
        
        st.dataframe(product_summary, use_container_width=True)
        
        # Export summary
        if st.button("📥 Export Summary Report"):
            summary_excel = io.BytesIO()
            with pd.ExcelWriter(summary_excel, engine='openpyxl') as writer:
                credit_customers.to_excel(writer, sheet_name='Customers', index=False)
                product_summary.to_excel(writer, sheet_name='Products', index=False)
            
            st.download_button(
                "Download Excel Summary",
                summary_excel.getvalue(),
                f"summary_{datetime.now().strftime('%Y%m')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with tab4:
        st.header("ℹ️ Help & Instructions")
        
        st.markdown("""
        ### How to Use This App
        
        #### 1️⃣ Upload Data
        - Click **"Upload POS Data"** in the sidebar
        - Select your Excel file with receipts
        - System automatically filters **Credit payments only**
        
        #### 2️⃣ Generate Bills
        - Go to **"Generate Bills"** tab
        - Select a customer from dropdown
        - Add previous balance or advance payment if applicable
        - Click **"Save Payment Info"** to track
        - Click **"Generate PDF Bill"** to create bill
        - Download and share via WhatsApp
        
        #### 3️⃣ Track Payments
        - Use **"Payment Tracker"** tab to see all payment records
        - Export to CSV for your records
        
        #### 4️⃣ View Summary
        - **"Summary"** tab shows overall statistics
        - See top customers and product sales
        - Export summary reports
        
        ### Excel File Format Required
        
        Your Excel file must have two sheets:
        
        **Sheet 1: receipts**
        - Date, ReceiptId, CustomerName, CustomerNumber
        - Total, PaymentMode, etc.
        
        **Sheet 2: receiptsWithItems**
        - ReceiptId, EntryType, EntryName, EntryAmount
        - EntryType should be "Item" for products
        
        ### Security
        - Password protected access
        - Data stored locally during session
        - Payment tracker saved to file
        - No data sent to external servers
        
        ### Support
        - Default password: **lalita2025**
        - Change password in `.streamlit/secrets.toml`
        
        ### Tips
        - 💾 Save payment info before generating bills
        - 📱 Share PDF via WhatsApp after download
        - 📊 Export summaries for record keeping
        - 🔄 Upload fresh data each month
        """)

if __name__ == "__main__":
    main()
