import streamlit as st
import json, os, math

# ── Config ──
CATALOG_DIR = "catalog"
STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
SUCCESS_URL = os.environ.get("SUCCESS_URL", "https://your-app.streamlit.app/?success=true&book={CHECKOUT_SESSION_ID}")
CANCEL_URL = os.environ.get("CANCEL_URL", "https://your-app.streamlit.app/?canceled=true")

st.set_page_config(page_title="William Liu Books", page_icon="📚", layout="wide")

# ── Custom CSS ──
st.markdown("""
<style>
.book-card { 
    border: 1px solid #333; border-radius: 10px; 
    padding: 12px; margin-bottom: 12px; 
    background: #1a1a2e; text-align: center; 
}
.book-title { font-size: 14px; font-weight: bold; margin: 8px 0 4px; }
.book-desc { font-size: 12px; color: #aaa; margin-bottom: 8px; }
.book-price { font-size: 16px; font-weight: bold; color: #00d4aa; }
</style>
""", unsafe_allow_html=True)

# ── Load manifest ──
@st.cache_data
def load_manifest():
    with open(os.path.join(CATALOG_DIR, "manifest.json"), "r") as f:
        return json.load(f)

# ── Load single page ──
@st.cache_data
def load_page(page_num):
    path = os.path.join(CATALOG_DIR, f"page_{page_num}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

manifest = load_manifest()
total_pages = manifest.get("total_pages", 1)
total_books = manifest.get("total_books", 0)
categories = manifest.get("categories", {})

# ── Handle Stripe success ──
params = st.query_params
if params.get("success") == "true":
    st.success("✅ Purchase complete! Your download link is below.")
    session_id = params.get("book", "")
    if session_id and STRIPE_KEY:
        try:
            import stripe
            stripe.api_key = STRIPE_KEY
            session = stripe.checkout.Session.retrieve(session_id)
            ebook_id = session.metadata.get("ebook_id", "")
            title = session.metadata.get("title", "Your Book")
            if ebook_id:
                dl = f"https://drive.google.com/uc?id={ebook_id}&export=download"
                st.markdown(f"### 📖 Download: [{title}]({dl})")
            else:
                st.warning("Could not retrieve download link. Contact support.")
        except Exception as e:
            st.error(f"Error retrieving session: {e}")
    st.stop()

if params.get("canceled") == "true":
    st.warning("Purchase canceled. You were not charged.")

# ── Header ──
st.title("📚 William Liu Books")
st.caption(f"{total_books} books available")

# ── Category filter (top of page) ──
all_cats = ["All"] + sorted(categories.keys())
selected_cat = st.radio(
    "Browse by category",
    all_cats,
    horizontal=True,
    index=0
)

# ── Sidebar ──
st.sidebar.header("📖 Navigation")
page = st.sidebar.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
st.sidebar.caption(f"Page {page} of {total_pages}")
search = st.sidebar.text_input("🔍 Search", "").strip().lower()

# ── Load selected page ──
books = load_page(page)

# ── Apply category filter ──
if selected_cat != "All":
    books = [b for b in books if b.get("category", "Fiction") == selected_cat]

# ── Apply search filter ──
if search:
    books = [b for b in books if
             search in b.get("title", "").lower() or
             search in b.get("description", "").lower()]
    st.info(f"Found {len(books)} results on page {page} for '{search}'")

# ── Display grid ──
if not books:
    st.info("No books on this page matching your filters. Try another page or category.")
else:
    COLS = 4
    rows = [books[i:i + COLS] for i in range(0, len(books), COLS)]

    for row in rows:
        cols = st.columns(COLS)
        for idx, book in enumerate(row):
            with cols[idx]:
                cover = book.get("cover_url", "")
                title = book.get("title", "Untitled")
                desc = book.get("description", "")
                price = book.get("price", 4.99)
                ebook_id = book.get("ebook_id", "")
                cat = book.get("category", "")

                if cover:
                    st.image(cover, use_container_width=True)
                else:
                    st.markdown("📕")

                st.markdown(f"**{title}**")

                if cat:
                    st.caption(f"📂 {cat}")

                if desc:
                    short = desc[:120] + "..." if len(desc) > 120 else desc
                    st.caption(short)

                st.markdown(f"💰 **${price:.2f}**")

                btn_key = f"buy_{page}_{idx}_{ebook_id}"
                if st.button("Buy Now", key=btn_key):
                    if not STRIPE_KEY:
                        st.error("Stripe not configured.")
                    else:
                        try:
                            import stripe
                            stripe.api_key = STRIPE_KEY
                            session = stripe.checkout.Session.create(
                                payment_method_types=["card"],
                                line_items=[{
                                    "price_data": {
                                        "currency": "usd",
                                        "product_data": {"name": title},
                                        "unit_amount": int(price * 100),
                                    },
                                    "quantity": 1,
                                }],
                                mode="payment",
                                success_url=SUCCESS_URL,
                                cancel_url=CANCEL_URL,
                                metadata={
                                    "ebook_id": ebook_id,
                                    "title": title,
                                },
                            )
                            st.markdown(
                                f'<meta http-equiv="refresh" content="0;url={session.url}">',
                                unsafe_allow_html=True
                            )
                        except Exception as e:
                            st.error(f"Checkout error: {e}")

# ── Bottom nav ──
st.divider()
c1, c2, c3 = st.columns([1, 2, 1])
with c1:
    if page > 1:
        st.markdown(f"⬅️ Previous: change page to {page - 1} in sidebar")
with c2:
    st.caption(f"Page {page} of {total_pages} • {total_books} books")
with c3:
    if page < total_pages:
        st.markdown(f"Next: change page to {page + 1} in sidebar ➡️")
