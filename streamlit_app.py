"""
Shri Lalita Bill Generator - OPTIMIZED & FAST
✅ No database locks
✅ Fast Excel processing  
✅ Progress indicators
"""
import streamlit as st
import pandas as pd
import sqlite3
from contextlib import contextmanager

st.set_page_config(page_title="Shri Lalita", page_icon="🥛", layout="wide")

DB = 'lalita.db'

@contextmanager
def db():
    c = sqlite3.connect(DB, timeout=30, check_same_thread=False)
    c.execute('PRAGMA journal_mode=WAL')  # FIX: No locks!
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
        c.execute('CREATE INDEX IF NOT EXISTS i1 ON receipts(phone)')
        c.execute('CREATE INDEX IF NOT EXISTS i2 ON items(rid)')

def norm(p):
    if pd.isna(p): return None
    s = str(int(float(p)))
    if s.startswith('91') and len(s)==12: s = s[2:]
    return s if len(s)==10 else s

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

def dash(df):
    st.header("📊 Dashboard")
    st.markdown("---")
    t = df['Amount Due'].sum()
    rec = df['Amount Paid'].sum()
    rem = df['Remaining Amount'].sum()
    recov = (rec/t*100) if t>0 else 0
    sc = df['Payment Status'].value_counts()
    c1,c2,c3 = st.columns(3)
    with c1:
        st.metric("💰 Total", f"₹{t:,.2f}")
        st.metric("✅ Received", f"₹{rec:,.2f}", f"{recov:.1f}%")
        st.metric("⏳ Remaining", f"₹{rem:,.2f}")
    with c2:
        st.metric("✔️ Paid", sc.get('Settled',0))
        st.metric("❌ Unpaid", sc.get('Due',0))
        st.metric("💵 Advance", sc.get('Advance',0))
        st.metric("⚠️ Partial", sc.get('Partial',0))
        st.metric("📊 Total", len(df))
    with c3:
        upi = df[df['Payment Mode'].str.contains('UPI|BHIM',case=False,na=False)]
        cash = df[df['Payment Mode'].str.contains('Cash',case=False,na=False)]
        ua = upi['Amount Paid'].sum()
        ca = cash['Amount Paid'].sum()
        st.metric("📱 UPI %", f"{(ua/rec*100 if rec>0 else 0):.2f}%")
        st.metric("💵 Cash %", f"{(ca/rec*100 if rec>0 else 0):.2f}%")
        st.metric("📱 UPI Amt", f"₹{ua:,.2f}")
        st.metric("💵 Cash Amt", f"₹{ca:,.2f}")
        st.metric("📱 UPI #", len(upi))
        st.metric("💵 Cash #", len(cash))
        st.metric("📈 Recovery", f"{recov:.2f}%")
    st.markdown("---")
    c1,c2 = st.columns(2)
    with c1:
        st.subheader("Status")
        st.bar_chart(sc)
    with c2:
        st.subheader("Top 10 Outstanding")
        top = df.nlargest(10,'Remaining Amount')[['Name','Phone','Remaining Amount']]
        top['Remaining Amount'] = top['Remaining Amount'].apply(lambda x:f"₹{x:,.2f}")
        st.dataframe(top,hide_index=True,use_container_width=True)

def main():
    if not pw(): return
    if 'i' not in st.session_state:
        init()
        st.session_state.i = True
    st.title("🥛 Shri Lalita")
    st.markdown("**Fast & Optimized**")
    st.markdown("---")
    with st.sidebar:
        st.header("📁 Data")
        r,i = load()
        if r is not None:
            st.success("✅ Loaded")
            st.info(f"📊 {len(r)} trans\n👥 {r['phone'].nunique()} cust")
        f = st.file_uploader("Excel", type=['xlsx','xls'])
        if f:
            try:
                with st.spinner("Processing..."):
                    s = st.empty()
                    s.info("Reading...")
                    dr = pd.read_excel(f, sheet_name='receipts',
                                      usecols=['ReceiptId','Date','CustomerName','CustomerNumber','Total','PaymentMode'])
                    di = pd.read_excel(f, sheet_name='receiptsWithItems',
                                      usecols=['ReceiptId','EntryType','EntryName','EntryAmount'])
                    s.info("Normalizing...")
                    dr['CustomerNumber'] = dr['CustomerNumber'].apply(norm)
                    s.info("Filtering...")
                    dr = dr[dr['PaymentMode']=='Credit']
                    di = di[di['ReceiptId'].isin(dr['ReceiptId']) & (di['EntryType']=='Item')]
                    s.empty()
                    if save(dr,di):
                        load.clear()
                        st.success(f"✅ {len(dr)} trans!")
                        st.balloons()
                        st.rerun()
            except Exception as e:
                st.error(str(e))
        if r is not None:
            st.markdown("---")
            if st.button("🗑️ Clear"):
                with db() as c:
                    c.execute('DELETE FROM receipts')
                    c.execute('DELETE FROM items')
                    c.execute('DELETE FROM tracking')
                load.clear()
                st.rerun()
        st.markdown("---")
        st.success("⚡ **Fast!**\n\n✅ No locks\n✅ Progress")
    if load()[0] is None:
        st.info("👆 Upload Excel")
        return
    if 'pd' not in st.session_state:
        st.session_state.pd = initpd()
    t1,t2 = st.tabs(["📊 Dashboard","📋 Tracking"])
    with t1:
        dash(st.session_state.pd)
    with t2:
        st.header("📋 Payment Tracking")
        df = st.session_state.pd
        c1,c2 = st.columns(2)
        with c1:
            n = st.text_input("🔍 Name","")
        with c2:
            p = st.text_input("🔍 Phone","")
        fdf = df.copy()
        if n: fdf = fdf[fdf['Name'].str.contains(n,case=False,na=False)]
        if p: fdf = fdf[fdf['Phone'].str.contains(p,na=False)]
        st.info(f"📊 {len(fdf)} of {len(df)}")
        ed = st.data_editor(fdf,use_container_width=True,hide_index=True,
                           column_config={
                               "Amount Due": st.column_config.NumberColumn(format="₹%.2f"),
                               "Amount Paid": st.column_config.NumberColumn(format="₹%.2f"),
                               "Remaining Amount": st.column_config.NumberColumn(format="₹%.2f"),
                               "Payment Status": st.column_config.SelectboxColumn(
                                   options=["Due","Partial","Settled","Advance"])})
        if st.button("💾 Save", type="primary"):
            if savet(ed):
                st.success("✅ Saved!")
                st.balloons()
                st.rerun()

if __name__ == "__main__":
    main()
