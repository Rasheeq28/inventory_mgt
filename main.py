import streamlit as st
from supabase import create_client
import os
from datetime import datetime

# ---------------- SUPABASE CONNECTION ----------------
SUPABASE_URL = os.getenv("SUPABASE_URL", st.secrets["SUPABASE_URL"])
SUPABASE_KEY = os.getenv("SUPABASE_KEY", st.secrets["SUPABASE_KEY"])
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Inventory Management", layout="wide")

# ---------------- NAVIGATION ----------------
st.sidebar.title("📦 Inventory Management")
page = st.sidebar.radio("Go to", ["Stock In", "Sell", "Accrual", "Reports"])

# ---------------- STOCK IN ----------------
# ---------------- STOCK IN ----------------
if page == "Stock In":
    st.header("➕ Add Stock to Inventory")
    with st.form("stock_in_form"):
        sku = st.text_input("SKU (unique)", placeholder="Enter a unique SKU")
        name = st.text_input("Product Name", placeholder="Enter product name")
        price = st.number_input("Unit Price", min_value=0.0, step=0.01, format="%.2f")
        qty = st.number_input("Quantity", min_value=1, step=1)
        submitted = st.form_submit_button("Add to Inventory")

        if submitted:
            # Validation check
            if not sku.strip():
                st.error("❌ SKU is required.")
            elif not name.strip():
                st.error("❌ Product Name is required.")
            elif price <= 0:
                st.error("❌ Unit Price must be greater than 0.")
            elif qty <= 0:
                st.error("❌ Quantity must be greater than 0.")
            else:
                # Proceed if valid
                existing = supabase.table("inventory").select("*").eq("sku", sku).execute()
                if existing.data:
                    new_qty = existing.data[0]["total_unit"] + qty
                    supabase.table("inventory").update(
                        {"total_unit": new_qty, "unit_price": price, "product_name": name}
                    ).eq("sku", sku).execute()
                    st.success(f"✅ Updated {name} stock to {new_qty}")
                else:
                    supabase.table("inventory").insert({
                        "sku": sku,
                        "product_name": name,
                        "unit_price": price,
                        "total_unit": qty
                    }).execute()
                    st.success(f"✅ Added {qty} units of {name}")


# ---------------- SELL ----------------
elif page == "Sell":
    st.header("🛒 Sell Products")
    search = st.text_input("Search product by name or SKU")
    if search:
        results = supabase.table("inventory").select("*").ilike("product_name", f"%{search}%").execute()
        if results.data:
            for item in results.data:
                st.write(
                    f"**{item['product_name']}** (SKU: {item['sku']}) | Price: {item['unit_price']} | Stock: {item['total_unit']}")
                qty = st.number_input(f"Quantity for {item['sku']}", 0, item['total_unit'], key=f"qty_{item['sku']}")
                if st.button(f"Add {item['sku']} to cart"):
                    if "cart" not in st.session_state:
                        st.session_state.cart = []
                    st.session_state.cart.append({
                        "sku": item["sku"],
                        "product_name": item["product_name"],
                        "unit_price": item["unit_price"],
                        "qty": qty
                    })
                    st.success(f"Added {qty} units of {item['product_name']} to cart")
        else:
            st.info("No matching products found.")

    # Show cart
    if "cart" in st.session_state and st.session_state.cart:
        st.subheader("🛒 Cart")
        total = 0
        for c in st.session_state.cart:
            st.write(f"{c['product_name']} x {c['qty']} @ {c['unit_price']} = {c['qty'] * c['unit_price']}")
            total += c["qty"] * c["unit_price"]
        st.write(f"**Total: {total}**")
        if st.button("Checkout"):
            for c in st.session_state.cart:
                # Update stock
                inv = supabase.table("inventory").select("*").eq("sku", c["sku"]).execute()
                if inv.data:
                    new_qty = inv.data[0]["total_unit"] - c["qty"]
                    supabase.table("inventory").update({"total_unit": new_qty}).eq("sku", c["sku"]).execute()

                # Record sale
                supabase.table("sold").insert({
                    "sku": c["sku"],
                    "product_name": c["product_name"],
                    "unit_price": c["unit_price"],
                    "total_unit": c["qty"],
                    "accrued": False
                }).execute()
            st.success("Sale completed ✅")
            st.session_state.cart = []

# ---------------- ACCRUAL ----------------
elif page == "Accrual":
    st.header("🧾 Accrual Purchase")
    customer_name = st.text_input("Customer Name / ID")
    search = st.text_input("Search product for accrual")

    if search:
        results = supabase.table("inventory").select("*").ilike("product_name", f"%{search}%").execute()
        if results.data:
            for item in results.data:
                qty = st.number_input(f"Qty for {item['product_name']}", 0, item['total_unit'],
                                      key=f"accrual_{item['sku']}")
                if st.button(f"Add {item['sku']} (Accrual)"):
                    if "cart_acc" not in st.session_state:
                        st.session_state.cart_acc = []
                    st.session_state.cart_acc.append({
                        "sku": item["sku"],
                        "product_name": item["product_name"],
                        "unit_price": item["unit_price"],
                        "qty": qty
                    })
                    st.success(f"Added {qty} units of {item['product_name']} to accrual cart")

    if "cart_acc" in st.session_state and st.session_state.cart_acc:
        st.subheader("Accrual Cart")
        total = 0
        for c in st.session_state.cart_acc:
            st.write(f"{c['product_name']} x {c['qty']} = {c['qty'] * c['unit_price']}")
            total += c["qty"] * c["unit_price"]
        st.write(f"**Total: {total}**")
        if st.button("Checkout Accrual"):
            for c in st.session_state.cart_acc:
                inv = supabase.table("inventory").select("*").eq("sku", c["sku"]).execute()
                if inv.data:
                    new_qty = inv.data[0]["total_unit"] - c["qty"]
                    supabase.table("inventory").update({"total_unit": new_qty}).eq("sku", c["sku"]).execute()
                supabase.table("sold").insert({
                    "sku": c["sku"],
                    "product_name": c["product_name"],
                    "unit_price": c["unit_price"],
                    "total_unit": c["qty"],
                    "accrued": True,
                    "accrued_name": customer_name
                }).execute()
            st.success("Accrual sale recorded ✅")
            st.session_state.cart_acc = []

# ---------------- REPORTS ----------------
elif page == "Reports":
    st.header("📊 Reports")
    inv = supabase.table("inventory").select("*").execute()
    st.subheader("Current Inventory")
    st.dataframe(inv.data)

    sales = supabase.table("sold").select("*").execute()
    st.subheader("Sales Records")
    st.dataframe(sales.data)
