import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# تنظیمات اولیه صفحه
st.set_page_config(page_title="مدیریت انبار هوشمند iLux", page_icon="⚡", layout="wide")

# استایل اختصاصی راست‌به‌چپ (RTL) و فارسی
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/fonts/webfonts/css/font-face.css');
    * { font-family: 'Vazirmatn', sans-serif !important; direction: rtl; text-align: right; }
    .stMetric { background: rgba(120, 120, 120, 0.08); padding: 15px; border-radius: 12px; border: 1px solid rgba(120, 120, 120, 0.2); }
    div[data-testid="stMetricValue"] { font-size: 24px !important; color: #00d2ff; }
    .header-box { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 20px; border-radius: 14px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.15); }
    .badge-ok { background-color: #28a745; color: white; padding: 4px 8px; border-radius: 6px; font-size: 12px; }
    .badge-warning { background-color: #ffc107; color: black; padding: 4px 8px; border-radius: 6px; font-size: 12px; }
    .badge-danger { background-color: #dc3545; color: white; padding: 4px 8px; border-radius: 6px; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# اتصال و راه‌اندازی دیتابیس
def get_db():
    conn = sqlite3.connect("ilux_inventory.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT,
        protocol TEXT,
        brand TEXT,
        min_stock INTEGER DEFAULT 5,
        current_stock INTEGER DEFAULT 0,
        unit_price INTEGER DEFAULT 0,
        location TEXT,
        notes TEXT
    )""")
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        client TEXT,
        location TEXT,
        status TEXT DEFAULT 'در حال اجرا'
    )""")
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        type TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        project_name TEXT,
        technician TEXT,
        invoice_num TEXT,
        timestamp TEXT,
        notes TEXT,
        FOREIGN KEY (item_id) REFERENCES items(id)
    )""")
    
    # دیتای پیش‌فرض در صورت خالی بودن
    c.execute("SELECT COUNT(*) FROM items")
    if c.fetchone()[0] == 0:
        sample_items = [
            ('KNX-RL-08', 'رله هوشمند ۸ کانال ۱۶ آمپر', 'رله و عملگر', 'KNX', 'GVS', 3, 8, 18500000, 'قفسه A1', 'پشتیبانی از روشنایی و بار خازنی'),
            ('ZIG-MOT-01', 'موتور پرده برقی هوشمند', 'موتور و پرده', 'Zigbee', 'Tuya / iLux', 5, 14, 4800000, 'قفسه B2', 'بی‌صدا، ریل اکسترود شده'),
            ('ZIG-GW-01', 'گیت‌وی مرکزی چند حالته', 'گیت‌وی و کنترلر', 'Zigbee', 'Tuya', 2, 6, 2300000, 'قفسه A3', 'پشتیبانی از اترنت و وای‌فای'),
            ('KNX-SW-4F', 'کلید لمسی ۴ پل هوشمند', 'کلید لمسی', 'KNX', 'Schneider', 4, 3, 14200000, 'قفسه C1', 'دارای ترموستات داخلی'),
            ('KNX-SENS-01', 'سنسور حضور و روشنایی ۳۶۰ درجه', 'سنسور', 'KNX', 'ABB', 3, 5, 9600000, 'قفسه C2', 'حساسیت بالا با سنجش لوکس نور'),
            ('ZIG-LEAK-01', 'سنسور تشخیص نشتی آب و رطوبت', 'سنسور', 'Zigbee', 'Sonoff', 5, 2, 850000, 'قفسه B4', 'باتری‌خور، هشدار بیزر و اپلیکیشن'),
            ('DALI-DRV-24V', 'درایور ال‌ای‌دی دالی ۲۴ ولت ۱۵۰ وات', 'روشنایی', 'سایر / سنتی', 4, 10, 3200000, 'قفسه D1', 'دیمینگ نرم بدون فلیکر')
        ]
        c.executemany("INSERT INTO items (sku, name, category, protocol, brand, min_stock, current_stock, unit_price, location, notes) VALUES (?,?,?,?,?,?,?,?,?,?)", sample_items)
        
        sample_projects = [('پروژه ویلای لواسان (آقای دکتر راد)', 'دکتر راد', 'لواسان', 'در حال اجرا'),
                           ('برج مسکونی سعادت‌آباد واحد ۱۲', 'مهندس کمالی', 'سعادت‌آباد', 'در حال اجرا'),
                           ('انبار مرکزی شرکت iLux', 'شرکت', 'دفتر مرکزی', 'تکمیل شده')]
        c.executemany("INSERT INTO projects (name, client, location, status) VALUES (?,?,?,?)", sample_projects)
    conn.commit()

init_db()

# هدر اصلی
st.markdown("""
<div class="header-box">
    <h2 style="margin:0; padding:0; color:#ffffff;">⚡ سیستم جامع مدیریت انبار هوشمند iLux</h2>
    <p style="margin:5px 0 0 0; opacity:0.9; font-size:14px;">مدیریت قطعات، تجهیزات KNX و Zigbee، کنترل موجودی و حواله پروژه‌ها | مهندس علی قلی‌زاده</p>
</div>
""", unsafe_allow_html=True)

# زبانه‌ها (Tabs)
tab1, tab2, tab3, tab4 = st.tabs(["📊 داشبورد و آمار", "📦 موجودی و کاتالوگ قطعات", "📝 ثبت ورود و خروج (تراکنش)", "🏢 گزارشات و پروژه‌ها"])

conn = get_db()

# ----------------- تب ۱: داشبورد -----------------
with tab1:
    items_df = pd.read_sql("SELECT * FROM items", conn)
    
    total_items_count = len(items_df)
    total_qty = items_df['current_stock'].sum() if total_items_count > 0 else 0
    total_value = (items_df['current_stock'] * items_df['unit_price']).sum() if total_items_count > 0 else 0
    low_stock_count = len(items_df[items_df['current_stock'] <= items_df['min_stock']]) if total_items_count > 0 else 0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ارزش کل موجودی انبار", f"{total_value:,.0f} تومان")
    c2.metric("تعداد کل قطعات فیزیکی", f"{total_qty} عدد")
    c3.metric("تنوع اقلام تعریف‌شده", f"{total_items_count} قلم")
    c4.metric("اقلام نیازمند سفارش", f"{low_stock_count} کالا", delta=-low_stock_count if low_stock_count > 0 else 0, delta_color="inverse")
    
    st.write("---")
    col_chart, col_low = st.columns([1, 1])
    with col_chart:
        st.subheader("توزیع تجهیزات بر اساس پروتکل")
        if not items_df.empty:
            proto_dist = items_df.groupby('protocol')['current_stock'].sum()
            st.bar_chart(proto_dist)
    
    with col_low:
        st.subheader("⚠️ قطعات رو به اتمام (نقطه سفارش)")
        low_df = items_df[items_df['current_stock'] <= items_df['min_stock']]
        if not low_df.empty:
            for _, r in low_df.iterrows():
                st.warning(f"**{r['name']}** ({r['protocol']}) — موجودی: **{r['current_stock']}** (حداقل: {r['min_stock']})")
        else:
            st.success("تمام اقلام موجودی کافی دارند.")

# ----------------- تب ۲: موجودی و کاتالوگ -----------------
with tab2:
    st.subheader("لیست و موجودی لحظه‌ای انبار")
    
    sc1, sc2 = st.columns([2, 1])
    search_q = sc1.text_input("🔍 جستجو در نام، پارت‌نامبر (SKU) یا برند:")
    proto_filter = sc2.selectbox("فیلتر پروتکل:", ["همه", "KNX", "Zigbee", "سایر / سنتی"])
    
    query = "SELECT id, sku as 'کد کالا', name as 'نام قطعه', protocol as 'پروتکل', brand as 'برند', current_stock as 'موجودی', min_stock as 'حداقل مجاز', unit_price as 'قیمت واحد (تومان)', location as 'موقعیت قفسه' FROM items WHERE 1=1"
    params = []
    if search_q:
        query += " AND (name LIKE ? OR sku LIKE ? OR brand LIKE ?)"
        params.extend([f"%{search_q}%", f"%{search_q}%", f"%{search_q}%"])
    if proto_filter != "همه":
        query += " AND protocol = ?"
        params.append(proto_filter)
        
    filtered_df = pd.read_sql(query, conn, params=params)
    st.dataframe(filtered_df.drop(columns=['id']), use_container_width=True)
    
    with st.expander("➕ افزودن تجهیز / قطعه جدید به انبار"):
        with st.form("add_item_form", clear_on_submit=True):
            f1, f2, f3 = st.columns(3)
            new_sku = f1.text_input("کد کالا / پارت نامبر (یکتا) *", placeholder="مثال: KNX-DIM-04")
            new_name = f2.text_input("نام کامل قطعه *", placeholder="مثال: دیمر ۴ کانال یونیورسال")
            new_proto = f3.selectbox("پروتکل ارتباطی", ["KNX", "Zigbee", "سایر / سنتی"])
            
            f4, f5, f6 = st.columns(3)
            new_brand = f4.text_input("برند سازنده", placeholder="Schneider, Tuya, GVS...")
            new_stock = f5.number_input("موجودی اولیه فیزیکی", min_value=0, value=0)
            new_min = f6.number_input("حداقل نقطه سفارش", min_value=1, value=3)
            
            f7, f8 = st.columns(2)
            new_price = f7.number_input("قیمت واحد تخمینی (تومان)", min_value=0, step=100000)
            new_loc = f8.text_input("موقعیت در انبار", placeholder="مثال: قفسه A2")
            
            submitted = st.form_submit_button("ثبت قطعه در انبار")
            if submitted:
                if new_sku and new_name:
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO items (sku, name, protocol, brand, current_stock, min_stock, unit_price, location) VALUES (?,?,?,?,?,?,?,?)",
                                  (new_sku, new_name, new_proto, new_brand, new_stock, new_min, new_price, new_loc))
                        conn.commit()
                        st.success("✅ قطعه با موفقیت ذخیره شد!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"خطا در ثبت: {e}")
                else:
                    st.error("لطفاً فیلدهای ستاره‌دار را پر کنید.")

# ----------------- تب ۳: ثبت تراکنش -----------------
with tab3:
    st.subheader("ثبت حواله ورود کالا یا خروج به مقصد پروژه")
    
    items_list = pd.read_sql("SELECT id, name, sku, current_stock FROM items", conn)
    projects_list = pd.read_sql("SELECT name FROM projects", conn)['name'].tolist()
    
    item_options = {f"{r['name']} ({r['sku']}) - موجودی فعلی: {r['current_stock']}": r['id'] for _, r in items_list.iterrows()}
    
    with st.form("tx_form", clear_on_submit=True):
        t1, t2 = st.columns(2)
        tx_type = t1.radio("نوع تراکنش:", ["خروج کالا (ارسال به پروژه/مشتری)", "ورود کالا به انبار (خرید جدید)"], horizontal=True)
        selected_item_label = t2.selectbox("انتخاب قطعه:", list(item_options.keys()))
        
        t3, t4, t5 = st.columns(3)
        tx_qty = t3.number_input("تعداد:", min_value=1, value=1)
        tx_project = t4.selectbox("پروژه مقصد / انبار مبدا:", projects_list)
        tx_tech = t5.text_input("تکنسین تحویل‌گیرنده / تامین‌کننده:", placeholder="مهندس نصاب...")
        
        t6, t7 = st.columns(2)
        tx_invoice = t6.text_input("شماره حواله / فاکتور:", placeholder="INV-1403-...")
        tx_notes = t7.text_input("توضیحات تکمیلی:")
        
        btn_tx = st.form_submit_button("🚀 ثبت نهایی تراکنش")
        if btn_tx:
            item_id = item_options[selected_item_label]
            is_out = "خروج" in tx_type
            
            # بررسی موجودی برای خروج
            cur_item = conn.execute("SELECT current_stock, name FROM items WHERE id=?", (item_id,)).fetchone()
            if is_out and cur_item['current_stock'] < tx_qty:
                st.error(f"❌ موجودی انبار ({cur_item['current_stock']} عدد) برای این خروج کافی نیست!")
            else:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                c = conn.cursor()
                c.execute("INSERT INTO transactions (item_id, type, quantity, project_name, technician, invoice_num, timestamp, notes) VALUES (?,?,?,?,?,?,?,?)",
                          (item_id, "خروج" if is_out else "ورود", tx_qty, tx_project, tx_tech, tx_invoice, now_str, tx_notes))
                
                # به روز رسانی موجودی
                new_stock_val = cur_item['current_stock'] - tx_qty if is_out else cur_item['current_stock'] + tx_qty
                c.execute("UPDATE items SET current_stock=? WHERE id=?", (new_stock_val, item_id))
                conn.commit()
                st.success(f"✅ تراکنش با موفقیت ثبت شد! موجودی جدید {cur_item['name']}: {new_stock_val} عدد")
                st.rerun()

# ----------------- تب ۴: گزارشات و پروژه‌ها -----------------
with tab4:
    st.subheader("📋 ریزمصرف تجهیزات بر اساس پروژه و دانلود گزارش")
    
    tx_df = pd.read_sql("""
    SELECT t.timestamp as 'تاریخ و زمان', t.type as 'نوع', i.name as 'نام قطعه', i.protocol as 'پروتکل', 
           t.quantity as 'تعداد', t.project_name as 'پروژه', t.technician as 'تحویل‌گیرنده', t.invoice_num as 'شماره فاکتور'
    FROM transactions t
    JOIN items i ON t.item_id = i.id
    ORDER BY t.id DESC
    """, conn)
    
    st.dataframe(tx_df, use_container_width=True)
    
    # خروجی اکسل
    if not tx_df.empty:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            tx_df.to_excel(writer, sheet_name='گزارش تراکنش‌ها', index=False)
            items_df.to_excel(writer, sheet_name='موجودی انبار', index=False)
        st.download_button(
            label="📥 دانلود کامل دیتابیس به صورت فایل اکسل (Excel)",
            data=buffer.getvalue(),
            file_name=f"ilux_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.ms-excel"
        )
