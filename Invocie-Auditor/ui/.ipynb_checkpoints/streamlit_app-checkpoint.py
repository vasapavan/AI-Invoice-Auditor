import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import json
import sys
import threading

# --- Imports ---
sys.path.append(str(Path(__file__).parent.parent))
from workflow.invoice_workflow import InvoiceAuditorWorkflow
from agents.monitor_agent import MonitorAgent

# --- Page Config ---
st.set_page_config(
    page_title="AI Invoice Auditor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed" # Helps prevent sidebar flash on load
)

# --- Custom Styles (Light Theme + Glassmorphism + Navbar Tabs) ---
# --- Custom Styles (Curvy, Deep Blue, Aligned Theme) ---
# --- Custom Styles (Curvy, Sky Blue Theme) ---
def apply_custom_styles():
    st.markdown(
        """
        <style>
        /* ----------------------------------- */
        /* 0. BASE APP (Modular, no global overrides!) */
        /* ----------------------------------- */
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] { display: none !important; }

        .stApp { 
            background-color: #F8FAFC !important; 
            font-family: 'Inter', 'Segoe UI', Roboto, sans-serif !important;
        }

        /* ----------------------------------- */
        /* 1. THE BIG HEADER BLOCK             */
        /* ----------------------------------- */
        .glass-header {
            background: #0077b6 !important; 
            border: none !important; 
            border-radius: 100px !important; 
            padding: 3rem !important;
            margin-bottom: 2rem;
            text-align: center;
        }
        .glass-header h1 { 
            color: #FFFFFF !important; 
            font-weight: 800 !important; 
            font-size: 2.8rem !important; 
            margin-bottom: 0.5rem; 
            text-shadow: none !important; 
        }
        .glass-header p { 
            color: #E0F2FE !important; 
            font-size: 1.2rem !important; 
            margin-bottom: 0; 
            font-weight: 500;
        }

        /* ----------------------------------- */
        /* 2. THE NAVBAR (TABS)                */
        /* ----------------------------------- */
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            background-color: #FFFFFF !important; 
            padding: 0.5rem !important;
            border-radius: 16px !important; 
            gap: 0.5rem !important;
            margin-bottom: 2rem;
            border: 1px solid #E2E8F0 !important; 
            display: flex !important;
            width: 100% !important; 
        }
        div[data-testid="stTabs"] [data-baseweb="tab"] {
            background-color: #8ecae6 !important; 
            border-radius: 12px !important; 
            min-height: 4rem !important; 
            flex: 1 1 0px !important; 
            display: flex !important;
            justify-content: center !important; 
            align-items: center !important;
            border: none !important;
        }
        /* Target all text elements strictly inside the tabs */
        div[data-testid="stTabs"] [data-baseweb="tab"] * {
            font-family: 'Montserrat', 'Arial Black', sans-serif !important;
            font-size: 1.5rem !important; 
            font-weight: 800 !important;
            color: #FFFFFF !important; 
            white-space: normal !important;
            text-align: center !important;
        }
        div[data-testid="stTabs"] [aria-selected="true"] {
            background-color: #0077b6 !important; 
        }

        /* ----------------------------------- */
        /* 3. METRIC BLOCKS (Fixed Height)     */
        /* ----------------------------------- */
        [data-testid="stMetric"] {
            background-color: #8ecae6 !important; 
            border-radius: 20px !important; 
            padding: 1.5rem !important;
            border: none !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
            min-height: 150px !important; 
            width: 100% !important;
        }
        /* Target Streamlit's <label> tags for headers (e.g. "Processed Invoices") */
        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] * { 
            font-family: 'Montserrat', 'Arial Black', sans-serif !important;
            font-size: 1.6rem !important; 
            font-weight: 800 !important; 
            color: #FFFFFF !important; 
            white-space: normal !important;
            text-align: center !important;
        }
        /* Target values strictly inside the metric */
        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] * { 
            font-family: 'Montserrat', 'Arial Black', sans-serif !important;
            font-size: 2.2rem !important; 
            font-weight: 800 !important; 
            color: #FFFFFF !important; 
            white-space: normal !important; 
            word-wrap: break-word !important; 
            line-height: 1.2 !important;
            text-align: center !important;
        }

        /* ----------------------------------- */
        /* 4. EXPANDERS & BUTTONS              */
        /* ----------------------------------- */
        div[data-testid="stExpander"] {
            background-color: #FFFFFF !important;
            border-radius: 16px !important; 
            border: 1px solid #E2E8F0 !important;
        }
        div[data-testid="stExpander"] details summary {
            padding: 0.5rem !important;
            transition: background-color 0.2s ease;
        }
        div[data-testid="stExpander"] details summary:hover {
            background-color: #F1F5F9 !important; 
            border-radius: 14px !important;
        }
        /* Only style the paragraph tag so we don't break the SVG arrow icon */
        div[data-testid="stExpander"] details summary p {
            font-family: 'Montserrat', 'Arial Black', sans-serif !important;
            font-size: 1.2rem !important;
            font-weight: 700 !important;
            color: #0F172A !important; 
        }
        
        div.stButton > button {
            background-color: #00509d !important; 
            border-radius: 12px !important; 
            padding: 0.5rem 1.5rem !important;
            font-weight: 700 !important;
            border: none !important;
        }
        div.stButton > button * {
            color: #FFFFFF !important;
            font-size: 1rem !important;
        }

        /* ----------------------------------- */
        /* 5. INPUT BLOCKS & CHAT INPUT        */
        /* ----------------------------------- */
        div[data-baseweb="input"] > div, 
        div[data-baseweb="select"] > div, 
        div[data-baseweb="textarea"] > div,
        div[data-testid="stFileUploaderDropzone"] {
            background-color: #FFFFFF !important; 
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
        }
        /* Make strictly input text black */
        div[data-baseweb="input"] input, 
        div[data-baseweb="textarea"] textarea,
        div[data-testid="stFileUploaderDropzone"] * {
            color: #0F172A !important;
        }

        div[data-testid="stChatInput"] {
            background-color: #E2E8F0 !important; 
            padding: 0.75rem !important;
            border-radius: 12px !important;
            border: 1px solid #CBD5E1 !important;
        }
        div[data-testid="stChatInput"] textarea {
            color: #0F172A !important;
            background-color: #FFFFFF !important; 
            border-radius: 6px !important;
            padding: 0.5rem !important;
        }

        /* ----------------------------------- */
        /* 6. TABLES & DATAFRAMES (Safe)       */
        /* ----------------------------------- */
        div[data-testid="stDataFrame"] {
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
            background-color: #F8FAFC !important;
        }
        div[data-testid="stTable"] {
            overflow-x: auto !important; 
            background-color: #F8FAFC !important;
            border-radius: 8px !important;
            border: 1px solid #CBD5E1 !important;
        }
        div[data-testid="stTable"] table {
            width: 100% !important;
            color: #0F172A !important;
        }
        div[data-testid="stTable"] th {
            background-color: #E2E8F0 !important; 
            color: #0F172A !important;
            font-family: 'Montserrat', 'Arial Black', sans-serif !important;
            font-size: 0.95rem !important;
            padding: 10px !important;
        }
        div[data-testid="stTable"] td {
            border-bottom: 1px solid #E2E8F0 !important;
            padding: 8px !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
apply_custom_styles()
# --- Persistent Queue File ---
NEW_INVOICES_QUEUE = Path("./data/new_invoices_queue.json")

# --- Callback ---
def process_invoice_callback(file_path):
    try:
        if NEW_INVOICES_QUEUE.exists():
            with open(NEW_INVOICES_QUEUE, 'r') as f:
                queue = json.load(f)
        else:
            queue = []
        if file_path not in queue:
            queue.append(file_path)
        NEW_INVOICES_QUEUE.parent.mkdir(parents=True, exist_ok=True)
        with open(NEW_INVOICES_QUEUE, 'w') as f:
            json.dump(queue, f)
    except Exception as e:
        print(f"Error adding to queue: {e}")

# --- Initialize Workflow and Monitor ---
if 'workflow' not in st.session_state:
    st.session_state.workflow = InvoiceAuditorWorkflow()
    st.session_state.processed_results = []
    st.session_state.monitor = MonitorAgent(
        watch_path="./data/incoming",
        callback=process_invoice_callback
    )
    monitor_thread = threading.Thread(target=st.session_state.monitor.start, daemon=True)
    monitor_thread.start()
    st.session_state.monitor_started = True

# --- Header (Glassmorphism) ---
st.markdown(
    """
    <div class="glass-header">
        <h1>📄 AI Invoice Auditor</h1>
        <p>Automated + Human-in-the-loop invoice validation system powered by Infosys & AWS Bedrock</p>
    </div>
    """,
    unsafe_allow_html=True
)
# --- Relocated Sidebar Content (Below Navbar/Tabs) ---
st.markdown("---")
st.header("⚙️ System Status Dashboard")

status_col, queue_col, metric_col1, metric_col2 = st.columns(4)

with status_col:
    st.success("✅ Workflow Ready")
    if st.session_state.get('monitor_started'):
        st.success("📡 File Monitor Active")

with queue_col:
    review_queue = st.session_state.workflow.get_review_queue()
    if review_queue:
        st.warning(f"⏸️ {len(review_queue)} awaiting review")
    else:
        st.info("💡 Ready for new invoices")

with metric_col1:
    rag_stats = st.session_state.workflow.get_rag_pipeline().get_stats()
    st.metric("Processed Invoices", rag_stats['total_documents'])

with metric_col2:
    st.metric("Indexed Chunks", rag_stats['total_chunks'])

# Process queue if present
if NEW_INVOICES_QUEUE.exists():
    try:
        with open(NEW_INVOICES_QUEUE, 'r') as f:
            queue = json.load(f)
        if queue:
            for file_path in queue:
                if Path(file_path).exists():
                    with st.spinner(f"Processing {Path(file_path).name}..."):
                        result = st.session_state.workflow.process_invoice(file_path)
                        st.session_state.processed_results.append(result)
                        st.session_state.current_result = result
            with open(NEW_INVOICES_QUEUE, 'w') as f:
                json.dump([], f)
            st.success(f"✅ Processed {len(queue)} new invoice(s)!")
    except Exception as e:
        st.error(f"Error processing queue: {e}")


# Main content - four tabs
tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload Invoice", "⏸️ Human Review", "📊 Query Bot", "📋 Audit Reports"])

# TAB 1: Upload & Process
with tab1:
    st.header("Upload Invoice")
    
    uploaded_file = st.file_uploader(
        "Choose invoice file (PDF, DOCX, PNG)",
        type=['pdf', 'docx', 'png', 'jpg', 'jpeg']
    )
    
    if uploaded_file:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info(f"📄 File: {uploaded_file.name}")
        
        with col2:
            if st.button("🚀 Process", type="primary", width='stretch'):
                # Save file
                upload_path = Path("./data/uploads") / uploaded_file.name
                upload_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(upload_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Process through workflow
                with st.spinner("Processing through workflow..."):
                    result = st.session_state.workflow.process_invoice(str(upload_path))
                    st.session_state.processed_results.append(result)
                    st.session_state.current_result = result
                
                st.success("✅ Processing Complete!")
                st.rerun()
    
    # Show current result if available
    if 'current_result' in st.session_state and st.session_state.current_result:
        st.markdown("---")
        st.subheader("📋 Processing Results")


        
        
        result = st.session_state.current_result
        invoice_data = result.get('invoice_data', {})
        validation = result.get('validation_result', {})
        
        # --- DYNAMIC TICK BOXES (WORKFLOW STATUS) ---
        st.markdown("**Workflow Progress:**")
        chk1, chk2, chk3, chk4, chk5 = st.columns(5)
        
        with chk1:
            st.checkbox("Monitor Activated", value=True, disabled=True)
        with chk2:
            st.checkbox("Extracted", value=bool(invoice_data), disabled=True)
        with chk3:
            # Ticks only if the workflow flagged it as translated
            st.checkbox("Translated", value=invoice_data.get('was_translated', False), disabled=True)
        with chk4:
            # Ticks only if a human explicitly overrode/verified it
            st.checkbox("Human Verified", value=bool(validation.get('human_override')), disabled=True)
        with chk5:
            # Ticks if the final report text exists
            st.checkbox("Report Generated", value=bool(result.get('report_text')), disabled=True)
            
        st.markdown("---")
        # --------------------------------------------
        
        # Check if paused for review
        


            
        
        result = st.session_state.current_result
        
        # Check if paused for review
        if result.get('status') == 'awaiting_human_review':
            st.warning("⏸️ **This invoice requires human review**")
            st.info("👉 Go to **'Review Queue'** tab to approve/reject and resume workflow")
            
            invoice_data = result.get('invoice_data', {})
            validation = result.get('validation_result', {})
            
            # Show basic info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Invoice No", invoice_data.get('invoice_no', 'N/A'))
            with col2:
                st.metric("Total", f"{invoice_data.get('currency', '')} {invoice_data.get('total_amount', 0)}")
            with col3:
                st.warning("⏸️ PAUSED")
            
            # Show discrepancies
            with st.expander("⚠️ Why it needs review:", expanded=True):
                for disc in validation.get('discrepancies', []):
                    st.warning(f"• {disc.get('message')}")
        
        else:
            # Normal completed workflow results
            invoice_data = result.get('invoice_data', {})
            validation = result.get('validation_result', {})
            
            # Basic info
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Invoice No", invoice_data.get('invoice_no', 'N/A'))
            with col2:
                st.metric("Total", f"{invoice_data.get('currency', '')} {invoice_data.get('total_amount', 0)}")
            with col3:
                st.metric("Items", len(invoice_data.get('line_items', [])))
            with col4:
                rec = validation.get('recommendation', 'unknown').upper()
                
                # Show human verification badge if applicable
                if validation.get('human_override'):
                    st.success(f"✅ HUMAN VERIFIED")
                    st.caption(f"Decision: {rec}")
                elif rec == 'APPROVE':
                    st.success(f"✅ {rec}")
                elif rec == 'REJECT':
                    st.error(f"❌ {rec}")
                else:
                    st.warning(f"⚠️ {rec}")
            
            # Details in expander
            with st.expander("📄 Invoice Details", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Invoice Number:**", invoice_data.get('invoice_no', 'N/A'))
                    st.write("**PO Number:**", invoice_data.get('po_number', 'N/A'))
                    st.write("**Vendor:**", invoice_data.get('vendor_name', 'N/A'))
                with col2:
                    st.write("**Date:**", invoice_data.get('invoice_date', 'N/A'))
                    st.write("**Currency:**", invoice_data.get('currency', 'N/A'))
                    st.write("**Total:**", invoice_data.get('total_amount', 0))
                
                st.write("**Line Items:**")
                if invoice_data.get('line_items'):
                    items_df = pd.DataFrame(invoice_data['line_items'])
                    st.dataframe(items_df, width='stretch', hide_index=True)
            
            # Discrepancies
            with st.expander("⚠️ Validation Issues"):
                discrepancies = validation.get('discrepancies', [])
                if discrepancies:
                    for i, disc in enumerate(discrepancies, 1):
                        severity = disc.get('severity', 'info')
                        msg = f"**{i}. {disc.get('field')}:** {disc.get('message')}"
                        
                        if severity == 'error':
                            st.error(msg)
                        elif severity == 'warning':
                            st.warning(msg)
                        else:
                            st.info(msg)
                else:
                    st.success("✅ No validation issues")
            
            # Report
            with st.expander("📊 Audit Report"):
                # Show human verification if present
                if validation.get('human_override'):
                    st.success("✅ **HUMAN VERIFIED**")
                    human_override = validation['human_override']
                    st.info(f"**Human Decision:** {human_override.get('decision', 'N/A').upper()}")
                    st.info(f"**Reason:** {human_override.get('reason', 'No reason provided')}")
                    st.caption(f"Original: {human_override.get('original_recommendation', 'N/A').upper()} → Changed to: {human_override.get('decision', 'N/A').upper()}")
                    st.markdown("---")
                
                st.text_area("Report", result.get('report_text', ''), height=200, disabled=True)
            
            # RAG Summary
            with st.expander("🔍 RAG Summary"):
                st.write(result.get('rag_answer', 'No RAG summary available'))

# TAB 2: Review Queue
with tab2:
    st.header("⏸️ Invoices Awaiting Human Review")
    
    review_queue = st.session_state.workflow.get_review_queue()
    
    if review_queue:
        st.warning(f"⚠️ **{len(review_queue)} invoice(s) need human review to continue workflow**")
        st.markdown("---")
        
        for i,item in enumerate(review_queue):
            state = item.get('state', {})
            invoice_data = state.get('invoice_data', {})
            validation = state.get('validation_result', {})
            invoice_no = invoice_data.get('invoice_no', 'Unknown')
            
            with st.expander(f"📄 **{invoice_no}** - Review Required", expanded=True):
                # Invoice details
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Invoice", invoice_no)
                with col2:
                    st.metric("Vendor", invoice_data.get('vendor_name', 'N/A'))
                with col3:
                    st.metric("Total", f"{invoice_data.get('currency', '')} {invoice_data.get('total_amount', 0)}")
                with col4:
                    st.metric("Items", len(invoice_data.get('line_items', [])))
                
                # Line items
                st.write("**Line Items:**")
                if invoice_data.get('line_items'):
                    items_df = pd.DataFrame(invoice_data['line_items'])
                    st.dataframe(items_df, width='stretch', hide_index=True)
                
                # Discrepancies
                st.write("**⚠️ Validation Issues (Why it needs review):**")
                discrepancies = validation.get('discrepancies', [])
                if discrepancies:
                    for disc in discrepancies:
                        severity = disc.get('severity', 'info')
                        if severity == 'error':
                            st.error(f"• [{severity.upper()}] {disc.get('message')}")
                        else:
                            st.warning(f"• [{severity.upper()}] {disc.get('message')}")
                else:
                    st.info("No specific discrepancies listed")
                
                st.markdown("---")
                st.subheader("🔧 Your Decision")
                
                # Human decision
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    decision = st.selectbox(
                        "Approve or Reject:",
                        ["approve", "reject"],
                        key=f"decision_{invoice_no}_{i}"
                    )
                    
                    reason = st.text_area(
                        "Reason for your decision:",
                        placeholder="Explain why you approve/reject this invoice...",
                        key=f"reason_{invoice_no}_{i}",
                        height=100
                    )
                
                with col2:
                    st.write("")
                    st.write("")
                    st.write("")
                    if st.button("✅ Submit & Resume Workflow", key=f"resume_{invoice_no}_{i}", type="primary", width='stretch'):
                        if reason.strip():
                            # Update state with human decision
                            state['validation_result']['recommendation'] = decision
                            state['validation_result']['human_override'] = {
                                'decision': decision,
                                'reason': reason,
                                'original_recommendation': 'manual_review',
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            # Resume workflow
                            with st.spinner(f"▶️ Resuming workflow for {invoice_no}..."):
                                final_state = st.session_state.workflow.resume_workflow(state)
                                
                                # Add to processed results
                                st.session_state.processed_results.append(final_state)
                                
                                # Set as current result to display in Tab 1
                                st.session_state.current_result = final_state
                                
                                # Remove from queue
                                st.session_state.workflow.remove_from_review_queue(invoice_no)
                            
                            st.success(f"✅ Workflow resumed and completed for **{invoice_no}**")
                            st.info("📋 Go to 'Upload & Process' tab to see complete results")
                            st.balloons()
                            st.rerun()
                        else:
                            st.warning("⚠️ Please provide a reason for your decision")
    else:
        st.success("✅ **No invoices awaiting review**")
        st.info("Invoices are either auto-approved (if perfect) or sent here for manual review. Only humans can reject invoices.")

# TAB 3: Query Bot

with tab3:
    st.header("🤖 Invoice Query Assistant")
    st.caption("Ask questions about your processed invoices")
    
    # Get RAG stats to check if there's data
    rag_stats = st.session_state.workflow.get_rag_pipeline().get_stats()
    has_indexed_data = rag_stats['total_documents'] > 0
    
    if has_indexed_data:
        # Quick stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📚 Indexed Invoices", rag_stats['total_documents'])
        with col2:
            st.metric("📑 Total Chunks", rag_stats['total_chunks'])
        with col3:
            if rag_stats.get('invoices'):
                approved_count = sum(1 for inv in rag_stats['invoices'] if inv.get('recommendation') == 'approve')
                st.metric("✅ Approved", approved_count)
        
        st.markdown("---")
        
        # Initialize chat history and pending query
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'pending_query' not in st.session_state:
            st.session_state.pending_query = None
        
        # Process pending query from button clicks
        if st.session_state.pending_query:
            query_to_process = st.session_state.pending_query
            st.session_state.pending_query = None
            
            # Add user message
            st.session_state.chat_history.append({
                'role': 'user',
                'content': query_to_process
            })
            
            # Query RAG pipeline
            with st.spinner("🔍 Searching through invoices..."):
                rag_pipeline = st.session_state.workflow.get_rag_pipeline()
                result = rag_pipeline.query(query_to_process, evaluate=False)
            
            # Add assistant response
            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': result['answer'],
                'sources': result.get('sources', [])
            })
        
        # Chat container
        chat_container = st.container()
        
        with chat_container:
            # Display chat history
            for i, message in enumerate(st.session_state.chat_history):
                if message['role'] == 'user':
                    with st.chat_message("user", avatar="👤"):
                        st.write(message['content'])
                else:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.write(message['content'])
                        if message.get('sources'):
                            with st.expander("📎 Sources"):
                                st.caption(", ".join(message['sources']))
        
        # Chat input
        user_query = st.chat_input("Ask about your invoices... (e.g., Which invoices were approved? Show me invoices from Acme Corp)")
        
        if user_query:
            # Add user message to history
            st.session_state.chat_history.append({
                'role': 'user',
                'content': user_query
            })
            
            # Query RAG pipeline
            with st.spinner("🔍 Searching through invoices..."):
                rag_pipeline = st.session_state.workflow.get_rag_pipeline()
                result = rag_pipeline.query(user_query, evaluate=False)
            
            # Add assistant response to history
            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': result['answer'],
                'sources': result.get('sources', [])
            })
            
            # Rerun to update chat display
            st.rerun()
        
        # Suggested questions
        st.markdown("---")
        st.subheader("💡 Suggested Questions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📋 Which invoices need manual review?", width='stretch'):
                st.session_state.pending_query = "Which invoices need manual review?"
                st.rerun()
            
            if st.button("✅ Show me all approved invoices", width='stretch'):
                st.session_state.pending_query = "Show me all approved invoices"
                st.rerun()
        
        with col2:
            if st.button("💰 What's the total amount of all invoices?", width='stretch'):
                st.session_state.pending_query = "What's the total amount of all invoices?"
                st.rerun()
            
            if st.button("🏢 List all vendors", width='stretch'):
                st.session_state.pending_query = "List all vendors from the invoices"
                st.rerun()
        
        # Clear chat button
        if st.session_state.chat_history:
            st.markdown("---")
            if st.button("🗑️ Clear Chat History", width='content'):
                st.session_state.chat_history = []
                st.session_state.pending_query = None
                st.rerun()
    
    else:
        st.info("📭 No invoices indexed yet. Process some invoices first to start querying!")
        st.caption("Once you upload and process invoices, you'll be able to ask questions about them here.")


# TAB 4: Audit Reports
with tab4:
    st.header("📋 Audit Reports Archive")
    
    reports_path = Path("./outputs/reports")
    
    if reports_path.exists():
        # Get all JSON files
        report_files = sorted(list(reports_path.glob("*.json")), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if report_files:
            st.success(f"📁 Found {len(report_files)} audit report(s)")
            
            # Initialize session state for selected report
            if 'selected_report' not in st.session_state:
                st.session_state.selected_report = None
            
            # Reports list in sidebar-style column
            col_list, col_detail = st.columns([1, 2])
            
            with col_list:
                st.subheader("📑 Reports")
                
                for report_file in report_files:
                    try:
                        with open(report_file, 'r') as f:
                            report_data = json.load(f)
                        
                        invoice_summary = report_data.get('invoice_summary', {})
                        invoice_no = invoice_summary.get('invoice_no', 'Unknown')
                        vendor = invoice_summary.get('vendor_name', 'Unknown')
                        recommendation = report_data.get('recommendation', 'N/A').upper()
                        generated_at = report_data.get('generated_at', '')
                        
                        # Parse timestamp
                        if generated_at:
                            try:
                                dt = datetime.fromisoformat(generated_at)
                                date_str = dt.strftime("%b %d, %Y %H:%M")
                            except:
                                date_str = generated_at
                        else:
                            date_str = "Unknown date"
                        
                        # Color-coded button based on recommendation
                        if recommendation == 'APPROVE':
                            button_label = f"✅ {invoice_no}"
                        elif recommendation == 'REJECT':
                            button_label = f"❌ {invoice_no}"
                        else:
                            button_label = f"⚠️ {invoice_no}"
                        
                        if st.button(
                            f"{button_label}\n{vendor}\n{date_str}",
                            key=f"btn_{report_file.name}",
                            width='stretch'
                        ):
                            st.session_state.selected_report = report_data
                
                    except Exception as e:
                        st.error(f"Error loading {report_file.name}: {e}")
            
            with col_detail:
                if st.session_state.selected_report:
                    report = st.session_state.selected_report
                    
                    st.subheader("📄 Report Details")
                    
                    # Header info
                    invoice_summary = report.get('invoice_summary', {})
                    human_verified = report.get('human_verified', False)
                    recommendation = report.get('recommendation', 'N/A').upper()
                    
                    # Status badge
                    if human_verified:
                        st.success("✅ HUMAN VERIFIED")
                    
                    # Metrics row
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Invoice No", invoice_summary.get('invoice_no', 'N/A'))
                    with col2:
                        st.metric("PO Number", invoice_summary.get('po_number', 'N/A'))
                    with col3:
                        amount = invoice_summary.get('total_amount', 0)
                        currency = invoice_summary.get('currency', '')
                        st.metric("Total", f"{currency} {amount}")
                    with col4:
                        if recommendation == 'APPROVE':
                            st.success(f"✅ {recommendation}")
                        elif recommendation == 'REJECT':
                            st.error(f"❌ {recommendation}")
                        else:
                            st.warning(f"⚠️ {recommendation}")
                    
                    st.markdown("---")
                    
                    # Vendor and date
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Vendor:**", invoice_summary.get('vendor_name', 'N/A'))
                    with col2:
                        generated_at = report.get('generated_at', 'N/A')
                        if generated_at != 'N/A':
                            try:
                                dt = datetime.fromisoformat(generated_at)
                                date_str = dt.strftime("%B %d, %Y at %H:%M:%S")
                            except:
                                date_str = generated_at
                        else:
                            date_str = generated_at
                        st.write("**Generated:**", date_str)
                    
                    # Discrepancies count
                    discrepancies_count = report.get('discrepancies_count', 0)
                    if discrepancies_count > 0:
                        st.warning(f"⚠️ **{discrepancies_count} discrepancy(ies) found**")
                    else:
                        st.success("✅ **No discrepancies found**")
                    
                    st.markdown("---")
                    
                    # Human override info
                    human_override = report.get('human_override')
                    if human_override:
                        with st.expander("👤 Human Override Details", expanded=True):
                            st.info(f"**Decision:** {human_override.get('decision', 'N/A').upper()}")
                            st.write(f"**Reason:** {human_override.get('reason', 'No reason provided')}")
                            original = human_override.get('original_recommendation', 'N/A')
                            st.caption(f"Original AI Recommendation: {original.upper()}")
                    
                    # Full audit report
                    with st.expander("📊 Full Audit Report", expanded=True):
                        report_text = report.get('report', 'No report text available')
                        st.markdown(report_text)
                    
                    # Invoice data details
                    with st.expander("📄 Invoice Data Details"):
                        full_data = report.get('full_data', {})
                        invoice_data = full_data.get('invoice_data', {})
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Invoice Date:**", invoice_data.get('invoice_date', 'N/A'))
                            st.write("**Currency:**", invoice_data.get('currency', 'N/A'))
                            st.write("**Subtotal:**", invoice_data.get('subtotal', 0))
                        with col2:
                            st.write("**Tax Amount:**", invoice_data.get('tax_amount', 0))
                            st.write("**Total Amount:**", invoice_data.get('total_amount', 0))
                            st.write("**Original Language:**", invoice_data.get('original_language', 'N/A'))
                        
                        # Line items
                        line_items = invoice_data.get('line_items', [])
                        if line_items:
                            st.write("**Line Items:**")
                            items_df = pd.DataFrame(line_items)
                            st.dataframe(items_df, width='stretch', hide_index=True)
                        
                        # Translation info
                        if invoice_data.get('was_translated'):
                            confidence = invoice_data.get('translation_confidence', 0)
                            st.info(f"🌐 Translated from {invoice_data.get('original_language', 'N/A')} (Confidence: {confidence:.2%})")
                    
                    # Validation details
                    with st.expander("🔍 Validation Details"):
                        validation = full_data.get('validation_result', {})
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if validation.get('data_validation_passed'):
                                st.success("✅ Data Validation")
                            else:
                                st.error("❌ Data Validation")
                        with col2:
                            if validation.get('business_validation_passed'):
                                st.success("✅ Business Validation")
                            else:
                                st.error("❌ Business Validation")
                        with col3:
                            erp_status = validation.get('erp_match_status', 'unknown')
                            if erp_status == 'match':
                                st.success(f"✅ ERP: {erp_status}")
                            else:
                                st.warning(f"⚠️ ERP: {erp_status}")
                        
                        # Discrepancies
                        discrepancies = validation.get('discrepancies', [])
                        if discrepancies:
                            st.write("**Discrepancies:**")
                            for disc in discrepancies:
                                severity = disc.get('severity', 'info')
                                msg = f"**{disc.get('field')}:** {disc.get('message')}"
                                if severity == 'error':
                                    st.error(msg)
                                elif severity == 'warning':
                                    st.warning(msg)
                                else:
                                    st.info(msg)
                        else:
                            st.success("✅ No discrepancies found")
                        
                        # Missing fields
                        missing_fields = validation.get('missing_fields', [])
                        if missing_fields:
                            st.warning(f"⚠️ **Missing fields:** {', '.join(missing_fields)}")
                    
                    # Raw JSON view
                    with st.expander("🔧 Raw JSON Data"):
                        st.json(report)
                
                else:
                    st.info("👈 Select a report from the list to view details")
        
        else:
            st.info("📭 No audit reports found in `outputs/reports/`")
            st.caption("Reports will appear here after processing invoices")
    
    else:
        st.warning("⚠️ Reports directory not found")
        st.caption("Expected path: `outputs/reports/`")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>🤖 AI Invoice Auditor | Powered by Group 3 & AWS Bedrock</div>",
    unsafe_allow_html=True
)

