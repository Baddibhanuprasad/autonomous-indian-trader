import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.data.database import DatabaseManager
from src.utils.config import config

class Dashboard:
    """Streamlit dashboard for trading system"""
    
    def __init__(self):
        self.db = DatabaseManager()
        
    def run(self):
        st.set_page_config(
            page_title="Indian Stock Trading Agent",
            page_icon="📈",
            layout="wide"
        )
        
        st.title("🇮🇳 Autonomous Indian Stock Trading Agent")
        
        # Auto-refresh
        st.empty()
        
        # Create layout
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            self.show_portfolio_value()
        
        with col2:
            self.show_daily_pnl()
        
        with col3:
            self.show_open_positions()
        
        with col4:
            self.show_win_rate()
        
        # Charts row
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            st.subheader("📊 Equity Curve")
            self.show_equity_curve()
        
        with col_right:
            st.subheader("📉 Drawdown")
            self.show_drawdown_chart()
        
        # Trade history
        st.subheader("📋 Recent Trades")
        self.show_trade_history()
        
        # News panel
        st.subheader("📰 Latest News Sentiment")
        self.show_news_panel()
    
    def show_portfolio_value(self):
        """Display current portfolio value"""
        capital = 1000000  # Initial capital
        # Calculate current value from database
        trades = self.db.get_trade_history(limit=1000)
        total_pnl = sum(t.pnl for t in trades if t.pnl and t.status == 'CLOSED')
        current_value = capital + total_pnl
        
        st.metric(
            label="Portfolio Value",
            value=f"₹{current_value:,.2f}",
            delta=f"₹{total_pnl:,.2f}"
        )
    
    def show_daily_pnl(self):
        """Display today's PnL"""
        daily_pnl = self.db.get_daily_pnl()
        st.metric(
            label="Today's P&L",
            value=f"₹{daily_pnl:,.2f}",
            delta=f"{(daily_pnl/10000)*100:.2f}%" if daily_pnl else "0%"
        )
    
    def show_open_positions(self):
        """Display open positions count"""
        open_trades = self.db.get_open_trades()
        st.metric(
            label="Open Positions",
            value=len(open_trades)
        )
    
    def show_win_rate(self):
        """Display win rate"""
        trades = self.db.get_trade_history(limit=1000)
        winning_trades = [t for t in trades if t.pnl and t.pnl > 0 and t.status == 'CLOSED']
        total_closed = len([t for t in trades if t.status == 'CLOSED'])
        win_rate = (len(winning_trades) / total_closed * 100) if total_closed > 0 else 0
        
        st.metric(
            label="Win Rate",
            value=f"{win_rate:.1f}%"
        )
    
    def show_equity_curve(self):
        """Display equity curve chart"""
        trades = self.db.get_trade_history(limit=1000)
        
        if not trades:
            st.info("No trade data available")
            return
        
        # Build equity curve
        data = []
        equity = 1000000
        for trade in reversed(trades):
            if trade.pnl and trade.status == 'CLOSED':
                equity += trade.pnl
                data.append({
                    'timestamp': trade.timestamp,
                    'equity': equity
                })
        
        if data:
            df = pd.DataFrame(data)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['equity'],
                mode='lines',
                name='Equity',
                line=dict(color='green', width=2)
            ))
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Equity (₹)",
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    def show_drawdown_chart(self):
        """Display drawdown chart"""
        trades = self.db.get_trade_history(limit=1000)
        
        if not trades:
            st.info("No trade data available")
            return
        
        # Calculate drawdown
        equity = 1000000
        peak = equity
        drawdowns = []
        
        for trade in reversed(trades):
            if trade.pnl and trade.status == 'CLOSED':
                equity += trade.pnl
                if equity > peak:
                    peak = equity
                drawdown = ((equity - peak) / peak) * 100
                drawdowns.append({
                    'timestamp': trade.timestamp,
                    'drawdown': drawdown
                })
        
        if drawdowns:
            df = pd.DataFrame(drawdowns)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['drawdown'],
                mode='lines',
                fill='tozeroy',
                name='Drawdown',
                line=dict(color='red', width=1)
            ))
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Drawdown (%)",
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    def show_trade_history(self):
        """Display trade history table"""
        trades = self.db.get_trade_history(limit=50)
        
        if trades:
            df = pd.DataFrame([{
                'Time': t.timestamp,
                'Symbol': t.symbol,
                'Type': t.trade_type,
                'Entry': t.entry_price,
                'Exit': t.exit_price,
                'Qty': t.quantity,
                'P&L': f"₹{t.pnl:,.2f}" if t.pnl else '-',
                'Status': t.status,
                'Sentiment': t.news_sentiment,
                'Tech Score': f"{t.technical_score:.0f}" if t.technical_score else '-'
            } for t in trades])
            
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No trades executed yet")
    
    def show_news_panel(self):
        """Display latest news sentiment"""
        st.write("Latest News Sentiment Analysis")
        
        # This would ideally fetch from the news agent
        # For now, showing sample data
        st.info("News sentiment data will appear here when trading is active")

def run_dashboard():
    """Run the dashboard"""
    dashboard = Dashboard()
    dashboard.run()

if __name__ == "__main__":
    run_dashboard()