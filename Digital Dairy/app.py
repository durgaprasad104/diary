import streamlit as st
import datetime
from firebase_config import db, auth
from firebase_admin import firestore
from collections import defaultdict
from PIL import Image
import io
import base64
import json

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None
if 'selected_month' not in st.session_state:
    st.session_state.selected_month = None
if 'current_entry' not in st.session_state:
    st.session_state.current_entry = None
if 'uploaded_image' not in st.session_state:
    st.session_state.uploaded_image = None
if 'viewing_entry' not in st.session_state:
    st.session_state.viewing_entry = None
if 'entry_to_delete' not in st.session_state:
    st.session_state.entry_to_delete = None
if 'refresh_sidebar' not in st.session_state:
    st.session_state.refresh_sidebar = False

# Custom CSS
st.markdown("""
<style>
    /* Main text area */
    .stTextArea textarea {
        min-height: 300px;
        border-radius: 8px;
        padding: 12px;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
        padding: 1rem;
    }
    
    /* Formatting buttons */
    .format-buttons {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
    }
    .format-btn {
        flex: 1;
        border-radius: 8px;
        padding: 8px 0;
    }
    
    /* Entry buttons */
    .entry-button {
        margin-bottom: 8px;
        width: 100%;
        text-align: left;
        border-radius: 8px;
        padding: 8px 12px;
    }
    
    /* Compact image uploader */
    .compact-uploader {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px;
        background-color: #f8f9fa;
        margin-bottom: 16px;
    }
    .compact-uploader:hover {
        border-color: #4e8cff;
        background-color: #f5f9ff;
    }
    .upload-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
    }
    .upload-icon {
        font-size: 1.2rem;
    }
    .file-info {
        font-size: 0.8rem;
        color: #666;
    }
    
    /* Diary entry cards */
    .entry-card {
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        background-color: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    /* Delete button */
    .delete-btn {
        background-color: #ffebee !important;
        color: #c62828 !important;
        border-color: #ef9a9a !important;
    }
    
    /* Download button */
    .download-btn {
        background-color: #e3f2fd !important;
        color: #1565c0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Main App
st.title("📖 Digital Diary")

# ===== AUTHENTICATION =====
def auth_form():
    st.subheader("Login / Signup")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login", use_container_width=True):
            try:
                user = auth.get_user_by_email(email)
                st.session_state.user = email
                st.success("Logged in successfully!")
                st.rerun()
            except Exception as e:
                st.error("Login failed. Please check your credentials.")
    
    with col2:
        if st.button("Sign Up", use_container_width=True):
            try:
                user = auth.create_user(email=email, password=password)
                st.session_state.user = email
                st.success("Account created! You're now logged in.")
                st.rerun()
            except Exception as e:
                st.error(f"Signup failed: {str(e)}")

if not st.session_state.user:
    auth_form()
else:
    st.write(f"Welcome, {st.session_state.user}!")
    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()

# ===== DIARY FUNCTIONALITY =====
if st.session_state.user:
    user_id = st.session_state.user.replace("@", "_").replace(".", "_")
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    
    # ===== RICH TEXT EDITOR =====
    st.subheader(f"Today's Diary Entry ({today})")
    
    # Formatting buttons
    st.markdown('<div class="format-buttons">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("• Bullet Points", key="bullet_btn", use_container_width=True, help="Add bullet points"):
            st.session_state.current_entry = (st.session_state.current_entry or "") + "\n• "
    with col2:
        if st.button("¶ Paragraph", key="paragraph_btn", use_container_width=True, help="Add paragraph break"):
            st.session_state.current_entry = (st.session_state.current_entry or "") + "\n\n"
    with col3:
        if st.button("― Divider", key="divider_btn", use_container_width=True, help="Add horizontal divider"):
            st.session_state.current_entry = (st.session_state.current_entry or "") + "\n---\n"
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ===== COMPACT IMAGE UPLOAD =====
    with st.container():
        st.markdown("""
        <div class="compact-uploader">
            <div class="upload-header">
                <span class="upload-icon">📷</span>
                <strong>Add Image to Entry</strong>
            </div>
            <div class="file-info">Supports: PNG, JPG, JPEG | Max 200MB</div>
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_image = st.file_uploader(
            "Choose an image",
            type=["png", "jpg", "jpeg"],
            key="image_uploader",
            label_visibility="collapsed"
        )
        
        if uploaded_image:
            st.session_state.uploaded_image = uploaded_image
            with st.expander("🖼️ Image Preview", expanded=False):
                st.image(uploaded_image, use_container_width=True)
    
    # Text area
    entry = st.text_area(
        "Write your thoughts...", 
        value=st.session_state.current_entry or "",
        height=300,
        key="diary_entry",
        placeholder="Start writing your thoughts here..."
    )
    st.session_state.current_entry = entry
    
    # Save entry - Only enabled if there's content or image
    save_disabled = not (entry.strip() or st.session_state.uploaded_image)
    if st.button("💾 Save Entry", use_container_width=True, disabled=save_disabled):
        # Create a unique document ID with timestamp
        entry_id = f"{today}_{current_time.replace(':', '-')}"
        diary_ref = db.collection("diaries").document(user_id).collection("entries").document(entry_id)
        
        entry_data = {
            "date": today,
            "content": entry,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "month_year": datetime.datetime.now().strftime("%Y-%m"),
            "entry_time": current_time,
            "entry_id": entry_id
        }
        
        if st.session_state.uploaded_image:
            image_bytes = st.session_state.uploaded_image.read()
            b64_image = base64.b64encode(image_bytes).decode()
            entry_data["image"] = b64_image
            entry_data["image_type"] = st.session_state.uploaded_image.type
        
        diary_ref.set(entry_data)
        st.success("Entry saved successfully! 🎉")
        
        # Clear inputs
        st.session_state.current_entry = None
        st.session_state.uploaded_image = None
        st.session_state.refresh_sidebar = True
        
        # Refresh the page
        st.rerun()

    # ===== SIDEBAR: PAST ENTRIES =====
    st.sidebar.title("📚 Past Entries")
    
    @st.cache_data(ttl=60)  # Cache for 1 minute
    def get_user_entries(user_id):
        entries_ref = db.collection("diaries").document(user_id).collection("entries")
        entries = entries_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
        return [entry.to_dict() for entry in entries]
    
    if st.session_state.refresh_sidebar:
        get_user_entries.clear()
        st.session_state.refresh_sidebar = False
    
    all_entries = get_user_entries(user_id)
    
    # Organize entries by month and day
    month_entries = defaultdict(list)
    day_entries = defaultdict(list)
    
    for entry in all_entries:
        month_year = entry.get("month_year", entry["date"][:7])
        month_entries[month_year].append(entry)
        day_entries[entry["date"]].append(entry)
    
    sorted_months = sorted(month_entries.keys(), reverse=True)
    
    selected_month = st.sidebar.selectbox(
        "Select Month",
        sorted_months,
        index=0 if not st.session_state.selected_month else sorted_months.index(st.session_state.selected_month)
    )
    st.session_state.selected_month = selected_month
    
    st.sidebar.subheader(f"🗓️ {selected_month}")
    
    # Group entries by day
    for day, entries in sorted(day_entries.items(), reverse=True):
        if day.startswith(selected_month):
            with st.sidebar.expander(f"📅 {day}", expanded=False):
                for idx, entry in enumerate(entries, 1):
                    entry_time = entry.get('entry_time', entry['timestamp'].split(' ')[1][:8])
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if st.button(
                            f"✏️ Entry {idx} - {entry_time}",
                            key=f"view_{day}_{idx}_{entry_time}",
                            help="Click to view this entry",
                            use_container_width=True
                        ):
                            st.session_state.viewing_entry = entry
                            st.rerun()
                    with col2:
                        # Prepare download data
                        download_data = {
                            "date": entry["date"],
                            "time": entry_time,
                            "content": entry["content"],
                            "timestamp": entry["timestamp"]
                        }
                        if "image" in entry:
                            download_data["image_base64"] = entry["image"]
                        
                        json_str = json.dumps(download_data, indent=2)
                        st.download_button(
                            label="⬇️",
                            data=json_str,
                            file_name=f"diary_{entry['date']}_{idx}.json",
                            mime="application/json",
                            key=f"dl_{day}_{idx}_{entry_time}",
                            use_container_width=True,
                            help="Download this entry"
                        )
    
    # Display selected entry in main area
    if st.session_state.viewing_entry:
        entry = st.session_state.viewing_entry
        entry_time = entry.get('entry_time', entry['timestamp'].split(' ')[1][:8])
        
        with st.container():
            st.markdown(f"""
            <div class="entry-card">
                <h3>📝 Entry from {entry['date']} at {entry_time}</h3>
                <div style="margin: 1rem 0;">{entry["content"].replace('\n', '<br>')}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if "image" in entry:
                try:
                    image_data = base64.b64decode(entry["image"])
                    st.image(Image.open(io.BytesIO(image_data)), 
                            caption=f"📷 Image from {entry['date']}",
                            use_container_width=True)
                except:
                    st.warning("Could not load image")
            
            st.caption(f"🕒 Last saved: {entry['timestamp']}")
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            with col1:
                # Download button
                download_data = {
                    "date": entry["date"],
                    "time": entry_time,
                    "content": entry["content"],
                    "timestamp": entry["timestamp"]
                }
                if "image" in entry:
                    download_data["image_base64"] = entry["image"]
                
                json_str = json.dumps(download_data, indent=2)
                st.download_button(
                    label="📥 Download Entry",
                    data=json_str,
                    file_name=f"diary_{entry['date']}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="main_download"
                )
            
            with col2:
                # Delete button
                if st.button("🗑️ Delete Entry", 
                            key="delete_entry", 
                            use_container_width=True,
                            type="primary"):
                    st.session_state.entry_to_delete = entry.get('entry_id')
            
            # Delete confirmation
            if st.session_state.entry_to_delete:
                with st.form("confirm_delete"):
                    st.warning("Are you sure you want to permanently delete this entry?")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("✅ Yes, Delete", 
                                               use_container_width=True,
                                               type="primary"):
                            db.collection("diaries").document(user_id)\
                              .collection("entries").document(st.session_state.entry_to_delete).delete()
                            st.success("Entry deleted successfully!")
                            st.session_state.refresh_sidebar = True
                            st.session_state.viewing_entry = None
                            st.session_state.entry_to_delete = None
                            st.rerun()
                    with col2:
                        if st.form_submit_button("❌ Cancel", 
                                               use_container_width=True):
                            st.session_state.entry_to_delete = None
                            st.rerun()
            
            if st.button("← Back to Writing", use_container_width=True):
                st.session_state.viewing_entry = None
                st.session_state.current_entry = None
                st.rerun()