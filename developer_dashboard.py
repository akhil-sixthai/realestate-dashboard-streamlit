import streamlit as st
from scipy.stats import linregress
import plotly.express as px
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import json
from functools import lru_cache
from developer_data import *






def dashboard_developer():
    # Initialize session state for storing filter values
    if 'filter_themes' not in st.session_state:
        st.session_state['filter_themes'] = []
    if 'filter_keywords' not in st.session_state:
        st.session_state['filter_keywords'] = []
    if 'filter_accounts' not in st.session_state:
        st.session_state['filter_accounts'] = []
    if 'filter_date_range' not in st.session_state:
        st.session_state['filter_date_range'] = None
    if 'filter_countries' not in st.session_state:
        st.session_state['filter_countries'] = []



    # Initialize session state for applied filters
    if 'selected_themes' not in st.session_state:
        st.session_state['selected_themes'] = []
    if 'selected_keywords' not in st.session_state:
        st.session_state['selected_keywords'] = []
    if 'selected_accounts' not in st.session_state:
        st.session_state['selected_accounts'] = []
    if 'date_range' not in st.session_state:
        st.session_state['date_range'] = None
    if 'selected_countries' not in st.session_state:
        st.session_state['selected_countries'] = []


    data = get_data()

    print(f"Total accounts = {len(data)}")

    # Get list of all usernames for account filter
    all_usernames = list(set([account.get('username', '') for account in data]))
    all_usernames.sort()  # Sort alphabetically for better UX

    # Get min and max dates from the data for the date range filter
    min_date, max_date = get_date_range(data)
    # Set default date range if not already in session state
    if st.session_state['filter_date_range'] is None and min_date and max_date:
        st.session_state['filter_date_range'] = (min_date, max_date)
        st.session_state['date_range'] = (min_date, max_date)  # Also set applied date range

    # Define callback functions for all filters
    def update_theme_selection():
        if "theme_filter_callback" in st.session_state:
            st.session_state['filter_themes'] = st.session_state["theme_filter_callback"]

    def update_keyword_selection():
        if "keyword_filter_callback" in st.session_state:
            st.session_state['filter_keywords'] = st.session_state["keyword_filter_callback"]

    def update_account_selection():
        if "account_filter_callback" in st.session_state:
            st.session_state['filter_accounts'] = st.session_state["account_filter_callback"]

    def update_country_selection():
        if "country_filter_callback" in st.session_state:
            st.session_state['filter_countries'] = st.session_state["country_filter_callback"]


    def update_date_selection():
        if "date_filter_callback" in st.session_state:
            date_input = st.session_state["date_filter_callback"]
            # Handle both single date and date range selections
            if isinstance(date_input, tuple) and len(date_input) == 2:
                st.session_state['filter_date_range'] = date_input
            elif hasattr(date_input, '__len__') and len(date_input) == 2:
                st.session_state['filter_date_range'] = (date_input[0], date_input[1])
            else:
                # For single date selection
                st.session_state['filter_date_range'] = (date_input, date_input)

    # Set the title
    st.subheader("Brand Led Analysis")

    # Create a container for filters
    filter_container = st.container()

    with filter_container:
        # Create two rows of filters
        filter_row1_col1, filter_row1_col2, filter_row1_col3 = st.columns(3)
        filter_row2_col1, filter_row2_col2 = st.columns(2)
        
        with filter_row1_col1:
            # Get all available themes
            all_themes = list(THEME_KEYWORDS.keys())
            all_themes.append("Others")  # Add "Others" as it's used in your theme distribution
            
            # Theme filter with callback
            st.multiselect(
                "Filter by Themes",
                options=all_themes,
                default=st.session_state['filter_themes'],
                key="theme_filter_callback",
                on_change=update_theme_selection
            )
        
        with filter_row1_col2:
            # Get all available keywords from all themes
            all_keywords = []
            for theme, keywords in THEME_KEYWORDS.items():
                all_keywords.extend(keywords)
            
            # Sort keywords alphabetically for better user experience
            all_keywords = sorted(list(set(all_keywords)))
            
            # Keyword filter with callback
            st.multiselect(
                "Filter by Sub Themes",
                options=all_keywords,
                default=st.session_state['filter_keywords'],
                key="keyword_filter_callback",
                on_change=update_keyword_selection
            )
        
        with filter_row1_col3:
            # Get all unique countries from data
            all_countries = sorted(list(set([account.get('country', '') for account in data if account.get('country')])))

            # Country filter
            st.multiselect(
                "Filter by Country",
                options=all_countries,
                default=st.session_state['filter_countries'],
                key="country_filter_callback",
                on_change=update_country_selection
            )
        
        with filter_row2_col1:
            # Account filter with callback
            st.multiselect(
                "Filter by Brands",
                options=all_usernames,
                default=st.session_state['filter_accounts'],
                key="account_filter_callback",
                on_change=update_account_selection
            )
        
        with filter_row2_col2:
            # Date range filter with callback
            if min_date and max_date:
                st.date_input(
                    "Filter by Date Range",
                    value=st.session_state['filter_date_range'],
                    min_value=min_date,
                    max_value=max_date,
                    key="date_filter_callback",
                    on_change=update_date_selection
                )

        # Add buttons in a row
        button_col1, button_col2 = st.columns([1, 1])
        
        with button_col1:
            # Apply Filters button
            if st.button("Apply Filters", type="primary"):
                st.session_state['selected_themes'] = st.session_state['filter_themes']
                st.session_state['selected_keywords'] = st.session_state['filter_keywords']
                st.session_state['selected_accounts'] = st.session_state['filter_accounts']
                st.session_state['selected_countries'] = st.session_state['filter_countries']  
                st.session_state['date_range'] = st.session_state['filter_date_range']
                st.toast("Filters Applied", icon="✅")

        
        with button_col2:
            # Clear Filters button
            if st.button("Clear Filters"):
                # Clear both the filter values and the applied filters
                st.session_state['filter_themes'] = []
                st.session_state['filter_keywords'] = []
                st.session_state['filter_accounts'] = []
                st.session_state["filter_countries"] = []
                if min_date and max_date:
                    st.session_state['filter_date_range'] = (min_date, max_date)
                
                # Also clear the applied filters
                st.session_state['selected_themes'] = []
                st.session_state['selected_keywords'] = []
                st.session_state['selected_accounts'] = []
                st.session_state["selected_countries"] = []
                if min_date and max_date:
                    st.session_state['date_range'] = (min_date, max_date)
                
                st.rerun()

    # Apply filters to data based on the applied filters (not the filter input values)
    filtered_data = filter_data(
        data, 
        st.session_state['selected_themes'], 
        st.session_state['selected_keywords'],
        st.session_state['selected_accounts'],
        st.session_state['date_range'],
        st.session_state['selected_countries']
    )

    # Display the currently applied filters
    if (st.session_state['selected_themes'] or 
        st.session_state['selected_keywords'] or 
        st.session_state['selected_accounts'] or 
        st.session_state["selected_countries"] or
        (st.session_state['date_range'] and st.session_state['date_range'] != (min_date, max_date))):
        
        st.subheader("Applied Filters")
        applied_filters = []
        
        if st.session_state['selected_themes']:
            applied_filters.append(f"Themes: {', '.join(st.session_state['selected_themes'])}")
        
        if st.session_state['selected_keywords']:
            applied_filters.append(f"Keywords: {', '.join(st.session_state['selected_keywords'])}")
        
        if st.session_state['selected_accounts']:
            applied_filters.append(f"Accounts: {', '.join(st.session_state['selected_accounts'])}")

        if st.session_state["selected_countries"]:
            applied_filters.append(f"Countries: {', '.join(st.session_state['selected_countries'])}")
        
        if st.session_state['date_range'] and st.session_state['date_range'] != (min_date, max_date):
            start, end = st.session_state['date_range']
            applied_filters.append(f"Date Range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
        
        st.info(" | ".join(applied_filters))



    # Dashboard metrics with HTML tooltips (hoverable ℹ️ icon)
    total_accounts = get_total_accounts(filtered_data)
    total_countries = get_total_countries(filtered_data)
    total_posts = get_total_posts(filtered_data)
    total_engagements = get_total_engagements(filtered_data)
    avg_post_engagement = round(total_engagements / total_posts) if total_posts > 0 else 0
    reach = get_estimated_reach(filtered_data)

    st.markdown("""
    <style>
    .metric-box {
        background-color: #ffffff;
        padding: 1rem;
        border: 1px solid rgba(200, 200, 200, 0.6);
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        text-align: center;
        transition: all 0.3s ease-in-out;
        margin: 3rem 0;
        cursor: pointer;
        max-width: 15rem;
        height: 7.5rem;
    }
    .metric-title {
        font-weight: bold;
        font-size: 14px;
    }
    .metric-value {
        font-size: 22px;
        margin-top: 1rem;
    }
    .metric-tooltip {
        font-size: 14px;
        cursor: help;
        margin-left: 6px;
    }
    @media (prefers-color-scheme: dark) {
        .metric-box {
            background-color: #0E1117;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 2px 8px rgba(255, 255, 255, 0.05);
            color: #fff;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-title">Total Brands
                <span class="metric-tooltip" title="Total number of unique brand accounts analyzed.">ℹ️</span>
            </div>
            <div class="metric-value">{total_accounts}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-title">🌍 Total Countries
                <span class="metric-tooltip" title="Total number of distinct countries represented in the data.">ℹ️</span>
            </div>
            <div class="metric-value">{total_countries}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-title">📸 Total Volume
                <span class="metric-tooltip" title="Total number of posts shared by the brands.">ℹ️</span>
            </div>
            <div class="metric-value">{format_number(total_posts)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-title">💬 Total Engagements
                <span class="metric-tooltip" title="Sum of likes, comments, and shares across all posts.">ℹ️</span>
            </div>
            <div class="metric-value">{format_number(total_engagements)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-title">👥 Avg Post Engagement
                <span class="metric-tooltip" title="Average engagement per post (total engagement ÷ total posts).">ℹ️</span>
            </div>
            <div class="metric-value">{format_number(avg_post_engagement)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-title">🌟 Reach
                <span class="metric-tooltip" title="Estimated total reach across all posts by brands.">ℹ️</span>
            </div>
            <div class="metric-value">{format_number(reach)}</div>
        </div>
        """, unsafe_allow_html=True)



    # Create tabs for Overview, Themes, and Keywords
    overview_tab, theme_tab, keyword_tab = st.tabs(["🌐 Overview", "🎨 Themes", "🔍 Sub Themes"])




    with overview_tab:
        with st.spinner("Loading overview graphs...."):

            col1, col2 = st.columns(2)

            with col1:
                # --- POST TREND LINE ---
                post_counts_by_month = get_post_trend_data(filtered_data)

                if not post_counts_by_month.empty:
                    fig_post = px.line(
                        post_counts_by_month,
                        x="month",
                        y="post_count",
                        labels={"month": "Month", "post_count": "Post Count"},
                        title="Volume Trend Over Time"
                    )
                    fig_post.update_layout(xaxis_title="Month", yaxis_title="Volume")
                    st.plotly_chart(fig_post, use_container_width=True)
                else:
                    st.info("No post trend data available for the selected filters.")
            with col2:

                # --- ENGAGEMENT TREND LINE ---
                engagement_by_month = get_engagement_trend_data(filtered_data)

                if not engagement_by_month.empty:
                    fig_engagement = px.line(
                        engagement_by_month,
                        x="month",
                        y="total_engagement",
                        labels={"month": "Month", "total_engagement": "Engagement"},
                        title="Engagement Trend Over Time"
                    )
                    fig_engagement.update_layout(xaxis_title="Month", yaxis_title="Engagement")
                    st.plotly_chart(fig_engagement, use_container_width=True)
                else:
                    st.info("No engagement trend data available for the selected filters.")

            # Top 5 Accounts by Post Count
            top_accounts_df = get_top_accounts_by_post_count(filtered_data)

            if not top_accounts_df.empty:
                fig_top_accounts = px.bar(
                    top_accounts_df,
                    x='Account',
                    y='Post Count',
                    text='Post Count',
                    color='Account',
                    title="Top 10 Brands by Volume"
                )
                fig_top_accounts.update_traces(textposition='outside')
                fig_top_accounts.update_layout(
                    showlegend=False,
                    yaxis_title="Volume",
                    xaxis_title="Brand",
                    bargap=0.6  # Increase value (default is 0.2); try 0.4–0.6 for thinner bars
                )
                st.plotly_chart(fig_top_accounts, use_container_width=True, key="top_accounts_chart")
            else:
                st.info("No data available to show top accounts.")


            
            

            # Get filtered accounts
            df = get_accounts(filtered_data)

            # ⚙️ Column config for links
            column_config = {
                "Profile URL": st.column_config.LinkColumn("Profile URL", display_text="Open"),
                "External URL": st.column_config.LinkColumn("External URL", display_text="Open"),
                "Post URL": st.column_config.LinkColumn("Post URL", display_text="Open"),
            }

            # Start index from 1 instead of 0
            df.index = range(1, len(df) + 1)

            # 📋 Show filtered table
            st.dataframe(df, column_config=column_config)


    
    # Content for the Themes Tab
    with theme_tab:
        col1, col2 = st.columns(2)

        with col1:
            with st.spinner("Chart loading"):
                top_themes_df = get_top_themes(filtered_data)

                if not top_themes_df.empty:
                    fig_top_themes = px.bar(
                        top_themes_df,
                        x="Theme",
                        y="Post Count",
                        text="Post Count",
                        color="Theme",
                        color_discrete_map=THEME_COLOR_MAP,
                        title="Top 5 Themes by Post Count"
                    )
                    fig_top_themes.update_traces(textposition='outside')
                    fig_top_themes.update_layout(
                        showlegend=False,
                        yaxis_title="Volume Count",
                        xaxis_title="Theme",
                        bargap=0.5
                    )
                    st.plotly_chart(fig_top_themes, use_container_width=True)
                else:
                    st.info("No theme data available for the selected filters.")

        with col2:
            with st.spinner("Chart loading"):
                theme_dist_df = get_theme_distribution(filtered_data)

                if not theme_dist_df.empty:
                    fig_pie = px.pie(
                        theme_dist_df,
                        names="Theme",
                        values="Post Count",
                        title="Theme-wise Post Distribution",
                        hole=0.3,
                        color="Theme",
                        color_discrete_map=THEME_COLOR_MAP
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("No theme distribution data available.")

        with st.spinner("Chart loading"):        
            if not top_themes_df.empty:
                top_3 = top_themes_df.head(3)["Theme"].tolist()
                theme_trend_df = get_theme_trend_over_time(filtered_data, top_3)

                if not theme_trend_df.empty:
                    fig_line = px.line(
                        theme_trend_df,
                        x="Month",
                        y="Post Count",
                        color="Theme",
                        markers=True,
                        title="Trend of Top 3 Themes Over Time",
                        color_discrete_map=THEME_COLOR_MAP
                    )
                    fig_line.update_layout(xaxis_title="Month", yaxis_title="Volume")
                    st.plotly_chart(fig_line, use_container_width=True)
                else:
                    st.info("No trend data available for top themes.")
        
        
        col1, col2 = st.columns(2)
        
        with col1:
            with st.spinner("Chart loading"):
                # Line chart showing trends over time
                growing_trends_df = get_top_growing_themes(filtered_data)
                
                if not growing_trends_df.empty:
                    fig_growing = px.line(
                        growing_trends_df,
                        x="Month",
                        y="Post Count",
                        color="Theme",
                        markers=True,
                        title="Growth Trends Over Time"
                    )
                    fig_growing.update_layout(
                        xaxis_title="Month", 
                        yaxis_title="Volume Count",
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig_growing, use_container_width=True)
                else:
                    st.info("No growing trends data available.")
        
        with col2:

            with st.spinner("Chart loading"):
                # Prepare growth rates DataFrame with human-readable summary
                growth_rates_df = get_theme_growth_rates(filtered_data)

                if not growth_rates_df.empty:
                    # Add a human-friendly growth summary
                    def classify_growth(rate):
                        if rate >= 0.15:
                            return "🚀 Strong Growth"
                        elif rate >= 0.05:
                            return "📈 Steady Growth"
                        else:
                            return "📉 Slow Growth"
                    
                    growth_rates_df["Growth Summary"] = growth_rates_df["Growth Rate"].apply(classify_growth)

                    fig_growth_bar = px.bar(
                        growth_rates_df,
                        x="Theme",
                        y="Growth Rate",
                        text="Growth Rate",
                        color="Theme",
                        color_discrete_map=THEME_COLOR_MAP,
                        title="Theme Growth Rates (Volume/Month)",
                        hover_data={
                            "Theme": True,
                            "Growth Rate": True,
                            "Total Posts": True,
                            "R-Squared": True,
                            "Growth Summary": True
                        }
                    )

                    fig_growth_bar.update_traces(textposition='outside')
                    fig_growth_bar.update_layout(
                        showlegend=False,
                        xaxis_title="Theme",
                        yaxis_title="Avg Monthly Volume Increase",
                    )

                    st.plotly_chart(fig_growth_bar, use_container_width=True)
                    st.markdown("**ℹ️ Growth Rate = Average number of additional posts per month mentioning the theme.**")
                else:
                    st.info("No growth rate data available.")
            

            


    # Content for the Keywords Tab
    with keyword_tab:
        col1, col2 = st.columns(2)

        with col1:
            with st.spinner("Chart loading"):
                top_keywords_df = get_top_keywords(filtered_data)

                if not top_keywords_df.empty:
                    fig_top_keywords = px.bar(
                        top_keywords_df,
                        x="Keyword",
                        y="Post Count",
                        text="Post Count",
                        color="Keyword",
                        title="Top 10 Sub Themes by Post Count"
                    )
                    fig_top_keywords.update_traces(textposition='outside')
                    fig_top_keywords.update_layout(
                        showlegend=False,
                        yaxis_title="Volume Count",
                        xaxis_title="Keyword",
                        bargap=0.5,
                    )
                    st.plotly_chart(fig_top_keywords, use_container_width=True)
                else:
                    st.info("No keyword data available for the selected filters.")

        with col2:
            with st.spinner("Chart loading"):
                keyword_dist_df = get_keyword_distribution(filtered_data)

                if not keyword_dist_df.empty:
                    fig_pie = px.pie(
                        keyword_dist_df,
                        names="Keyword",
                        values="Post Count",
                        title="Sub Theme-wise Volume Distribution",
                        hole=0.3,
                        color="Keyword"
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("No keyword distribution data available.")


        with st.spinner("Chart loading"):        
            if not top_keywords_df.empty:
                top_5 = top_keywords_df.head(5)["Keyword"].tolist()
                keyword_trend_df = get_keyword_trend_over_time(filtered_data, top_5)

                if not keyword_trend_df.empty:
                    fig_line = px.line(
                        keyword_trend_df,
                        x="Month",
                        y="Post Count",
                        color="Keyword",
                        markers=True,
                        title="Trend of Top 5 Sub Thems Over Time"
                    )
                    fig_line.update_layout(xaxis_title="Month", yaxis_title="Volume")
                    st.plotly_chart(fig_line, use_container_width=True)
                else:
                    st.info("No trend data available for top keywords.")
        
        
        col1, col2 = st.columns(2)
        
        with col1:
            with st.spinner("Chart loading"):
                # Line chart showing trends over time
                growing_keywords_df = get_top_growing_keywords(filtered_data)
                
                if not growing_keywords_df.empty:
                    fig_growing = px.line(
                        growing_keywords_df,
                        x="Month",
                        y="Post Count",
                        color="Keyword",
                        markers=True,
                        title="Sub Themes Growth Trends Over Time"
                    )
                    fig_growing.update_layout(
                        xaxis_title="Month", 
                        yaxis_title="Volume Count",
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig_growing, use_container_width=True)
                else:
                    st.info("No growing keyword trends data available.")
        
        with col2:
            with st.spinner("Chart loading"):
                # Prepare growth rates DataFrame with human-readable summary
                growth_rates_df = get_keyword_growth_rates(filtered_data)

                if not growth_rates_df.empty:
                    # Add a human-friendly growth summary
                    def classify_growth(rate):
                        if rate >= 0.15:
                            return "🚀 Strong Growth"
                        elif rate >= 0.05:
                            return "📈 Steady Growth"
                        else:
                            return "📉 Slow Growth"
                    
                    growth_rates_df["Growth Summary"] = growth_rates_df["Growth Rate"].apply(classify_growth)

                    fig_growth_bar = px.bar(
                        growth_rates_df,
                        x="Keyword",
                        y="Growth Rate",
                        text="Growth Rate",
                        color="Keyword",
                        title="Sub Themes Growth Rates (Volume/Month)",
                        hover_data={
                            "Keyword": True,
                            "Growth Rate": True,
                            "Total Posts": True,
                            "R-Squared": True,
                            "Growth Summary": True
                        }
                    )

                    fig_growth_bar.update_traces(textposition='outside')
                    fig_growth_bar.update_layout(
                        showlegend=False,
                        xaxis_title="Sub Theme",
                        yaxis_title="Avg Monthly Volume Increase",
                        xaxis_tickangle=45
                    )

                    st.plotly_chart(fig_growth_bar, use_container_width=True)
                    st.markdown("**ℹ️ Growth Rate = Average number of additional posts per month mentioning the keyword.**")
                else:
                    st.info("No keyword growth rate data available.")