"""Streamlit dashboard for data visualization and chatbot."""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from src.database.operations import DatabaseOperations
from src.processors.change_detector import ChangeDetector
from src.processors.snapshot_manager import SnapshotManager
from src.agents.agentic_system import AgenticSystem
from src.dashboard.visualizations import Visualizations
from config.settings import Settings

# Page config
st.set_page_config(
    page_title="Company Data Management Dashboard",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize components
@st.cache_resource
def init_components():
    """Initialize dashboard components."""
    return {
        'db_ops': DatabaseOperations(),
        'change_detector': ChangeDetector(),
        'snapshot_manager': SnapshotManager(),
        'agent': AgenticSystem(),
        'viz': Visualizations()
    }

components = init_components()

def main():
    """Main dashboard function."""
    st.title("🏢 Company Data Management Dashboard")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Select Page",
            ["📊 Overview", "📈 Analytics", "🔍 Changes Explorer", "🤖 AI Chatbot"]
        )
        
        st.markdown("---")
        st.header("Settings")
        
        time_period = st.selectbox(
            "Time Period",
            ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "Custom"],
            index=1
        )
        
        # Calculate date range
        if time_period == "Last 24 Hours":
            days = 1
        elif time_period == "Last 7 Days":
            days = 7
        elif time_period == "Last 30 Days":
            days = 30
        else:
            days = st.number_input("Days", min_value=1, max_value=365, value=7)
    
    # Main content
    if page == "📊 Overview":
        show_overview(days)
    elif page == "📈 Analytics":
        show_analytics(days)
    elif page == "🔍 Changes Explorer":
        show_changes_explorer(days)
    else:
        show_chatbot()


    
    
def show_overview(days: int):
    """Show overview page."""
    st.header("Overview")
    
    # Get statistics with error handling
    with st.spinner("Loading statistics..."):
        try:
            # Try to get from database
            db_stats = components['db_ops'].get_statistics(days)
            
            # Get from hybrid search (always has data)
            search_stats = components['change_detector'].search_system.get_statistics() if hasattr(components['change_detector'], 'search_system') else {}
            
            # Merge statistics (prefer database if available, fallback to hybrid search)
            stats = {
                'total_companies': db_stats.get('total_companies', 0) or search_stats.get('total_companies', 0),
                'active_companies': db_stats.get('active_companies', 0) or search_stats.get('active_companies', 0),
                'total_changes': db_stats.get('total_changes', 0) or search_stats.get('total_changes', 0),
                'changes_by_type': db_stats.get('changes_by_type', {
                    'NEW': 0,
                    'MODIFIED': 0,
                    'DELETED': 0
                })
            }
            
            # If still no data, try to get from tools directly
            if stats['total_companies'] == 0:
                try:
                    tool_stats = components['agent'].tools.get_statistics(days)
                    stats.update(tool_stats)
                except:
                    pass
            
        except Exception as e:
            st.error(f"Error loading statistics: {e}")
            # Provide default values
            stats = {
                'total_companies': 0,
                'active_companies': 0,
                'total_changes': 0,
                'changes_by_type': {'NEW': 0, 'MODIFIED': 0, 'DELETED': 0}
            }
    
    # Show metrics
    components['viz'].show_metrics(stats)
    
    st.markdown("---")
    
    # Get changes summary with error handling
    try:
        changes_summary = components['change_detector'].get_changes_summary(days)
    except Exception as e:
        st.warning(f"Could not load changes: {e}")
        changes_summary = {
            'total_changes': 0,
            'new': 0,
            'modified': 0,
            'deleted': 0,
            'by_date': {}
        }
    
    # Only show charts if there's data
    if changes_summary['total_changes'] > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            components['viz'].plot_change_type_distribution(changes_summary)
        
        with col2:
            if changes_summary.get('by_date'):
                components['viz'].plot_changes_timeline(changes_summary['by_date'])
    else:
        st.info("No changes recorded yet. Changes will appear here after running change detection.")
    
    # Recent snapshots
    st.markdown("---")
    st.subheader("Recent Snapshots")
    
    snapshot_files = sorted(
        Settings.SNAPSHOT_DIR.glob("snapshot_*.csv"),
        reverse=True
    )[:5]
    
    if snapshot_files:
        snapshot_data = []
        for file in snapshot_files:
            try:
                # Just get file size, don't load entire file
                file_size = file.stat().st_size / 1024 / 1024
                
                # Try to count rows quickly
                try:
                    with open(file, 'r') as f:
                        row_count = sum(1 for _ in f) - 1  # Subtract header
                except:
                    row_count = "Unknown"
                
                snapshot_data.append({
                    'Date': file.stem.replace('snapshot_', ''),
                    'Records': f"{row_count:,}" if isinstance(row_count, int) else row_count,
                    'Size': f"{file_size:.2f} MB"
                })
            except Exception as e:
                logger.warning(f"Error reading {file.name}: {e}")
        
        if snapshot_data:
            st.dataframe(pd.DataFrame(snapshot_data), width='stretch')
    else:
        st.info("No snapshots available. Run 'python main.py snapshot' to create one.")


def show_analytics(days: int):
    """Show analytics page."""
    st.header("Analytics")
    
    # Load latest snapshot
    with st.spinner("Loading snapshot data..."):
        try:
            df = components['snapshot_manager'].get_latest_snapshot()
        except Exception as e:
            st.error(f"Error loading snapshot: {e}")
            return
    
    if df is not None and not df.empty:
        st.success(f"Loaded {len(df):,} companies")
        
        # Company status distribution
        st.subheader("Company Status Distribution")
        components['viz'].plot_company_status(df)
        
        # Category distribution
        st.subheader("Company Categories")
        top_n = st.slider("Number of categories to show", 5, 20, 10)
        components['viz'].plot_category_distribution(df, top_n)
        
        # Data table
        st.subheader("Company Data Sample")
        st.dataframe(df.head(100), width='stretch')  # Changed here
        
    else:
        st.warning("No snapshot data available")

def show_changes_explorer(days: int):
    """Show changes explorer page."""
    st.header("Changes Explorer")
    
    # Date range
    start_date = datetime.now().date() - timedelta(days=days)
    end_date = datetime.now().date()
    
    # Get changes
    with st.spinner("Loading changes..."):
        changes = components['db_ops'].get_changes_by_date_range(start_date, end_date)
    
    if changes:
        st.success(f"Found {len(changes):,} changes")
        
        # Filters
        col1, col2 = st.columns(2)
        
        with col1:
            change_types = ['All'] + list(set(c['change_type'] for c in changes))
            selected_type = st.selectbox("Change Type", change_types)
        
        with col2:
            search_query = st.text_input("Search Company", "")
        
        # Filter changes
        filtered_changes = changes
        
        if selected_type != 'All':
            filtered_changes = [c for c in filtered_changes if c['change_type'] == selected_type]
        
        if search_query:
            filtered_changes = [
                c for c in filtered_changes
                if search_query.lower() in (c.get('company_name', '') or '').lower()
                or search_query.upper() in (c.get('cin', '') or '').upper()
            ]
        
        # Display changes
        st.subheader(f"Showing {len(filtered_changes)} changes")
        
        for change in filtered_changes[:50]:  # Show first 50
            with st.expander(
                f"{change['change_type']} - {change.get('company_name', 'N/A')} ({change.get('cin', 'N/A')})"
            ):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Change Date:**", change.get('change_date'))
                    st.write("**Change Type:**", change.get('change_type'))
                
                with col2:
                    if change.get('changed_fields'):
                        st.write("**Changed Fields:**")
                        st.json(change['changed_fields'])
                
                if change.get('old_values') and change.get('new_values'):
                    st.write("**Changes:**")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("Old Values:")
                        st.json(change['old_values'])
                    with col2:
                        st.write("New Values:")
                        st.json(change['new_values'])
    else:
        st.info("No changes found in the selected period")




def show_chatbot():
    """Show AI chatbot page with timeout handling."""
    st.header("🤖 AI Assistant")
    
    # Check if agent is available
    if components.get('agent') is None:
        st.error("❌ AI Assistant is currently unavailable.")
        return
    
    # Instructions
    st.markdown("""
    💬 **Ask me about company data!**
    
    **What I can do:**
    - 🔍 Find companies by name or CIN
    - 📊 Show changes and updates
    - 📈 Provide statistics
    
    **Example questions:**
    - "Hello" or "Help"
    - "Find MAPPD SYSTEMS"
    - "Show changes"
    - "How many companies?"
    """)
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your question here..."):
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response with timeout
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    # Import threading for timeout
                    import threading
                    
                    response_container = {"response": None, "error": None}
                    
                    def get_response():
                        try:
                            response_container["response"] = components['agent'].query(prompt)
                        except Exception as e:
                            response_container["error"] = str(e)
                    
                    # Start thread
                    thread = threading.Thread(target=get_response)
                    thread.daemon = True
                    thread.start()
                    
                    # Wait with timeout
                    thread.join(timeout=20)  # 20 second timeout
                    
                    if thread.is_alive():
                        # Timeout occurred
                        response = "⚠️ The request is taking too long. Please try a simpler question."
                    elif response_container["error"]:
                        # Error occurred
                        response = f"❌ Error: {response_container['error']}"
                    elif response_container["response"]:
                        # Success
                        response = response_container["response"]
                    else:
                        # Unknown state
                        response = "❌ Unable to generate response. Please try again."
                    
                    st.markdown(response)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
    
    # Sidebar controls
    with st.sidebar:
        st.markdown("---")
        st.subheader("💬 Chat Controls")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_history = []
                st.rerun()
        
        with col2:
            if st.button("💡 Example"):
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": "How many companies?"
                })
                st.rerun()
        
        # System status
        st.markdown("---")
        st.subheader("⚙️ System Status")
        
        try:
            health = components['agent'].health_check()
            
            if health['status'] == 'healthy':
                st.success("✅ Online")
            else:
                st.warning("⚠️ Limited")
            
            st.caption(f"Graph: {'✅' if health.get('graph_available') else '❌'}")
            st.caption(f"Tools: {'✅' if health.get('tools_available') else '❌'}")
            
        except Exception as e:
            st.error("❌ Offline")
def run_dashboard():
    """Run the dashboard."""
    main()

if __name__ == "__main__":
    run_dashboard()