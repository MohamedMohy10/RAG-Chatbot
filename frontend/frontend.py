import streamlit as st
import requests

st.set_page_config(page_title="📄 PDF Q&A Chatbot", page_icon="🤖")
st.title("📄 PDF Q&A Chatbot")

# -----------------------
# Session state setup
# -----------------------
if "pdf_chats" not in st.session_state:
    st.session_state.pdf_chats = {}  # {pdf_filename: [{"role":..., "text":...}, ...]}
if "current_pdf" not in st.session_state:
    st.session_state.current_pdf = None

# -----------------------
# Upload PDF
# -----------------------
uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file:
    files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
    try:
        res = requests.post("http://127.0.0.1:8000/upload_pdf", files=files)
        data = res.json()
        if "filename" in data:
            pdf_filename = data["filename"]
            st.session_state.current_pdf = pdf_filename
            if pdf_filename not in st.session_state.pdf_chats:
                st.session_state.pdf_chats[pdf_filename] = []
            st.success(f"Uploaded {pdf_filename}")
        else:
            st.error(data.get("error", "Upload failed"))
    except Exception as e:
        st.error(f"Could not connect to backend: {e}")
        st.stop()

# -----------------------
# Sidebar: select PDF and show info
# -----------------------
if st.session_state.pdf_chats:
    with st.sidebar:
        st.markdown("### 📁 Select PDF")
        pdf_list = list(st.session_state.pdf_chats.keys())
        selected_pdf = st.selectbox("Choose PDF", pdf_list, index=pdf_list.index(st.session_state.current_pdf) if st.session_state.current_pdf in pdf_list else 0)
        st.session_state.current_pdf = selected_pdf
        st.markdown("---")
        st.markdown(f"**Current PDF:** {st.session_state.current_pdf}")
        st.markdown(f"**Messages:** {len(st.session_state.pdf_chats[st.session_state.current_pdf])}")

# -----------------------
# Input question
# -----------------------
if st.session_state.current_pdf:
    question = st.text_input("Ask a question about this PDF:")

    if st.button("Ask") and question:
        try:
            res = requests.post(
                "http://127.0.0.1:8000/ask",
                data={"question": question, "pdf_filename": st.session_state.current_pdf}
            )
            data = res.json()

            if "answer" in data:
                st.session_state.pdf_chats[st.session_state.current_pdf].append({"role": "user", "text": question})
                st.session_state.pdf_chats[st.session_state.current_pdf].append({"role": "ai", "text": data["answer"]})
            else:
                st.error(data.get("error", "Something went wrong"))

        except Exception as e:
            st.error(f"Could not connect to backend: {e}")

# -----------------------
# Display chat history
# -----------------------
if st.session_state.current_pdf and st.session_state.current_pdf in st.session_state.pdf_chats:
    st.markdown("---")
    st.markdown("### 💬 Chat History")
    for msg in st.session_state.pdf_chats[st.session_state.current_pdf]:
        if msg["role"] == "user":
            st.markdown(f"**You:** {msg['text']}")
        else:
            st.markdown(f"**AI:** {msg['text']}")