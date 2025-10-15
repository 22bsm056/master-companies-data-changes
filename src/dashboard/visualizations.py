"""Visualization components for dashboard with enhanced features."""
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Optional, Tuple
import streamlit as st
from datetime import datetime, timedelta
import numpy as np


class Visualizations:
    """Enhanced visualization components for company data dashboard."""
    
    # Color scheme
    COLORS = {
        'new': '#2ecc71',
        'modified': '#3498db',
        'deleted': '#e74c3c',
        'active': '#27ae60',
        'inactive': '#95a5a6',
        'primary': '#3498db',
        'secondary': '#9b59b6',
        'warning': '#f39c12',
        'danger': '#e74c3c',
        'success': '#2ecc71'
    }
    
    @staticmethod
    def plot_changes_timeline(changes_by_date: Dict):
        """
        Plot changes timeline with grouped bar chart.
        
        Args:
            changes_by_date: Dictionary of {date: {type: count}}
        """
        if not changes_by_date:
            st.info("📊 No timeline data available. Changes will appear after running change detection.")
            return
        
        try:
            # Prepare data
            dates = []
            new_counts = []
            modified_counts = []
            deleted_counts = []
            
            for date, counts in sorted(changes_by_date.items()):
                dates.append(date)
                new_counts.append(counts.get('NEW', 0))
                modified_counts.append(counts.get('MODIFIED', 0))
                deleted_counts.append(counts.get('DELETED', 0))
            
            # Create figure
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=dates,
                y=new_counts,
                name='New',
                marker_color=Visualizations.COLORS['new'],
                text=new_counts,
                textposition='auto',
                hovertemplate='<b>New Companies</b><br>Date: %{x}<br>Count: %{y}<extra></extra>'
            ))
            
            fig.add_trace(go.Bar(
                x=dates,
                y=modified_counts,
                name='Modified',
                marker_color=Visualizations.COLORS['modified'],
                text=modified_counts,
                textposition='auto',
                hovertemplate='<b>Modified Companies</b><br>Date: %{x}<br>Count: %{y}<extra></extra>'
            ))
            
            fig.add_trace(go.Bar(
                x=dates,
                y=deleted_counts,
                name='Deleted',
                marker_color=Visualizations.COLORS['deleted'],
                text=deleted_counts,
                textposition='auto',
                hovertemplate='<b>Deleted Companies</b><br>Date: %{x}<br>Count: %{y}<extra></extra>'
            ))
            
            fig.update_layout(
                title={
                    'text': '📈 Changes Timeline',
                    'x': 0.5,
                    'xanchor': 'center'
                },
                xaxis_title='Date',
                yaxis_title='Number of Changes',
                barmode='group',
                height=450,
                hovermode='x unified',
                template='plotly_white',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error plotting changes timeline: {e}")
    
    @staticmethod
    def plot_change_type_distribution(changes: Dict):
        """
        Plot change type distribution as donut chart.
        
        Args:
            changes: Dictionary with change counts
        """
        labels = ['New', 'Modified', 'Deleted']
        values = [
            changes.get('new', 0),
            changes.get('modified', 0),
            changes.get('deleted', 0)
        ]
        
        # Check if there's data
        if sum(values) == 0:
            st.info("📊 No changes to display. Run change detection to see data here.")
            return
        
        try:
            colors = [
                Visualizations.COLORS['new'],
                Visualizations.COLORS['modified'],
                Visualizations.COLORS['deleted']
            ]
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                marker=dict(colors=colors),
                hole=0.4,
                textinfo='label+percent+value',
                textposition='auto',
                hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
            )])
            
            # Add annotation in the center
            total = sum(values)
            fig.add_annotation(
                text=f'Total<br>{total:,}',
                x=0.5, y=0.5,
                font_size=16,
                showarrow=False
            )
            
            fig.update_layout(
                title={
                    'text': '🔄 Change Type Distribution',
                    'x': 0.5,
                    'xanchor': 'center'
                },
                height=450,
                template='plotly_white',
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.1,
                    xanchor="center",
                    x=0.5
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error plotting change distribution: {e}")
    
    @staticmethod
    def plot_company_status(df: pd.DataFrame):
        """
        Plot company status distribution.
        
        Args:
            df: DataFrame with company data
        """
        if df is None or df.empty:
            st.warning("No company data available")
            return
        
        if 'company_status' not in df.columns:
            st.warning("Company status column not found")
            return
        
        try:
            status_counts = df['company_status'].value_counts()
            
            if status_counts.empty:
                st.info("No status data available")
                return
            
            # Create color mapping
            colors = []
            for status in status_counts.index:
                if 'Active' in str(status):
                    colors.append(Visualizations.COLORS['active'])
                elif 'Strike' in str(status) or 'Inactive' in str(status):
                    colors.append(Visualizations.COLORS['inactive'])
                else:
                    colors.append(Visualizations.COLORS['primary'])
            
            fig = go.Figure(data=[
                go.Bar(
                    x=status_counts.index,
                    y=status_counts.values,
                    marker_color=colors,
                    text=status_counts.values,
                    textposition='auto',
                    hovertemplate='<b>%{x}</b><br>Count: %{y:,}<extra></extra>'
                )
            ])
            
            fig.update_layout(
                title={
                    'text': '📊 Company Status Distribution',
                    'x': 0.5,
                    'xanchor': 'center'
                },
                xaxis_title='Status',
                yaxis_title='Number of Companies',
                height=450,
                template='plotly_white',
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show percentage breakdown
            with st.expander("📈 Status Breakdown"):
                total = status_counts.sum()
                breakdown_data = []
                for status, count in status_counts.items():
                    percentage = (count / total) * 100
                    breakdown_data.append({
                        'Status': status,
                        'Count': f"{count:,}",
                        'Percentage': f"{percentage:.2f}%"
                    })
                st.dataframe(pd.DataFrame(breakdown_data), width='stretch')
            
        except Exception as e:
            st.error(f"Error plotting company status: {e}")
    
    @staticmethod
    def plot_category_distribution(df: pd.DataFrame, top_n: int = 10):
        """
        Plot top company categories.
        
        Args:
            df: DataFrame with company data
            top_n: Number of top categories to show
        """
        if df is None or df.empty:
            st.warning("No company data available")
            return
        
        if 'company_category' not in df.columns:
            st.warning("Company category column not found")
            return
        
        try:
            category_counts = df['company_category'].value_counts().head(top_n)
            
            if category_counts.empty:
                st.info("No category data available")
                return
            
            fig = go.Figure(data=[
                go.Bar(
                    x=category_counts.values,
                    y=category_counts.index,
                    orientation='h',
                    marker=dict(
                        color=category_counts.values,
                        colorscale='Blues',
                        showscale=True,
                        colorbar=dict(title="Count")
                    ),
                    text=category_counts.values,
                    textposition='auto',
                    hovertemplate='<b>%{y}</b><br>Count: %{x:,}<extra></extra>'
                )
            ])
            
            fig.update_layout(
                title={
                    'text': f'📊 Top {top_n} Company Categories',
                    'x': 0.5,
                    'xanchor': 'center'
                },
                xaxis_title='Number of Companies',
                yaxis_title='Category',
                height=500,
                template='plotly_white',
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error plotting category distribution: {e}")
    
    @staticmethod
    def plot_state_distribution(df: pd.DataFrame, top_n: int = 10):
        """
        Plot company distribution by state.
        
        Args:
            df: DataFrame with company data
            top_n: Number of top states to show
        """
        if df is None or df.empty or 'company_state_code' not in df.columns:
            return
        
        try:
            state_counts = df['company_state_code'].value_counts().head(top_n)
            
            fig = px.bar(
                x=state_counts.values,
                y=state_counts.index,
                orientation='h',
                labels={'x': 'Number of Companies', 'y': 'State'},
                title=f'🗺️ Top {top_n} States by Company Count',
                color=state_counts.values,
                color_continuous_scale='Greens'
            )
            
            fig.update_layout(
                height=450,
                template='plotly_white',
                title={'x': 0.5, 'xanchor': 'center'}
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error plotting state distribution: {e}")
    
    @staticmethod
    def plot_registration_trend(df: pd.DataFrame):
        """
        Plot company registration trend over time.
        
        Args:
            df: DataFrame with company data
        """
        if df is None or df.empty or 'registration_date' not in df.columns:
            return
        
        try:
            # Convert to datetime
            df['registration_date'] = pd.to_datetime(df['registration_date'], errors='coerce')
            
            # Group by month
            df['reg_month'] = df['registration_date'].dt.to_period('M')
            monthly_counts = df.groupby('reg_month').size().reset_index(name='count')
            monthly_counts['reg_month'] = monthly_counts['reg_month'].astype(str)
            
            # Get last 24 months
            monthly_counts = monthly_counts.tail(24)
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=monthly_counts['reg_month'],
                y=monthly_counts['count'],
                mode='lines+markers',
                name='Registrations',
                line=dict(color=Visualizations.COLORS['primary'], width=3),
                marker=dict(size=8),
                fill='tozeroy',
                fillcolor='rgba(52, 152, 219, 0.2)',
                hovertemplate='<b>%{x}</b><br>Registrations: %{y:,}<extra></extra>'
            ))
            
            fig.update_layout(
                title={
                    'text': '📈 Company Registration Trend (Last 24 Months)',
                    'x': 0.5,
                    'xanchor': 'center'
                },
                xaxis_title='Month',
                yaxis_title='Number of Registrations',
                height=450,
                template='plotly_white',
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error plotting registration trend: {e}")
    
    @staticmethod
    def plot_capital_distribution(df: pd.DataFrame):
        """
        Plot authorized vs paid-up capital distribution.
        
        Args:
            df: DataFrame with company data
        """
        if df is None or df.empty:
            return
        
        if 'authorized_capital' not in df.columns or 'paidup_capital' not in df.columns:
            return
        
        try:
            # Filter valid data
            valid_df = df[
                (df['authorized_capital'].notna()) & 
                (df['paidup_capital'].notna()) &
                (df['authorized_capital'] > 0)
            ].copy()
            
            if valid_df.empty:
                return
            
            # Sample if too large
            if len(valid_df) > 10000:
                valid_df = valid_df.sample(10000)
            
            fig = px.scatter(
                valid_df,
                x='authorized_capital',
                y='paidup_capital',
                title='💰 Authorized vs Paid-up Capital',
                labels={
                    'authorized_capital': 'Authorized Capital',
                    'paidup_capital': 'Paid-up Capital'
                },
                opacity=0.6,
                color_discrete_sequence=[Visualizations.COLORS['primary']]
            )
            
            fig.update_layout(
                height=450,
                template='plotly_white',
                title={'x': 0.5, 'xanchor': 'center'},
                xaxis_type='log',
                yaxis_type='log'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error plotting capital distribution: {e}")
    
    @staticmethod
    def show_metrics(stats: Dict):
        """
        Show key metrics in a card layout.
        
        Args:
            stats: Statistics dictionary
        """
        try:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total = stats.get('total_companies', 0)
                st.metric(
                    label="🏢 Total Companies",
                    value=f"{total:,}" if total > 0 else "No data",
                    help="Total number of companies in the system"
                )
            
            with col2:
                active = stats.get('active_companies', 0)
                total = stats.get('total_companies', 1)
                percentage = (active / total * 100) if total > 0 else 0
                st.metric(
                    label="✅ Active Companies",
                    value=f"{active:,}" if active > 0 else "No data",
                    delta=f"{percentage:.1f}%" if percentage > 0 else None,
                    help="Number of active companies"
                )
            
            with col3:
                changes = stats.get('total_changes', 0)
                st.metric(
                    label="🔄 Total Changes",
                    value=f"{changes:,}" if changes > 0 else "No data",
                    help="Total changes in selected period"
                )
            
            with col4:
                changes_by_type = stats.get('changes_by_type', {})
                modified = changes_by_type.get('MODIFIED', 0)
                st.metric(
                    label="📝 Modified",
                    value=f"{modified:,}" if modified > 0 else "No data",
                    help="Number of modified companies"
                )
            
        except Exception as e:
            st.error(f"Error displaying metrics: {e}")
    
    @staticmethod
    def show_advanced_metrics(stats: Dict, df: pd.DataFrame = None):
        """
        Show advanced analytics metrics.
        
        Args:
            stats: Statistics dictionary
            df: Optional DataFrame for additional calculations
        """
        try:
            st.subheader("📊 Advanced Analytics")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### Change Rate")
                changes = stats.get('total_changes', 0)
                total = stats.get('total_companies', 1)
                change_rate = (changes / total * 100) if total > 0 else 0
                
                st.metric(
                    "Change Rate",
                    f"{change_rate:.2f}%",
                    help="Percentage of companies that changed"
                )
            
            with col2:
                st.markdown("### Activity Score")
                changes_by_type = stats.get('changes_by_type', {})
                new = changes_by_type.get('NEW', 0)
                modified = changes_by_type.get('MODIFIED', 0)
                activity_score = new + (modified * 0.5)
                
                st.metric(
                    "Activity Score",
                    f"{activity_score:,.0f}",
                    help="Weighted activity metric"
                )
            
            with col3:
                st.markdown("### Data Quality")
                if df is not None and not df.empty:
                    completeness = (1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
                    st.metric(
                        "Data Completeness",
                        f"{completeness:.1f}%",
                        help="Percentage of non-null values"
                    )
                else:
                    st.metric("Data Completeness", "N/A")
            
        except Exception as e:
            st.error(f"Error showing advanced metrics: {e}")
    
    @staticmethod
    def create_summary_table(changes_by_date: Dict):
        """
        Create a summary table of changes.
        
        Args:
            changes_by_date: Dictionary of changes by date
        """
        if not changes_by_date:
            return
        
        try:
            summary_data = []
            for date, counts in sorted(changes_by_date.items(), reverse=True):
                summary_data.append({
                    'Date': date,
                    'New': counts.get('NEW', 0),
                    'Modified': counts.get('MODIFIED', 0),
                    'Deleted': counts.get('DELETED', 0),
                    'Total': counts.get('NEW', 0) + counts.get('MODIFIED', 0) + counts.get('DELETED', 0)
                })
            
            df_summary = pd.DataFrame(summary_data)
            
            # Style the dataframe
            st.dataframe(
                df_summary.style.highlight_max(axis=0, subset=['New', 'Modified', 'Deleted']),
                width='stretch'
            )
            
        except Exception as e:
            st.error(f"Error creating summary table: {e}")
    
    @staticmethod
    def export_chart_data(data: pd.DataFrame, filename: str):
        """
        Provide export functionality for chart data.
        
        Args:
            data: DataFrame to export
            filename: Name for the export file
        """
        try:
            csv = data.to_csv(index=False)
            st.download_button(
                label="📥 Download Data as CSV",
                data=csv,
                file_name=filename,
                mime='text/csv'
            )
        except Exception as e:
            st.error(f"Error exporting data: {e}")