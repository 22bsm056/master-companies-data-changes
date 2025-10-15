"""Smart Agentic AI system - Context-aware and precise responses."""
import os
import json
import re
from typing import Dict, List, Optional, TypedDict, Annotated, Any
import operator
from datetime import datetime, timedelta
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from config.settings import Settings
from src.agents.tools import AgentTools
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# Define agent state
class AgentState(TypedDict):
    """State for the agentic workflow."""
    messages: Annotated[List, operator.add]
    user_query: str
    intent: Optional[str]
    time_context: Optional[str]  # today, yesterday, week, etc.
    company_identifier: Optional[str]
    company_data: Optional[List[Dict]]
    changes_data: Optional[List[Dict]]
    statistics: Optional[Dict]
    final_response: Optional[str]


class AgenticSystem:
    """Smart agentic AI system with precise, context-aware responses."""
    
    def __init__(self):
        """Initialize agentic system."""
        logger.info("Initializing Smart Agentic AI System...")
        
        # Initialize tools
        self.tools = AgentTools()
        logger.info("[OK] Agent tools initialized")
        
        # Initialize Gemini LLM
        self.llm = None
        try:
            if Settings.GEMINI_API_KEY:
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash",
                    google_api_key=Settings.GEMINI_API_KEY,
                    temperature=0.3,  # Lower for more consistent responses
                    max_tokens=512,
                    timeout=10
                )
                logger.info("[OK] Gemini LLM initialized")
        except Exception as e:
            logger.warning(f"[WARN] LLM initialization failed: {e}")
        
        # Build agent graph
        self.graph = self._build_graph()
        logger.info("[OK] Agent graph built")
    
    def _build_graph(self) -> StateGraph:
        """Build intelligent workflow."""
        workflow = StateGraph(AgentState)
        
        workflow.add_node("analyze_query", self._analyze_query)
        workflow.add_node("fetch_data", self._fetch_data)
        workflow.add_node("generate_response", self._generate_smart_response)
        
        workflow.set_entry_point("analyze_query")
        workflow.add_edge("analyze_query", "fetch_data")
        workflow.add_edge("fetch_data", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    def _analyze_query(self, state: AgentState) -> AgentState:
        """Analyze user query to understand context and intent."""
        query = state["user_query"].lower()
        
        # Extract time context
        time_context = self._extract_time_context(query)
        state["time_context"] = time_context
        
        # Determine intent
        intent = self._determine_intent(query)
        state["intent"] = intent
        
        # Extract company identifier if present
        state["company_identifier"] = self._extract_company_identifier(query)
        
        logger.info(f"Analysis: intent={intent}, time={time_context}")
        return state
    
    def _extract_time_context(self, query: str) -> Optional[str]:
        """Extract time period from query."""
        if 'today' in query:
            return 'today'
        elif 'yesterday' in query:
            return 'yesterday'
        elif 'this week' in query or 'week' in query:
            return 'week'
        elif 'this month' in query or 'month' in query:
            return 'month'
        elif 'last 7 days' in query:
            return 'week'
        elif 'last 30 days' in query:
            return 'month'
        return None
    
    def _determine_intent(self, query: str) -> str:
        """Determine user intent from query."""
        # Greeting
        if any(word in query for word in ['hi', 'hello', 'hey', 'greetings']):
            return 'greeting'
        
        # Help
        if 'help' in query:
            return 'help'
        
        # Changes query (specific)
        if any(phrase in query for phrase in ['changed', 'changes', 'what changed', 'updates', 'modified']):
            return 'changes'
        
        # Company search
        if any(word in query for word in ['find', 'search', 'show me', 'get', 'details about']):
            return 'search'
        
        # Statistics (general count)
        if any(phrase in query for phrase in ['how many', 'count', 'total', 'number of']):
            # Distinguish between general count and change count
            if any(word in query for word in ['changed', 'changes', 'modified', 'updated']):
                return 'changes'
            return 'statistics'
        
        return 'general'
    
    def _extract_company_identifier(self, query: str) -> Optional[str]:
        """Extract company name or CIN from query."""
        # CIN pattern
        cin_pattern = r'[A-Z]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}'
        cin_match = re.search(cin_pattern, query.upper())
        if cin_match:
            return cin_match.group(0)
        
        # Company name extraction (simple approach)
        # Look for words after "find", "search", "about", etc.
        patterns = [
            r'find\s+([A-Za-z\s]+?)(?:\s+company|\s+cin|$)',
            r'search\s+([A-Za-z\s]+?)(?:\s+company|\s+cin|$)',
            r'about\s+([A-Za-z\s]+?)(?:\s+company|\s+cin|$)',
            r'show me\s+([A-Za-z\s]+?)(?:\s+company|\s+cin|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _fetch_data(self, state: AgentState) -> AgentState:
        """Fetch relevant data based on intent and context."""
        intent = state["intent"]
        time_context = state["time_context"]
        
        try:
            # Always fetch basic statistics
            days = self._get_days_from_context(time_context)
            state["statistics"] = self.tools.get_statistics(days)
            
            # Fetch specific data based on intent
            if intent == 'search' and state["company_identifier"]:
                # Search for company
                results = self.tools.query_rag_companies(state["company_identifier"], top_k=5)
                state["company_data"] = results
                
                # Get changes for found companies
                if results:
                    all_changes = []
                    for company in results[:3]:
                        cin = company.get("metadata", {}).get("cin")
                        if cin:
                            changes = self.tools.get_company_changes(cin)
                            if changes:
                                all_changes.extend(changes)
                    state["changes_data"] = all_changes
            
            elif intent == 'changes':
                # Fetch changes based on time context
                if time_context:
                    # Get changes for specific time period
                    changes = self.tools.query_rag_changes(state["user_query"], top_k=20)
                    state["changes_data"] = changes
            
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
        
        return state
    
    def _get_days_from_context(self, time_context: Optional[str]) -> int:
        """Convert time context to number of days."""
        if time_context == 'today':
            return 1
        elif time_context == 'yesterday':
            return 2
        elif time_context == 'week':
            return 7
        elif time_context == 'month':
            return 30
        return 7  # Default
    
    def _generate_smart_response(self, state: AgentState) -> AgentState:
        """Generate context-aware, precise response."""
        intent = state["intent"]
        
        # Route to specific response generator
        if intent == 'greeting':
            response = self._greeting_response(state)
        elif intent == 'help':
            response = self._help_response(state)
        elif intent == 'statistics':
            response = self._statistics_response(state)
        elif intent == 'changes':
            response = self._changes_response(state)
        elif intent == 'search':
            response = self._search_response(state)
        else:
            response = self._general_response(state)
        
        state["final_response"] = response
        return state
    
    def _greeting_response(self, state: AgentState) -> str:
        """Generate greeting response."""
        stats = state.get("statistics", {})
        total = stats.get('total_companies', 0)
        active = stats.get('active_companies', 0)
        
        return f"""👋 **Hello!**

I'm managing **{total:,} companies** in your dashboard ({active:,} active).

**What can I help you with?**
• Search for a company
• Check today's changes
• Get detailed statistics
• Analyze trends

Just ask me naturally!"""
    
    def _help_response(self, state: AgentState) -> str:
        """Generate help response."""
        return """🤖 **I'm your AI Company Data Assistant**

**📊 Ask about statistics:**
• "How many companies are active?"
• "Total companies in dashboard"
• "Give me the overview"

**🔍 Search for companies:**
• "Find MAPPD SYSTEMS"
• "Search for companies in Delhi"
• "Show me company U74999DL2016PTC300286"

**📝 Check changes:**
• "What changed today?"
• "Show changes this week"
• "Companies modified yesterday"

**💡 Tips:**
• Ask naturally, like you're talking to a colleague
• Be specific about time periods (today, this week, etc.)
• I understand context and follow-up questions

Try asking: "What companies changed today?"""
    
    def _statistics_response(self, state: AgentState) -> str:
        """Generate statistics response."""
        stats = state.get("statistics", {})
        time_context = state["time_context"]
        
        total = stats.get('total_companies', 0)
        active = stats.get('active_companies', 0)
        inactive = total - active
        
        # Determine active percentage
        active_pct = (active / total * 100) if total > 0 else 0
        
        return f"""📊 **Dashboard Overview**

**Total Companies:** {total:,}
• ✅ Active: {active:,} ({active_pct:.1f}%)
• ⏸️ Inactive/Strike-off: {inactive:,} ({100-active_pct:.1f}%)

**Status Breakdown:**
The majority of companies in your dashboard are {'active and operational' if active_pct > 50 else 'inactive or struck off'}.

Need more details? Ask:
• "What changed today?"
• "Find a specific company"
• "Show me active companies in [state]" """
    
    def _changes_response(self, state: AgentState) -> str:
        """Generate changes response with context."""
        stats = state.get("statistics", {})
        time_context = state["time_context"]
        changes_data = state.get("changes_data", [])
        
        # Get change counts from statistics
        changes_by_type = stats.get('changes_by_type', {})
        total_changes = stats.get('total_changes', 0)
        new = changes_by_type.get('NEW', 0)
        modified = changes_by_type.get('MODIFIED', 0)
        deleted = changes_by_type.get('DELETED', 0)
        
        # Determine time period text
        if time_context == 'today':
            period_text = "today"
            days = 1
        elif time_context == 'yesterday':
            period_text = "yesterday"
            days = 2
        elif time_context == 'week':
            period_text = "this week"
            days = 7
        elif time_context == 'month':
            period_text = "this month"
            days = 30
        else:
            period_text = "in the last 7 days"
            days = 7
        
        # Build response
        if total_changes == 0:
            return f"""📝 **Changes {period_text.capitalize()}**

No changes detected {period_text}.

This could mean:
• No new data was received
• No companies were modified
• Change detection hasn't run yet

**Next steps:**
• Run change detection: `python main.py changes`
• Check a different time period
• Verify your data sources"""
        
        # Show detailed breakdown
        response = f"""📝 **Changes {period_text.capitalize()}**

**Total Changes:** {total_changes:,}

**Breakdown:**
• 🆕 New Companies: {new:,}
• ✏️ Modified: {modified:,}
• 🗑️ Removed: {deleted:,}

"""
        
        # Add trend analysis
        if new > modified + deleted:
            response += "**Trend:** 📈 Growing - More companies being added\n"
        elif deleted > new + modified:
            response += "**Trend:** 📉 Declining - More companies being removed\n"
        elif modified > new + deleted:
            response += "**Trend:** 🔄 Active Updates - Existing companies being modified\n"
        
        # Show sample changes if available
        if changes_data:
            response += f"\n**Recent Examples:**\n"
            for i, change in enumerate(changes_data[:3], 1):
                metadata = change.get("metadata", {})
                name = metadata.get("company_name", "N/A")
                change_type = metadata.get("change_type", "N/A")
                response += f"{i}. {change_type}: {name}\n"
        
        return response
    
    def _search_response(self, state: AgentState) -> str:
        """Generate search response."""
        company_data = state.get("company_data", [])
        company_id = state.get("company_identifier", "")
        
        if not company_data:
            return f"""🔍 **Search Results**

No companies found matching: **{company_id}**

**Suggestions:**
• Check spelling
• Try searching by CIN instead
• Use partial name (e.g., "MAPPD" instead of full name)
• Ask: "Show me active companies" for a general list"""
        
        # Show results
        response = f"🔍 **Found {len(company_data)} result(s) for '{company_id}':**\n\n"
        
        for i, company in enumerate(company_data[:5], 1):
            metadata = company.get("metadata", {})
            name = metadata.get("company_name", "N/A")
            cin = metadata.get("cin", "N/A")
            status = metadata.get("company_status", "N/A")
            category = metadata.get("company_category", "N/A")
            
            status_emoji = "✅" if status == "Active" else "⏸️"
            
            response += f"""**{i}. {name}**
{status_emoji} Status: {status}
🔢 CIN: `{cin}`
📁 Category: {category}

"""
        
        # Show changes if available
        changes_data = state.get("changes_data", [])
        if changes_data:
            response += f"\n**📝 Recent Changes ({len(changes_data)}):**\n"
            for change in changes_data[:3]:
                change_type = change.get("change_type", "N/A")
                change_date = change.get("change_date", "N/A")
                response += f"• {change_type} on {change_date}\n"
        
        return response
    
    def _general_response(self, state: AgentState) -> str:
        """Generate general response with AI if available."""
        query = state["user_query"]
        
        # Try AI response
        if self.llm:
            try:
                stats = state.get("statistics", {})
                context = f"""User manages {stats.get('total_companies', 0):,} companies.
Active: {stats.get('active_companies', 0):,}
Recent changes: {stats.get('total_changes', 0):,}"""
                
                prompt = f"""You are a helpful AI assistant for company data.
Context: {context}
User question: {query}

Provide a brief, natural response (max 100 words). Be conversational and helpful."""
                
                response = self.llm.invoke([HumanMessage(content=prompt)])
                return response.content
                
            except Exception as e:
                logger.error(f"AI response failed: {e}")
        
        # Fallback
        stats = state.get("statistics", {})
        return f"""I understand you're asking: "{query}"

**Quick facts:**
• {stats.get('total_companies', 0):,} total companies
• {stats.get('active_companies', 0):,} active companies

**I can help with:**
• "What changed today?" - Check recent changes
• "Find [company name]" - Search for companies
• "Help" - See all commands

What would you like to know?"""
    
    def query(self, user_query: str) -> str:
        """
        Process user query with smart understanding.
        
        Args:
            user_query: User's question
        
        Returns:
            Context-aware response
        """
        if not user_query or len(user_query.strip()) == 0:
            return "Please ask me a question about your company data."
        
        if len(user_query) > 500:
            return "Please keep questions under 500 characters."
        
        logger.info(f"Processing: {user_query}")
        
        initial_state = AgentState(
            messages=[],
            user_query=user_query.strip(),
            intent=None,
            time_context=None,
            company_identifier=None,
            company_data=None,
            changes_data=None,
            statistics=None,
            final_response=None
        )
        
        try:
            final_state = self.graph.invoke(initial_state)
            response = final_state.get("final_response", "Unable to process your request.")
            logger.info("[OK] Response generated")
            return response
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return f"I encountered an error. Please try rephrasing your question.\n\nError: {str(e)}"
    
    def health_check(self) -> Dict[str, Any]:
        """Check system health."""
        try:
            stats = self.tools.get_statistics(7)
            return {
                "status": "healthy",
                "llm_available": self.llm is not None,
                "graph_available": self.graph is not None,
                "companies_count": stats.get('total_companies', 0),
                "data_available": stats.get('total_companies', 0) > 0
            }
        except:
            return {"status": "degraded", "data_available": False}