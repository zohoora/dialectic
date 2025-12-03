"""
File upload component for the AI Case Conference UI.

Provides a file uploader for adding documents to be analyzed by the Librarian.
"""

import streamlit as st

from src.models.librarian import LibrarianFile, LibrarianSummary


# Supported file types
SUPPORTED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".txt", ".md", ".csv"]
MAX_FILE_SIZE_MB = 20
MAX_FILES = 10


def render_file_upload() -> list[LibrarianFile]:
    """
    Render the file upload widget.
    
    Returns:
        List of LibrarianFile objects from uploaded files.
    """
    st.markdown(
        '<p style="color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase; '
        'letter-spacing: 0.08em; margin-bottom: 0.5rem;">Supporting Documents (optional)</p>',
        unsafe_allow_html=True
    )
    
    uploaded_files = st.file_uploader(
        "Upload documents",
        type=["pdf", "png", "jpg", "jpeg", "gif", "webp", "txt", "md", "csv"],
        accept_multiple_files=True,
        help=f"Upload documents for the Librarian to analyze. Supports PDF, images, and text files. Max {MAX_FILES} files, {MAX_FILE_SIZE_MB}MB each.",
        label_visibility="collapsed",
    )
    
    librarian_files = []
    
    if uploaded_files:
        # Limit number of files
        if len(uploaded_files) > MAX_FILES:
            st.warning(f"⚠️ Maximum {MAX_FILES} files allowed. Only the first {MAX_FILES} will be processed.")
            uploaded_files = uploaded_files[:MAX_FILES]
        
        # Process uploaded files
        for uploaded_file in uploaded_files:
            # Check file size
            file_size_mb = uploaded_file.size / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                st.warning(f"⚠️ {uploaded_file.name} is too large ({file_size_mb:.1f}MB). Maximum size is {MAX_FILE_SIZE_MB}MB.")
                continue
            
            # Read content
            content = uploaded_file.read()
            uploaded_file.seek(0)  # Reset for potential re-read
            
            # Create LibrarianFile
            librarian_file = LibrarianFile.from_upload(
                filename=uploaded_file.name,
                content=content,
                mime_type=uploaded_file.type or "",
            )
            librarian_files.append(librarian_file)
        
        # Show uploaded files summary
        if librarian_files:
            file_info = ", ".join([f.filename for f in librarian_files])
            total_size_kb = sum(f.size_bytes for f in librarian_files) / 1024
            st.caption(f"📎 {len(librarian_files)} file(s): {file_info} ({total_size_kb:.1f} KB total)")
    
    return librarian_files


def render_librarian_summary(summary: LibrarianSummary):
    """
    Render the Librarian's document summary.
    
    Args:
        summary: The LibrarianSummary to display.
    """
    if not summary or not summary.summary:
        return
    
    st.markdown(
        '<div style="margin-top: 1rem;">'
        '<h4 style="color: var(--text-primary); font-weight: 600; margin-bottom: 0.5rem;">'
        '📚 Document Analysis</h4>'
        '</div>',
        unsafe_allow_html=True
    )
    
    # File manifest
    if summary.file_manifest:
        with st.expander("📄 Document Manifest", expanded=False):
            for entry in summary.file_manifest:
                size_kb = entry.size_bytes / 1024
                icon = _get_file_icon(entry.file_type.value)
                st.markdown(f"{icon} **{entry.filename}** ({size_kb:.1f} KB)")
    
    # Summary content
    with st.expander("📋 Summary", expanded=True):
        st.markdown(summary.summary)
    
    # Key findings
    if summary.key_findings:
        with st.expander("🔍 Key Findings", expanded=False):
            for finding in summary.key_findings:
                st.markdown(f"• {finding}")
    
    # Token usage
    if summary.input_tokens or summary.output_tokens:
        st.caption(
            f"Librarian: {summary.input_tokens:,} input tokens, "
            f"{summary.output_tokens:,} output tokens"
        )


def _get_file_icon(file_type: str) -> str:
    """Get an icon for a file type."""
    icons = {
        "pdf": "📕",
        "image": "🖼️",
        "text": "📄",
        "unknown": "📎",
    }
    return icons.get(file_type, "📎")

