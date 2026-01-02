"""
Shri Lalita Bill Generator - ENHANCED VERSION v2
✅ Individual Customer Details View
✅ PDF Bill Generation  
✅ Line Items View (what products bought)
✅ Payment Recording & History
✅ Customer Status PDF Report
✅ All existing features preserved
"""
import streamlit as st
import pandas as pd
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date
from io import BytesIO
import re

# PDF Generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER

st.set_page_config(page_title="Shri Lalita", page_icon="🥛", layout="wide")

DB = 'lalita.db'

# ==================== DATABASE ====================
@contextmanager
def db():
    c = sqlite3.connect(DB, timeout=30, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    try:
        yield c
        c.commit()
    finally:
        c.close()

def init():
    with db() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS receipts (
            rid TEXT PRIMARY KEY, date TEXT, name TEXT, phone TEXT, total REAL, mode TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY, rid TEXT, item TEXT, amt REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS tracking (
            phone TEXT PRIMARY KEY, name TEXT, addr TEXT, due REAL, prev REAL DEFAULT 0,
            adv REAL DEFAULT 0, status TEXT DEFAULT 'Due', paid REAL DEFAULT 0,
            rem REAL, pmode TEXT, date TEXT, ccol INT DEFAULT 0, cdep INT DEFAULT 0,
            remarks TEXT, acf REAL DEFAULT 0)''')
        # NEW: Payment history table
        c.execute('''CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY, phone TEXT, amount REAL, mode TEXT, 
            payment_date TEXT, remarks TEXT, created_at TEXT)''')
        c.execute('CREATE INDEX IF NOT EXISTS i1 ON receipts(phone)')
        c.execute('CREATE INDEX IF NOT EXISTS i2 ON items(rid)')
        c.execute('CREATE INDEX IF NOT EXISTS i3 ON payments(phone)')

def norm(p):
    if pd.isna(p): return None
    s = str(int(float(p)))
    if s.startswith('91') and len(s)==12: s = s[2:]
    return s if len(s)>=10 else s

# ==================== PASSWORD ====================
def pw():
    def ck():
        if st.session_state["pw"] == st.secrets.get("password", "lalita2025"):
            st.session_state["ok"] = True
            del st.session_state["pw"]
        else:
            st.session_state["ok"] = False
    if "ok" not in st.session_state:
        st.markdown("### 🔐 Shri Lalita")
        st.text_input("Password", type="password", on_change=ck, key="pw")
        st.info("💡 Default: **lalita2025**")
        return False
    elif not st.session_state["ok"]:
        st.markdown("### 🔐 Shri Lalita")
        st.text_input("Password", type="password", on_change=ck, key="pw")
        st.error("Wrong password")
        return False
    return True

# ==================== DATA FUNCTIONS ====================
def save(dr, di):
    p = st.progress(0)
    s = st.empty()
    try:
        with db() as c:
            s.text("Clearing...")
            c.execute('DELETE FROM receipts')
            c.execute('DELETE FROM items')
            p.progress(20)
            s.text(f"Saving {len(dr)} receipts...")
            c.executemany('INSERT INTO receipts VALUES (?,?,?,?,?,?)',
                         [(r.ReceiptId,str(r.Date),r.CustomerName,r.CustomerNumber,r.Total,r.PaymentMode) 
                          for _,r in dr.iterrows()])
            p.progress(60)
            s.text(f"Saving {len(di)} items...")
            c.executemany('INSERT INTO items VALUES (?,?,?,?)',
                         [(None,i.ReceiptId,i.EntryName,i.EntryAmount) for _,i in di.iterrows()])
            p.progress(100)
        s.empty()
        p.empty()
        return True
    except Exception as e:
        st.error(str(e))
        return False

@st.cache_data(ttl=300)
def load():
    try:
        with db() as c:
            r = pd.read_sql('SELECT * FROM receipts', c)
            i = pd.read_sql('SELECT * FROM items', c)
        return r if len(r)>0 else None, i if len(i)>0 else None
    except:
        return None, None

def initpd():
    r,i = load()
    if r is None: return None
    s = r.groupby('phone').agg({'name':'first','total':'sum'}).reset_index()
    with db() as c:
        t = pd.read_sql('SELECT * FROM tracking', c)
    m = s.merge(t, on='phone', how='left', suffixes=('','_t'))
    for col in ['prev','adv','paid','acf']:
        m[col] = m[col].fillna(0)
    m['status'] = m['status'].fillna('Due')
    m['pmode'] = m['pmode'].fillna('')
    m['date'] = m['date'].fillna('')
    m['addr'] = m['addr'].fillna('')
    m['remarks'] = m['remarks'].fillna('')
    m['ccol'] = m['ccol'].fillna(0).astype(bool)
    m['cdep'] = m['cdep'].fillna(0).astype(bool)
    m['rem'] = m['total'] + m['prev'] - m['adv'] - m['paid']
    return pd.DataFrame({
        'Name':m['name'],'Phone':m['phone'],'Address':m['addr'],'Amount Due':m['total'],
        'Previous Balance':m['prev'],'Advance Given?':m['adv'].apply(lambda x:'Yes' if x>0 else 'No'),
        'Advance Amount':m['adv'],'Payment Status':m['status'],'Amount Paid':m['paid'],
        'Remaining Amount':m['rem'],'Payment Mode':m['pmode'],'Received On':m['date'],
        'Cash Collected':m['ccol'],'Cash Deposited':m['cdep'],'Remarks':m['remarks'],'Advance CF':m['acf']})

def savet(df):
    try:
        with db() as c:
            c.executemany('INSERT OR REPLACE INTO tracking VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                         [(r.Phone,r.Name,r.Address,r['Amount Due'],r['Previous Balance'],
                           r['Advance Amount'],r['Payment Status'],r['Amount Paid'],r['Remaining Amount'],
                           r['Payment Mode'],r['Received On'],
                           1 if r['Cash Collected'] else 0,1 if r['Cash Deposited'] else 0,
                           r.Remarks,r['Advance CF']) for _,r in df.iterrows()])
        load.clear()
        return True
    except Exception as e:
        st.error(str(e))
        return False

# ==================== NEW: CUSTOMER DETAILS FUNCTIONS ====================
def get_customer_list():
    """Get list of all customers with totals"""
    r, _ = load()
    if r is None:
        return []
    customers = r.groupby('phone').agg({
        'name': 'first',
        'total': 'sum'
    }).reset_index()
    customers = customers.sort_values('total', ascending=False)
    return customers.to_dict('records')

def get_customer_details(phone):
    """Get full details for a single customer"""
    with db() as c:
        # Basic info
        cust = c.execute('SELECT * FROM receipts WHERE phone=? LIMIT 1', (phone,)).fetchone()
        if not cust:
            return None
        
        # All receipts
        receipts = c.execute('''
            SELECT rid, date, total FROM receipts WHERE phone=? ORDER BY date DESC
        ''', (phone,)).fetchall()
        
        # Tracking info
        tracking = c.execute('SELECT * FROM tracking WHERE phone=?', (phone,)).fetchone()
        
        # Payment history
        payments = c.execute('''
            SELECT * FROM payments WHERE phone=? ORDER BY payment_date DESC
        ''', (phone,)).fetchall()
        
        # Calculate totals
        total_purchases = sum(r['total'] for r in receipts)
        total_paid = sum(p['amount'] for p in payments) if payments else 0
        
        # Also get paid from tracking if no payment records
        if not payments and tracking:
            total_paid = tracking['paid'] or 0
        
        return {
            'name': cust['name'],
            'phone': phone,
            'receipts': [dict(r) for r in receipts],
            'tracking': dict(tracking) if tracking else None,
            'payments': [dict(p) for p in payments],
            'total_purchases': total_purchases,
            'total_paid': total_paid,
            'balance': total_purchases - total_paid
        }

def get_customer_items(phone):
    """Get all line items for a customer"""
    with db() as c:
        items = c.execute('''
            SELECT r.date, r.rid, i.item, i.amt 
            FROM items i 
            JOIN receipts r ON i.rid = r.rid 
            WHERE r.phone = ?
            ORDER BY r.date DESC
        ''', (phone,)).fetchall()
    return [dict(i) for i in items]

def record_payment(phone, amount, mode, payment_date, remarks=""):
    """Record a new payment"""
    with db() as c:
        # Insert payment record
        c.execute('''
            INSERT INTO payments (phone, amount, mode, payment_date, remarks, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (phone, amount, mode, payment_date, remarks, datetime.now().isoformat()))
        
        # Update tracking table
        existing = c.execute('SELECT * FROM tracking WHERE phone=?', (phone,)).fetchone()
        if existing:
            new_paid = (existing['paid'] or 0) + amount
            new_rem = (existing['due'] or 0) + (existing['prev'] or 0) - (existing['adv'] or 0) - new_paid
            new_status = 'Settled' if new_rem <= 0 else ('Partial' if new_paid > 0 else 'Due')
            
            c.execute('''
                UPDATE tracking SET 
                    paid = ?,
                    rem = ?,
                    pmode = ?,
                    date = ?,
                    status = ?
                WHERE phone = ?
            ''', (new_paid, new_rem, mode, payment_date, new_status, phone))
    
    # Clear cache
    load.clear()
    if 'pd' in st.session_state:
        st.session_state.pd = None

# ==================== PDF GENERATION ====================
def parse_item(entry_name):
    """Parse item entry like 'Buffalo Milk (2 X 75)'"""
    if pd.isna(entry_name):
        return None, 0, 0
    match = re.match(r'(.+?)\s*\((\d+\.?\d*)\s*X\s*(\d+\.?\d*)\)', str(entry_name))
    if match:
        return match.group(1).strip(), float(match.group(2)), float(match.group(3))
    return str(entry_name), 1, 0

def generate_customer_bill_pdf(phone):
    """Generate PDF bill for a customer"""
    details = get_customer_details(phone)
    if not details:
        return None
    
    items = get_customer_items(phone)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=15*mm, leftMargin=15*mm,
                           topMargin=15*mm, bottomMargin=15*mm)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Title2', parent=styles['Heading1'],
                             fontSize=18, alignment=TA_CENTER,
                             textColor=colors.HexColor('#1e3a5f')))
    styles.add(ParagraphStyle(name='Section', parent=styles['Heading2'],
                             fontSize=12, textColor=colors.HexColor('#1e3a5f'),
                             spaceBefore=10, spaceAfter=5))
    
    story = []
    
    # Title
    story.append(Paragraph("Customer Receipt", styles['Title2']))
    story.append(Paragraph("Shri Lalita - Pure and Natural Milk", styles['Normal']))
    story.append(Spacer(1, 5*mm))
    
    # Customer Info
    info_text = f"""
    <b>Name:</b> {details['name']}<br/>
    <b>Phone:</b> {details['phone']}<br/>
    <b>Payment Mode:</b> Credit
    """
    story.append(Paragraph(info_text, styles['Normal']))
    story.append(Spacer(1, 5*mm))
    
    # Items Table
    story.append(Paragraph("Purchase Details", styles['Section']))
    
    table_data = [['Date', 'Product', 'Qty', 'Rate', 'Amount']]
    for item in items:
        product, qty, rate = parse_item(item['item'])
        if product:
            amt = item['amt'] if item['amt'] else qty * rate
            table_data.append([
                str(item['date'])[:16] if item['date'] else '',
                product[:30],
                f"{qty:.0f}" if qty == int(qty) else f"{qty:.1f}",
                f"Rs.{rate:.2f}",
                f"Rs.{amt:.2f}"
            ])
    
    if len(table_data) > 1:
        col_widths = [35*mm, 60*mm, 20*mm, 30*mm, 30*mm]
        items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(items_table)
    
    story.append(Spacer(1, 8*mm))
    
    # Summary
    story.append(Paragraph("Summary", styles['Section']))
    
    summary_data = [
        ['Total Purchases:', f"Rs.{details['total_purchases']:,.2f}"],
        ['Amount Paid:', f"Rs.{details['total_paid']:,.2f}"],
        ['Balance Due:', f"Rs.{details['balance']:,.2f}"],
    ]
    
    summary_table = Table(summary_data, colWidths=[100*mm, 60*mm])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, -1), (1, -1), 
         colors.HexColor('#d32f2f') if details['balance'] > 0 else colors.HexColor('#2e7d32')),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#1e3a5f')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    
    # Payment History
    if details['payments']:
        story.append(Spacer(1, 8*mm))
        story.append(Paragraph("Payment History", styles['Section']))
        
        pay_data = [['Date', 'Amount', 'Mode', 'Remarks']]
        for p in details['payments']:
            pay_data.append([
                p.get('payment_date', ''),
                f"Rs.{p.get('amount', 0):,.2f}",
                p.get('mode', ''),
                (p.get('remarks', '') or '')[:20]
            ])
        
        pay_table = Table(pay_data, colWidths=[35*mm, 35*mm, 35*mm, 55*mm])
        pay_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4caf50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(pay_table)
    
    # Footer
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}",
        ParagraphStyle(name='Footer', fontSize=8, alignment=TA_CENTER, textColor=colors.gray)
    ))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_status_report_pdf(df):
    """Generate customer status report PDF"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=10*mm, leftMargin=10*mm,
                           topMargin=15*mm, bottomMargin=15*mm)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Title2', parent=styles['Heading1'],
                             fontSize=16, alignment=TA_CENTER,
                             textColor=colors.HexColor('#1e3a5f')))
    
    story = []
    
    # Title
    story.append(Paragraph("Customer Status Report", styles['Title2']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}", 
                          ParagraphStyle(name='Sub', fontSize=10, alignment=TA_CENTER)))
    story.append(Spacer(1, 5*mm))
    
    # Summary Stats
    total = df['Amount Due'].sum()
    received = df['Amount Paid'].sum()
    remaining = df['Remaining Amount'].sum()
    recovery = (received/total*100) if total > 0 else 0
    
    stats_data = [
        ['Total Amount', 'Received', 'Remaining', 'Recovery %'],
        [f"Rs.{total:,.2f}", f"Rs.{received:,.2f}", f"Rs.{remaining:,.2f}", f"{recovery:.1f}%"]
    ]
    
    stats_table = Table(stats_data, colWidths=[45*mm, 45*mm, 45*mm, 45*mm])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1e3a5f')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 5*mm))
    
    # Status counts
    sc = df['Payment Status'].value_counts()
    count_text = f"Settled: {sc.get('Settled', 0)} | Partial: {sc.get('Partial', 0)} | Due: {sc.get('Due', 0)} | Total: {len(df)}"
    story.append(Paragraph(count_text, ParagraphStyle(name='Counts', fontSize=10, alignment=TA_CENTER)))
    story.append(Spacer(1, 5*mm))
    
    # Customer List
    table_data = [['#', 'Customer', 'Phone', 'Amount', 'Paid', 'Due', 'Status']]
    
    for i, (_, row) in enumerate(df.iterrows(), 1):
        status = row['Payment Status']
        table_data.append([
            str(i),
            str(row['Name'])[:20],
            str(row['Phone']),
            f"Rs.{row['Amount Due']:,.0f}",
            f"Rs.{row['Amount Paid']:,.0f}",
            f"Rs.{row['Remaining Amount']:,.0f}",
            status.upper()[:3]
        ])
    
    col_widths = [10*mm, 40*mm, 28*mm, 28*mm, 28*mm, 28*mm, 15*mm]
    cust_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    cust_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(cust_table)
    
    # Footer
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("Shri Lalita - Credit Management System",
                          ParagraphStyle(name='Footer', fontSize=8, alignment=TA_CENTER, textColor=colors.gray)))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# ==================== UI VIEWS ====================
def dash(df):
    """Dashboard view"""
    if df is None or len(df) == 0:
        st.info("📤 No customer data available yet")
        return
    
    st.header("📊 Dashboard")
    
    t = df['Amount Due'].sum()
    rec = df['Amount Paid'].sum()
    rem = df['Remaining Amount'].sum()
    recov = (rec/t*100) if t>0 else 0
    sc = df['Payment Status'].value_counts()
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("💰 Total Amount", f"₹{t:,.2f}")
        st.metric("✅ Received", f"₹{rec:,.2f}", f"{recov:.1f}%")
        st.metric("⏳ Remaining", f"₹{rem:,.2f}")
    with c2:
        st.metric("✔️ Settled", sc.get('Settled', 0))
        st.metric("⚠️ Partial", sc.get('Partial', 0))
        st.metric("❌ Due", sc.get('Due', 0))
        st.metric("📊 Total Customers", len(df))
    with c3:
        upi = df[df['Payment Mode'].str.contains('UPI|BHIM', case=False, na=False)]
        cash = df[df['Payment Mode'].str.contains('Cash', case=False, na=False)]
        ua = upi['Amount Paid'].sum()
        ca = cash['Amount Paid'].sum()
        st.metric("📱 UPI Amount", f"₹{ua:,.2f}")
        st.metric("💵 Cash Amount", f"₹{ca:,.2f}")
        st.metric("📈 Recovery %", f"{recov:.2f}%")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Status Breakdown")
        st.bar_chart(sc)
    with col2:
        st.subheader("🔝 Top 10 Outstanding")
        top = df.nlargest(10, 'Remaining Amount')[['Name', 'Phone', 'Remaining Amount']]
        top['Remaining Amount'] = top['Remaining Amount'].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(top, hide_index=True, use_container_width=True)

def customer_detail_view():
    """NEW: Individual customer detail view"""
    st.header("👤 Customer Details")
    
    customers = get_customer_list()
    if not customers:
        st.warning("No customers found. Please upload data first.")
        return
    
    # Customer selector
    col1, col2 = st.columns([3, 1])
    with col1:
        customer_options = [f"{c['name']} ({c['phone']}) - ₹{c['total']:,.2f}" for c in customers]
        selected_idx = st.selectbox("🔍 Select Customer", options=range(len(customers)), 
                                   format_func=lambda x: customer_options[x])
    
    if selected_idx is not None:
        phone = customers[selected_idx]['phone']
        details = get_customer_details(phone)
        
        if details:
            with col2:
                # Download PDF button
                pdf_buffer = generate_customer_bill_pdf(phone)
                if pdf_buffer:
                    st.download_button(
                        "📄 Download Bill",
                        data=pdf_buffer,
                        file_name=f"{details['name'].replace(' ', '_')}_{phone}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            
            # Customer Info Card
            st.markdown("---")
            
            # Info row
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"### {details['name']}")
                st.markdown(f"📞 {details['phone']}")
            with col2:
                st.metric("Total Purchases", f"₹{details['total_purchases']:,.2f}")
            with col3:
                st.metric("Amount Paid", f"₹{details['total_paid']:,.2f}")
            with col4:
                balance_color = "🔴" if details['balance'] > 0 else "🟢"
                st.metric(f"{balance_color} Balance Due", f"₹{details['balance']:,.2f}")
            
            st.markdown("---")
            
            # Tabs for different views
            tab1, tab2, tab3 = st.tabs(["📦 Items Purchased", "🧾 Receipts", "💳 Payments"])
            
            with tab1:
                items = get_customer_items(phone)
                if items:
                    items_df = pd.DataFrame(items)
                    items_df.columns = ['Date', 'Receipt ID', 'Item', 'Amount']
                    items_df['Amount'] = items_df['Amount'].apply(lambda x: f"₹{x:,.2f}" if x else "-")
                    st.dataframe(items_df, hide_index=True, use_container_width=True, height=400)
                    st.info(f"📊 Total {len(items)} items")
                else:
                    st.info("No items found")
            
            with tab2:
                if details['receipts']:
                    receipts_df = pd.DataFrame(details['receipts'])
                    receipts_df.columns = ['Receipt ID', 'Date', 'Total']
                    receipts_df['Total'] = receipts_df['Total'].apply(lambda x: f"₹{x:,.2f}")
                    st.dataframe(receipts_df, hide_index=True, use_container_width=True)
                    st.info(f"📊 Total {len(details['receipts'])} receipts")
                else:
                    st.info("No receipts found")
            
            with tab3:
                st.subheader("Payment History")
                if details['payments']:
                    pay_df = pd.DataFrame(details['payments'])
                    pay_df = pay_df[['payment_date', 'amount', 'mode', 'remarks']]
                    pay_df.columns = ['Date', 'Amount', 'Mode', 'Remarks']
                    pay_df['Amount'] = pay_df['Amount'].apply(lambda x: f"₹{x:,.2f}")
                    st.dataframe(pay_df, hide_index=True, use_container_width=True)
                else:
                    st.info("No payments recorded yet")
                
                # Record new payment
                st.markdown("---")
                st.subheader("➕ Record New Payment")
                
                with st.form("payment_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        amount = st.number_input("Amount (₹)", min_value=0.0, 
                                                value=float(max(0, details['balance'])),
                                                step=100.0, format="%.2f")
                        mode = st.selectbox("Payment Mode", ["Cash", "UPI", "Bank Transfer"])
                    with col2:
                        payment_date = st.date_input("Payment Date", value=date.today())
                        remarks = st.text_input("Remarks (optional)")
                    
                    submitted = st.form_submit_button("💾 Save Payment", type="primary", use_container_width=True)
                    
                    if submitted:
                        if amount > 0:
                            record_payment(phone, amount, mode, str(payment_date), remarks)
                            st.success(f"✅ Payment of ₹{amount:,.2f} recorded!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("Please enter a valid amount")

def tracking_view(df):
    """Payment tracking grid view"""
    st.header("📋 Payment Tracking")
    
    # Filters
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    with col1:
        name_filter = st.text_input("🔍 Search Name", "")
    with col2:
        phone_filter = st.text_input("🔍 Search Phone", "")
    with col3:
        status_filter = st.selectbox("Status", ["All", "Due", "Partial", "Settled", "Advance"])
    with col4:
        # Download Status Report PDF
        pdf_buffer = generate_status_report_pdf(df)
        st.download_button(
            "📄 Status PDF",
            data=pdf_buffer,
            file_name=f"Status_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    
    # Filter data
    fdf = df.copy()
    if name_filter:
        fdf = fdf[fdf['Name'].str.contains(name_filter, case=False, na=False)]
    if phone_filter:
        fdf = fdf[fdf['Phone'].str.contains(phone_filter, na=False)]
    if status_filter != "All":
        fdf = fdf[fdf['Payment Status'] == status_filter]
    
    st.info(f"📊 Showing {len(fdf)} of {len(df)} customers")
    
    # Editable data grid
    ed = st.data_editor(
        fdf,
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config={
            "Amount Due": st.column_config.NumberColumn(format="₹%.2f"),
            "Amount Paid": st.column_config.NumberColumn(format="₹%.2f"),
            "Remaining Amount": st.column_config.NumberColumn(format="₹%.2f"),
            "Previous Balance": st.column_config.NumberColumn(format="₹%.2f"),
            "Advance Amount": st.column_config.NumberColumn(format="₹%.2f"),
            "Advance CF": st.column_config.NumberColumn(format="₹%.2f"),
            "Payment Status": st.column_config.SelectboxColumn(
                options=["Due", "Partial", "Settled", "Advance"]
            ),
            "Payment Mode": st.column_config.SelectboxColumn(
                options=["", "Cash", "UPI", "Bank Transfer"]
            ),
        }
    )
    
    if st.button("💾 Save Changes", type="primary"):
        if savet(ed):
            st.success("✅ Changes saved!")
            st.balloons()
            st.rerun()

# ==================== MAIN APP ====================
def main():
    if not pw():
        return
    
    if 'i' not in st.session_state:
        init()
        st.session_state.i = True
    
    st.title("🥛 Shri Lalita")
    st.caption("Credit Management System - Enhanced v2")
    
    # Sidebar
    with st.sidebar:
        st.header("📁 Data Management")
        r, i = load()
        
        if r is not None:
            st.success(f"✅ Data Loaded")
            st.info(f"📊 {len(r)} transactions\n👥 {r['phone'].nunique()} customers")
        
        f = st.file_uploader("📤 Upload Excel", type=['xlsx', 'xls'], key='excel_upload')
        
        if f and ('last_upload' not in st.session_state or st.session_state.get('last_upload') != f.name):
            try:
                with st.spinner("Processing..."):
                    s = st.empty()
                    s.info("📖 Reading Excel...")
                    dr = pd.read_excel(f, sheet_name='receipts',
                                      usecols=['ReceiptId', 'Date', 'CustomerName', 'CustomerNumber', 'Total', 'PaymentMode'])
                    di = pd.read_excel(f, sheet_name='receiptsWithItems',
                                      usecols=['ReceiptId', 'EntryType', 'EntryName', 'EntryAmount'])
                    s.info("🔧 Normalizing phones...")
                    dr['CustomerNumber'] = dr['CustomerNumber'].apply(norm)
                    s.info("🔍 Filtering credit transactions...")
                    dr = dr[dr['PaymentMode'] == 'Credit']
                    di = di[di['ReceiptId'].isin(dr['ReceiptId']) & (di['EntryType'] == 'Item')]
                    s.empty()
                    
                    if save(dr, di):
                        st.session_state.last_upload = f.name
                        st.session_state.pd = None
                        load.clear()
                        st.success(f"✅ Processed {len(dr)} transactions!")
                        st.balloons()
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
        
        if r is not None:
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Refresh", use_container_width=True):
                    st.session_state.pd = None
                    load.clear()
                    st.rerun()
            with col2:
                if st.button("🗑️ Clear", use_container_width=True):
                    with db() as c:
                        c.execute('DELETE FROM receipts')
                        c.execute('DELETE FROM items')
                        c.execute('DELETE FROM tracking')
                        c.execute('DELETE FROM payments')
                    st.session_state.pd = None
                    st.session_state.last_upload = None
                    load.clear()
                    st.success("Cleared!")
                    st.rerun()
        
        st.markdown("---")
        st.markdown("""
        ### ✨ Features
        - 📊 Dashboard
        - 👤 **Customer Details** ⭐
        - 📦 **Line Items View** ⭐
        - 📄 **PDF Bills** ⭐
        - 💳 **Payment Recording** ⭐
        - 📋 Status Report PDF
        """)
    
    # Main content
    if load()[0] is None:
        st.info("👆 Upload Excel file to start")
        st.markdown("""
        ### 🚀 New Features in v2:
        
        | Feature | Description |
        |---------|-------------|
        | 👤 **Customer Details** | View individual customer's full history |
        | 📦 **Line Items** | See what products each customer bought |
        | 📄 **PDF Bills** | Download professional PDF bill per customer |
        | 💳 **Payment Recording** | Record payments with history tracking |
        | 📋 **Status Report** | Download full customer status as PDF |
        """)
        return
    
    # Initialize data
    if 'pd' not in st.session_state or st.session_state.pd is None:
        with st.spinner("Loading..."):
            st.session_state.pd = initpd()
    
    if st.session_state.pd is None:
        st.warning("⚠️ No data. Please upload Excel file.")
        return
    
    # Navigation tabs
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "👤 Customer Details", "📋 Tracking"])
    
    with tab1:
        dash(st.session_state.pd)
    
    with tab2:
        customer_detail_view()
    
    with tab3:
        tracking_view(st.session_state.pd)

if __name__ == "__main__":
    main()
