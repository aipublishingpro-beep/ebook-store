import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import stripe
import io
import docx2txt
import base64

st.set_page_config(page_title="William Liu Books", layout="wide")

FOLDER_ID = st.secrets["google"]["folder_id"]
STRIPE_SECRET = st.secrets["stripe"]["secret_key"]
STRIPE_PUBLIC = st.secrets["stripe"]["public_key"]
SUCCESS_URL = st.secrets["stripe"]["success_url"]
CANCEL_URL = st.secrets["stripe"]["cancel_url"]

stripe.api_key = STRIPE_SECRET

@st.cache_resource
def get_drive_service():
    creds_dict = {
        "type": st.secrets["google"]["type"],
        "project_id": st.secrets["google"]["project_id"],
        "private_key_id": st.secrets["google"]["private_key_id"],
        "private_key": st.secrets["google"]["private_key"],
        "client_email": st.secrets["google"]["client_email"],
        "client_id": st.secrets["google"]["client_id"],
        "auth_uri": st.secrets["google"]["auth_uri"],
        "token_uri": st.secrets["google"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["google"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["google"]["client_x509_cert_url"]
    }
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=creds)

PRICE_CENTS = 499
PRICE_DISPLAY = "$4.99"

def normalize_name(name):
    n = name.lower()
    n = n.replace(" ebook", "").replace(" paper", "").replace(" new", "")
    n = n.replace("-", " ").replace("_", " ")
    n = " ".join(n.split())
    return n

@st.cache_data(ttl=3600)
def get_all_files(_service):
    books = {}
    covers = {}
    folders_to_search = [FOLDER_ID]
    
    while folders_to_search:
        current_folder = folders_to_search.pop()
        query = f"'{current_folder}' in parents and trashed=false"
        page_token = None
        folder_books = {}
        folder_images = {}
        
        while True:
            results = _service.files().list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType)",
                pageToken=page_token,
                pageSize=1000
            ).execute()
            
            for f in results.get("files", []):
                name = f["name"]
                mime = f.get("mimeType", "")
                
                if mime == "application/vnd.google-apps.folder":
                    folders_to_search.append(f["id"])
                elif name.upper().endswith("EBOOK.DOCX"):
                    title = name[:-5]
                    books[title] = f["id"]
                    normalized = normalize_name(title)
                    folder_books[normalized] = title
                elif name.lower().endswith(".jpg") or name.lower().endswith(".png"):
                    base = name.rsplit(".", 1)[0]
                    normalized = normalize_name(base)
                    folder_images[normalized] = f["id"]
            
            page_token = results.get("nextPageToken")
            if not page_token:
                break
        
        for norm_title, full_title in folder_books.items():
            best_match = None
            for norm_img, img_id in folder_images.items():
                if norm_title in norm_img or norm_img in norm_title:
                    best_match = img_id
                    break
            if best_match:
                covers[full_title] = best_match
            elif folder_images:
                covers[full_title] = list(folder_images.values())[0]
    
    return books, covers

def download_file(service, file_id):
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buffer.seek(0)
    return buffer

def get_description(service, file_id):
    try:
        buffer = download_file(service, file_id)
        text = docx2txt.process(buffer)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        found = False
        for p in paragraphs:
            l = p.lower()
            if any(k in l for k in ["chapter", "introduction", "prologue"]):
                found = True
                continue
            if found and len(p) > 100:
                if any(bad in l for bad in ["copyright", "all rights reserved", "reproduced"]):
                    continue
                return p[:300] + "..."
        return "A compelling read by William Liu."
    except:
        return "A compelling read by William Liu."

@st.cache_data(ttl=3600)
def get_cover_base64(_service, file_id):
    try:
        buffer = download_file(_service, file_id)
        return base64.b64encode(buffer.read()).decode()
    except:
        return None

def create_checkout_session(title, price_cents, book_id):
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": title},
                "unit_amount": price_cents,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=SUCCESS_URL + f"?book={book_id}",
        cancel_url=CANCEL_URL,
        metadata={"book_title": title, "book_id": book_id}
    )
    return session.url

def main():
    if 'descriptions' not in st.session_state:
        st.session_state.descriptions = {}
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    
    st.title("📚 William Liu Books")
    st.markdown("---")
    
    service = get_drive_service()
    books, covers = get_all_files(service)
    
    search = st.text_input("🔍 Search books", "")
    
    # Reset page when search changes
    if 'last_search' not in st.session_state:
        st.session_state.last_search = ""
    if search != st.session_state.last_search:
        st.session_state.current_page = 1
        st.session_state.last_search = search
    
    filtered_books = {}
    for title, file_id in books.items():
        if search.lower() and search.lower() not in title.lower():
            continue
        filtered_books[title] = file_id
    
    titles = sorted(filtered_books.keys())
    cols_per_row = 4
    books_per_page = 12
    
    total_pages = max(1, (len(titles) + books_per_page - 1) // books_per_page)
    page = st.session_state.current_page
    
    start_idx = (page - 1) * books_per_page
    end_idx = start_idx + books_per_page
    page_titles = titles[start_idx:end_idx]
    
    st.markdown(f"**Showing {len(page_titles)} of {len(filtered_books)} books** | Page {page} of {total_pages}")
    st.markdown("---")
    
    for i in range(0, len(page_titles), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(page_titles):
                break
            title = page_titles[idx]
            file_id = filtered_books[title]
            
            with col:
                cover_id = covers.get(title)
                if cover_id:
                    img_b64 = get_cover_base64(service, cover_id)
                    if img_b64:
                        st.markdown(
                            f'<img src="data:image/*;base64,{img_b64}" style="width:100%;border-radius:8px;">',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown("📖", unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<div style="width:100%;height:200px;background:#333;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:48px;">📖</div>',
                        unsafe_allow_html=True
                    )
                
                st.markdown(f"**{title}**")
                st.caption(PRICE_DISPLAY)
                
                with st.expander("Description"):
                    desc_key = f"desc_{file_id}"
                    if desc_key in st.session_state.descriptions:
                        st.write(st.session_state.descriptions[desc_key])
                    else:
                        if st.button("Load Description", key=f"load_{file_id}"):
                            with st.spinner("Loading..."):
                                desc = get_description(service, file_id)
                                st.session_state.descriptions[desc_key] = desc
                                st.rerun()
                        else:
                            st.write("Click to load description")
                
                if st.button(f"Buy {PRICE_DISPLAY}", key=f"buy_{file_id}"):
                    checkout_url = create_checkout_session(title, PRICE_CENTS, file_id)
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={checkout_url}">', unsafe_allow_html=True)
                    st.write(f"[Click here if not redirected]({checkout_url})")
    
    st.markdown("---")
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if page > 1:
            if st.button("⬅️ Previous Page", use_container_width=True):
                st.session_state.current_page -= 1
                st.rerun()
    
    with col2:
        st.markdown(f"<center>Page {page} of {total_pages}</center>", unsafe_allow_html=True)
    
    with col3:
        if page < total_pages:
            if st.button("Next Page ➡️", use_container_width=True):
                st.session_state.current_page += 1
                st.rerun()

if __name__ == "__main__":
    main()
