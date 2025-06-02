import re
import json
import hashlib
from urllib.parse import quote_plus
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime, date
from collections import Counter
from rapidfuzz import fuzz
from collections import defaultdict
from scipy.stats import linregress
import numpy as np




@st.cache_data
def get_data():
    try:
        with open("translated_output.json", "r", encoding='utf-8') as f:
            data = json.load(f)
        print("Loaded data from JSON file")
        return data
    except Exception as e:
        print(f"Failed to load data from JSON: {e}")
        return []



def get_date_range(data):
    """
    Get minimum and maximum dates from all posts in the data
    
    Args:
        data (list): List of account data
        
    Returns:
        tuple: (min_date, max_date) as datetime.date objects, or (None, None) if no valid dates
    """
    all_dates = []
    
    for account in data:
        for post in account.get("posts", []):
            upload_date_str = post.get("upload_date")
            if upload_date_str:
                try:
                    upload_date = datetime.strptime(upload_date_str, "%Y-%m-%d").date()
                    all_dates.append(upload_date)
                except ValueError:
                    pass  # Skip malformed dates
    
    if all_dates:
        return min(all_dates), max(all_dates)
    else:
        return None, None


def filter_data(data, selected_themes=None, selected_keywords=None, selected_accounts=None, date_range=None, selected_countries=None):
    """
    Filter the data based on selected themes, keywords, accounts, date range, and countries
    """
    # If no filters applied, return original data
    if not selected_themes and not selected_keywords and not selected_accounts and not date_range and not selected_countries:
        return data
        
    filtered_data = []
    
    for account in data:
        username = account.get("username", "")
        country = account.get("country", "")
        
        # Filter by account
        account_match = True
        if selected_accounts:
            account_match = username in selected_accounts
        
        # Filter by country
        country_match = True
        if selected_countries:
            country_match = country in selected_countries
        
        if not (account_match and country_match):
            continue
        
        filtered_account = account.copy()
        filtered_posts = []
        
        for post in account.get("posts", []):
            caption = (post.get("caption") or "").lower()
            hashtags = [h.lower() for h in post.get("hashtags", [])]
            text_blob = caption + " " + " ".join(hashtags)


            
            # Check date range
            date_match = True
            if date_range and isinstance(date_range, tuple) and len(date_range) == 2:
                upload_date_str = post.get("upload_date")
                if upload_date_str:
                    try:
                        upload_date = datetime.strptime(upload_date_str, "%Y-%m-%d").date()
                        start_date, end_date = date_range
                        if isinstance(start_date, datetime):
                            start_date = start_date.date()
                        if isinstance(end_date, datetime):
                            end_date = end_date.date()
                        date_match = start_date <= upload_date <= end_date
                    except ValueError:
                        date_match = False
                else:
                    date_match = False
            
            if not date_match:
                continue

            # Check themes
            theme_match = True
            if selected_themes:
                post_themes = []
                for theme, keywords in THEME_KEYWORDS.items():
                    if any(keyword.lower() in text_blob for keyword in keywords):
                        post_themes.append(theme)
                
                if not post_themes:
                    theme_match = True
                elif any(theme in selected_themes for theme in post_themes):
                    theme_match = True
                else:
                    theme_match = False

            # Check keywords
            keyword_match = True
            if selected_keywords:
                if not any(keyword.lower() in text_blob for keyword in selected_keywords):
                    keyword_match = False
            
            if theme_match and keyword_match:
                filtered_posts.append(post)
        
        if filtered_posts:
            filtered_account["posts"] = filtered_posts
            filtered_data.append(filtered_account)
    
    return filtered_data



def get_total_accounts(data):
    return len(data)


def get_total_engagements(data):
    total_engagements = 0
    for account in data:
        for post in account.get("posts", []):
            total_engagements += post.get("number_of_likes", 0) or 0
            total_engagements += post.get("number_of_comments", 0) or 0
            total_engagements += post.get("video_view_count", 0) or 0

    return total_engagements


def get_total_posts(data):
    total_posts = 0
    for account in data:
        total_posts += len(account.get("posts", []))

    return total_posts


# Heuristic: assume ~10% of followers see a post + a boost from engagement
def estimate_post_reach(post, followers):
    likes = post.get("number_of_likes", 0) or 0
    comments = post.get("number_of_comments", 0) or 0
    views = post.get("video_view_count", 0) or 0

    engagement = likes + comments + views
    return (0.1 * followers) + (0.05 * engagement)


def get_estimated_reach(data):
    estimated_reach = 0
    for account in data:
        followers = account.get("followers", 0)
        for post in account.get("posts", []):
            estimated_reach += estimate_post_reach(post, followers)
    return int(estimated_reach)


def get_post_trend_data(data):
    post_dates = []
    for account in data:
        for post in account.get("posts", []):
            upload_date_str = post.get("upload_date")
            if upload_date_str:
                try:
                    upload_date = datetime.strptime(upload_date_str, "%Y-%m-%d").date()
                    post_dates.append(upload_date)
                except ValueError:
                    pass  # skip malformed dates

    # If no posts match the filters, return an empty dataframe
    if not post_dates:
        return pd.DataFrame(columns=["month", "post_count"])
        
    # Step 2: Create DataFrame and convert the date column to datetime
    df_posts = pd.DataFrame(post_dates, columns=["date"])
    df_posts["date"] = pd.to_datetime(df_posts["date"])  # Ensure 'date' column is datetime type

    # Extract month-year for grouping
    df_posts["month"] = df_posts["date"].dt.to_period("M").dt.to_timestamp()

    # Group by month and count posts
    post_counts_by_month = df_posts.groupby("month").size().reset_index(name="post_count")

    return post_counts_by_month


def get_engagement_trend_data(data):
    engagement_data = []
    for account in data:
        for post in account.get("posts", []):
            upload_date_str = post.get("upload_date")
            likes = post.get("number_of_likes", 0) or 0
            comments = post.get("number_of_comments", 0) or 0
            video_view_count = post.get("video_view_count", 0) or 0
            
            if upload_date_str:
                try:
                    upload_date = datetime.strptime(upload_date_str, "%Y-%m-%d").date()
                    total_engagement = likes + comments + video_view_count  # Sum of likes, comments, and video views
                    engagement_data.append((upload_date, total_engagement))
                except ValueError:
                    pass  # skip malformed dates

    # If no engagement data matches the filters, return an empty dataframe
    if not engagement_data:
        return pd.DataFrame(columns=["month", "total_engagement"])
        
    # Step 2: Create DataFrame and convert the date column to datetime
    df_engagement = pd.DataFrame(engagement_data, columns=["date", "engagement"])
    df_engagement["date"] = pd.to_datetime(df_engagement["date"])  # Ensure 'date' column is datetime type

    # Extract month-year for grouping
    df_engagement["month"] = df_engagement["date"].dt.to_period("M").dt.to_timestamp()

    # Group by month and calculate total engagement for each month
    engagement_by_month = df_engagement.groupby("month")["engagement"].sum().reset_index(name="total_engagement")

    return engagement_by_month


THEME_KEYWORDS = {
    "Sustainability": [
        "Solar System",
        "Energy-efficient",
        "Solar Energy",
        "Eco-friendly",
        "Renewable Energy",
        "Sustainable materials",
        "Water saving",
        "LEED certification",
        "Green Building",
        "Passive design",
        "Rainwater harvesting",
        "Greywater system",
        "Composting facilities",
        "Energy star products",
        "Solar panels",
        "Energy-efficient appliances",
        "LED lighting",
        "Low-flow fixtures",
        "Programmable thermostats",
        "Efficient insulation",
        "Energy-efficient windows",
        "Sustainable flooring",
        "Water-saving faucets",
        "Water-saving showerheads",
        "LEED",
        "Recycled content",
        "Salvaged wood",
        "Cork flooring",
        "Hemp insulation",
        "Sustainable concrete",
        "Rammed earth walls",
        "Bamboo flooring",
        "Clay plaster",
        "Sustainable Energy"
    ],
    "Smart Home Technology": [
        "Home Automation",
        "Voice control",
        "Smart Sensors",
        "Smart Connectivity",
        "Remote access",
        "Smart security",
        "Energy monitoring",
        "App-based control",
        "Smart locks",
        "Energy management systems",
        "Voice assistant",
        "Smart meters",
        "Automated lighting",
        "Smart blinds",
        "Smart shades",
        "Remote surveillance",
        "Motion sensors",
        "Home energy monitoring",
        "Remote camera",
        "Smart home features",
        "Virtual concierge app",
        "Smart Home"
    ],
    "Health & Wellness Spaces": [
        "Meditation rooms",
        "Spa facilities",
        "Health club",
        "Wellness center",
        "Wellness classes",
        "Hydrotherapy",
        "Saunas",
        "Massage therapy",
        "Nutritional counseling",
        "General Wellness"
    ],
    "House Features": [
        "Open floor plan",
        "Granite countertops",
        "Stainless steel appliances",
        "Hardwood floors",
        "Walk-in closets",
        "Master suite",
        "Soaking tub",
        "Fireplace",
        "Outdoor living space",
        "Attached garage",
        "High ceilings",
        "Pantry",
        "Laundry room",
        "Bonus room",
        "Covered patio",
        "Central air conditioning",
        "Kitchen island",
        "Breakfast bar",
        "Walk-in pantry",
        "Recessed lighting",
        "Crown molding",
        "Home office",
        "Mudroom",
        "Wine cellar",
        "Wine fridge",
        "Jetted bathtub",
        "Home theater",
        "Storage space",
        "Built-in shelving",
        "Media room",
        "Sunroom",
        "Wet bar",
        "Gas fireplace",
        "Heated floors",
        "Vaulted ceilings",
        "Custom cabinetry",
        "Enclosed porch",
        "Nanny room",
        "Spacious living area",
        "Dining area",
        "Top notch features",
        "Exquisite space",
        "Terrace",
        "Balcony",
        "Large windows",
        "Modern kitchen",
        "Open-plan kitchen",
        "Open-plan living",
        "Wood floors",
        "Cycle storage",
        "Open-plan reception",
        "Private garden",
        "Basement Access",
        "Roof Access"
    ],
    "Interior Style": [
        "Luxury flooring",
        "Neutral color palette",
        "Architectural details",
        "Statement feature walls",
        "Tile work",
        "Trendy backsplash designs",
        "Cozy",
        "Attention to detail",
        "Modern Interiors",
        "Classic Interiors",
        "Bohemian Interiors",
        "Contemporary Interiors",
        "Minimalist Interiors",
        "Industrial Interiors",
        "Farmhouse",
        "Scandinavian Interiors",
        "Mediterranean Interiors",
        "Victorian Interiors",
        "Craftsman",
        "Mid-Century Modern Interiors",
        "Eclectic Interiors",
        "Transitional Interiors",
        "Rustic Interiors",
        "Coastal Interiors",
        "Colonial Interiors",
        "Art Deco",
        "Tudor Interiors",
        "Asian-inspired Interiors",
        "Luxury design",
        "Luxury interior",
        "Timeless Interiors",
        "Prestigious Brands",
        "Award-winning Interiors",
        "Luxurious décor",
        "Chic Interiors",
        "Semi-custom Interiors",
        "Custom homes",
        "General Interior Design"
    ],
    "Sports & Recreation Facilities": [
        "Tennis",
        "Basketball",
        "Football",
        "Baseball",
        "Volleyball",
        "Swimming",
        "Fitness center",
        "Running track",
        "Golf Club",
        "Yoga",
        "Cycling paths",
        "Outdoor gym",
        "CrossFit area",
        "Climbing wall",
        "Gym",
        "Dance studio",
        "Pool",
        "Aerobics room",
        "Personal training",
        "Billiards room",
        "Sports courts",
        "Cycling trail",
        "Fitness classes",
        "Group sports tournaments",
        "Group workout",
        "Bike lanes",
        "Bike racks",
        "Running trails",
        "General fitness facilities"
    ],
    "Safety": [
        "Gated community",
        "Gated entry",
        "Security patrols",
        "Access control",
        "Security cameras",
        "Emergency call",
        "Neighborhood watch",
        "On-site security",
        "Perimeter fencing",
        "Motion-sensor lighting",
        "Alarm systems",
        "Fire safety",
        "Visitor management",
        "Intercom system",
        "Crime prevention",
        "Emergency response",
        "Evacuation plan",
        "Safety meetings",
        "Controlled access",
        "Secure parking",
        "Well-lit pathways",
        "General security",
        "General safety",
        "Security alarms"
    ],
    "Entertainment": [
        "Gaming",
        "Events",
        "Game room",
        "Movie theater",
        "Playground",
        "Picnic area",
        "BBQ grills",
        "BBQ area",
        "Social events",
        "Craft nights",
        "Community parties",
        "Live music",
        "Outdoor concerts",
        "Holiday celebrations",
        "Cooking classes",
        "Outdoor movie nights",
        "Pool parties",
        "Art workshops",
        "Cultural festivals",
        "Talent shows",
        "Cultural events",
        "Cinema",
        "Comedy shows",
        "Family game nights",
        "Coffee bar",
        "Bars",
        "Cafes",
        "Lounge",
        "Non-alcoholic bar",
        "General entertainment"
    ],
    "Working Space": [
        "Co-working space",
        "Business center",
        "Conference rooms",
        "Private offices",
        "High-speed internet",
        "Printing facility",
        "Photocopying facility",
        "Workstations",
        "Quiet zones",
        "Lounge areas",
        "Meeting pods",
        "Collaborative workspaces",
        "Networking events",
        "Business workshops",
        "Seminars",
        "Workspaces"
    ],
    "Greenery": [
        "Garden",
        "Parks",
        "Nature trails",
        "Green belts",
        "Arboretum",
        "Botanical gardens",
        "Green rooftops",
        "Urban forests",
        "Rain gardens",
        "Meditation gardens",
        "Butterfly gardens",
        "Greenery",
        "Green space",
        "Shade trees",
        "Flowering gardens",
        "Orchards",
        "Community orchards",
        "Tree-lined streets",
        "Rooftop gardens",
        "Trees",
        "Flowers",
        "Park",
        "Green vibes",
        "Green living",
        "Nature",
        "Lagoon",
        "River"
    ],
    "Pet-friendly Amenities": [
        "Dog park",
        "Pet grooming",
        "Pet trails",
        "Pet waste stations",
        "Pet clinic",
        "Pet events",
        "Pet spa",
        "Pet friendly"
    ],
    "Accessibility for People of Determination": [
        "Accessible entrances",
        "Wheelchair ramps",
        "Elevators",
        "Handicap parking",
        "Roll-in showers",
        "Lowered countertops",
        "Accessible pathways",
        "Visual fire alarms",
        "Hearing loop systems",
        "Accessible fitness equipment",
        "Accessible swimming pool",
        "Disability-friendly landscaping"
    ],
    "Children Amenities": [
        "Playground",
        "Splash pad",
        "Kids' club",
        "Children's pool",
        "Nursery",
        "Outdoor play area",
        "Childcare center",
        "Kid-friendly events",
        "Babysitting services",
        "Scooter lanes",
        "Children's library",
        "Storytime sessions",
        "Kid-friendly trails",
        "Summer camps",
        "Teen center",
        "School bus stop",
        "Kid-friendly facilities"
    ],
    "Parking Amenities": [
        "Garage",
        "Covered parking",
        "Underground parking",
        "Driveway parking",
        "Carport",
        "Assigned parking spaces",
        "Guest parking",
        "Electric vehicle charging stations",
        "Secured parking",
        "Valet parking",
        "Bicycle storage",
        "Oversized garage",
        "Tandem parking",
        "Remote-controlled garage door",
        "Garage storage cabinets",
        "On-street parking",
        "Parking permits",
        "Car wash stations",
        "Parking space"
    ],
    "Views": [
        "Panoramic views",
        "City skyline",
        "Mountain view",
        "Waterfront",
        "Park views",
        "Golf course view",
        "Lake view",
        "Oceanfront",
        "Forest views",
        "Sunset views",
        "Sunrise views",
        "Valley views",
        "Nature vistas",
        "River views",
        "Coastal panoramas",
        "Scenic overlooks",
        "Stunning views",
        "Lagoon views",
        "Golf views",
        "Nature view",
        "Beachfront",
        "Burj Khalifa view"
    ],
    "Location Connectivity & Access": [
        "Quick access",
        "Highway access",
        "School accessibility",
        "Accessibility to malls",
        "City centre",
        "Walking distances",
        "Minutes’ drive away",
        "Good connectivity",
        "Metro accessibility",
        "Train accessibility",
        "Bus accessibility",
        "Prime location"
    ],
    "LifeStyle Messaging & Identity": [
        "Luxury",
        "Modern living",
        "Convenience living",
        "City living",
        "Built for perfection",
        "Elegant ambiance",
        "Prime living",
        "Elegant",
        "First-class",
        "Comfort living",
        "Beach living",
        "World-class amenities",
        "Modern lifestyles",
        "Luxurious living",
        "Urban lifestyle",
        "Comfortable lifestyle",
        "Prestigious"
    ],
    "Types of residential properties": [
        "Townhouse",
        "Penthouse",
        "Apartment",
        "Glasshouse",
        "Single-family home",
        "Duplex",
        "Villa",
        "Cottage",
        "Bungalow",
        "Loft",
        "Studio apartment",
        "Mobile home",
        "Mansion",
        "Ranch-style house",
        "Row house",
        "Tiny house",
        "Cluster home"
    ],
    "Branded Developments": [
        "Branded launches",
        "Branded residences",
        "Branded projects",
        "Branded community",
        "Branded communities",
        "Armani",
        "Fendi",
        "Missoni",
        "Versace",
        "Bulgari",
        "Baccarat",
        "Porsche",
        "Bentley",
        "Bugatti",
        "Aston Martin"
    ]
}






def get_accounts(data):
    rows = []

    for account in data:
        username = account.get("username", "")
        profile_url = f"https://www.instagram.com/{username}"

        for post in account.get("posts", []):
            post_url = post.get("url", "")  # Assuming each post has a `url` field

            rows.append({
                "User Name": username,
                "Full Name": account.get("full_name", ""),
                "Followers": account.get("followers", 0),
                "Following": account.get("following", 0),
                "Countries": account.get("country", ""),
                "Post URL": post_url,  # Each post gets its own URL in a separate row
                "Profile URL": profile_url,
                "External URL": account.get("external_url", ""),
            })
    
    # Convert the rows into a DataFrame
    df = pd.DataFrame(rows)
    return df


def format_number(num):
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    else:
        return str(num)



def get_total_countries(data):
    countries = set()

    for account in data:
        country = account.get("country", "")
        if country:
            countries.add(country)

    return len(countries)


def get_top_accounts_by_post_count(data, top_n=10):
    account_post_counts = []

    for account in data:
        username = account.get("username", "")
        post_count = len(account.get("posts", []))
        account_post_counts.append((username, post_count))

    sorted_accounts = sorted(account_post_counts, key=lambda x: x[1], reverse=True)[:top_n]
    
    return pd.DataFrame(sorted_accounts, columns=["Account", "Post Count"])



# Define consistent theme colors
THEME_COLOR_MAP = {
    theme: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)]
    for i, theme in enumerate(THEME_KEYWORDS.keys())
}

@st.cache_data(show_spinner=False)
def get_top_themes(data, top_n=5, threshold=60):
    theme_counter = Counter()

    for account in data:
        for post in account.get("posts", []):
            caption = post.get("caption", "")
            hashtags = " ".join(post.get("hashtags", []))
            text_blob = f"{caption} {hashtags}".lower()


            for theme, keywords in THEME_KEYWORDS.items():
                if any(keyword.lower() in text_blob and fuzz.partial_ratio(keyword.lower(), text_blob) >= threshold for keyword in keywords):
                    theme_counter[theme] += 1

    top_themes = theme_counter.most_common(top_n)
    return pd.DataFrame(top_themes, columns=["Theme", "Post Count"])

@st.cache_data(show_spinner=False)
def get_theme_distribution(data, threshold=60):
    theme_counter = Counter()

    for account in data:
        for post in account.get("posts", []):
            caption = post.get("caption", "")
            hashtags = " ".join(post.get("hashtags", []))
            text_blob = f"{caption} {hashtags}".lower()

            for theme, keywords in THEME_KEYWORDS.items():
                if any(keyword.lower() in text_blob and fuzz.partial_ratio(keyword.lower(), text_blob) >= threshold for keyword in keywords):
                    theme_counter[theme] += 1

    return pd.DataFrame(theme_counter.items(), columns=["Theme", "Post Count"])

@st.cache_data(show_spinner=False)
def get_theme_trend_over_time(data, _top_themes, threshold=60):
    theme_monthly_counts = defaultdict(lambda: defaultdict(int))

    for account in data:
        for post in account.get("posts", []):
            caption = post.get("caption", "")
            hashtags = " ".join(post.get("hashtags", []))
            text_blob = f"{caption} {hashtags}".lower()
            upload_date = post.get("upload_date")

            if not upload_date:
                continue

            try:
                month = datetime.strptime(upload_date, "%Y-%m-%d").strftime("%Y-%m")
            except ValueError:
                continue

            for theme in _top_themes:
                keywords = THEME_KEYWORDS.get(theme, [])
                if any(keyword.lower() in text_blob and fuzz.partial_ratio(keyword.lower(), text_blob) >= threshold for keyword in keywords):
                    theme_monthly_counts[theme][month] += 1

    records = []
    for theme, monthly_data in theme_monthly_counts.items():
        for month, count in monthly_data.items():
            records.append({"Theme": theme, "Month": month, "Post Count": count})

    df = pd.DataFrame(records)
    df["Month"] = pd.to_datetime(df["Month"])
    return df.sort_values("Month")




@st.cache_data(show_spinner=True)
def get_top_growing_themes(data, top_n=5, threshold=60):
    """
    Calculate growth trends for themes and return top growing themes
    """
    theme_monthly_counts = defaultdict(lambda: defaultdict(int))

    # Collect monthly data for all themes
    for account in data:
        for post in account.get("posts", []):
            caption = post.get("caption", "")
            hashtags = " ".join(post.get("hashtags", []))
            text_blob = f"{caption} {hashtags}".lower()
            upload_date = post.get("upload_date")

            if not upload_date:
                continue

            try:
                month = datetime.strptime(upload_date, "%Y-%m-%d").strftime("%Y-%m")
            except ValueError:
                continue

            for theme, keywords in THEME_KEYWORDS.items():
                if any(keyword.lower() in text_blob and fuzz.partial_ratio(keyword.lower(), text_blob) >= threshold for keyword in keywords):
                    theme_monthly_counts[theme][month] += 1

    # Calculate growth rates for each theme
    theme_growth_rates = {}
    
    for theme, monthly_data in theme_monthly_counts.items():
        if len(monthly_data) < 2:  # Need at least 2 months for trend calculation
            continue
            
        months = sorted(monthly_data.keys())
        counts = [monthly_data[month] for month in months]
        
        # Convert months to numeric values for regression
        month_nums = list(range(len(months)))
        
        if len(month_nums) >= 2 and sum(counts) > 0:  # Ensure we have data
            # Use linear regression to calculate growth trend
            slope, intercept, r_value, p_value, std_err = linregress(month_nums, counts)
            
            # Store growth rate (slope) and R-squared for filtering
            theme_growth_rates[theme] = {
                'growth_rate': slope,
                'r_squared': r_value ** 2,
                'total_posts': sum(counts)
            }

    # Filter themes with meaningful growth (more lenient criteria)
    growing_themes = {
        theme: data for theme, data in theme_growth_rates.items()
        if data['growth_rate'] > 0 and data['total_posts'] >= 3
    }
    
    # Sort by growth rate and get top N
    top_growing = sorted(growing_themes.items(), key=lambda x: x[1]['growth_rate'], reverse=True)[:top_n]
    
    # Prepare data for the trend chart
    records = []
    for theme, _ in top_growing:
        monthly_data = theme_monthly_counts[theme]
        for month, count in monthly_data.items():
            records.append({"Theme": theme, "Month": month, "Post Count": count})

    if records:
        df = pd.DataFrame(records)
        df["Month"] = pd.to_datetime(df["Month"])
        return df.sort_values("Month")
    else:
        return pd.DataFrame(columns=["Theme", "Month", "Post Count"])


# Add this additional function to developer_data.py for the bar chart

@st.cache_data(show_spinner=False)
def get_theme_growth_rates(data, top_n=5, threshold=60):
    """
    Get growth rates for themes to display in a bar chart
    """
    theme_monthly_counts = defaultdict(lambda: defaultdict(int))

    # Collect monthly data for all themes
    for account in data:
        for post in account.get("posts", []):
            caption = post.get("caption", "")
            hashtags = " ".join(post.get("hashtags", []))
            text_blob = f"{caption} {hashtags}".lower()
            upload_date = post.get("upload_date")

            if not upload_date:
                continue

            try:
                month = datetime.strptime(upload_date, "%Y-%m-%d").strftime("%Y-%m")
            except ValueError:
                continue

            for theme, keywords in THEME_KEYWORDS.items():
                if any(keyword.lower() in text_blob and fuzz.partial_ratio(keyword.lower(), text_blob) >= threshold for keyword in keywords):
                    theme_monthly_counts[theme][month] += 1

    # Calculate growth rates for each theme
    theme_growth_data = []
    
    for theme, monthly_data in theme_monthly_counts.items():
        if len(monthly_data) < 2:
            continue
            
        months = sorted(monthly_data.keys())
        counts = [monthly_data[month] for month in months]
        month_nums = list(range(len(months)))
        
        if len(month_nums) >= 2 and sum(counts) > 0:
            slope, intercept, r_value, p_value, std_err = linregress(month_nums, counts)
            
            theme_growth_data.append({
                'Theme': theme,
                'Growth Rate': round(slope, 2),
                'Total Posts': sum(counts),
                'R-Squared': round(r_value ** 2, 3)
            })

    # Filter and sort
    growing_themes = [
        item for item in theme_growth_data 
        if item['Growth Rate'] > 0 and item['Total Posts'] >= 3
    ]
    
    # Sort by growth rate and get top N
    growing_themes = sorted(growing_themes, key=lambda x: x['Growth Rate'], reverse=True)[:top_n]
    
    return pd.DataFrame(growing_themes)





@st.cache_data(show_spinner=False)
def get_top_keywords(data, top_n=10, threshold=60):
    """
    Get top keywords from all posts using predefined THEME_KEYWORDS
    """
    keyword_counter = Counter()

    # Flatten all keywords from THEME_KEYWORDS
    all_keywords = []
    for theme, keywords in THEME_KEYWORDS.items():
        all_keywords.extend(keywords)

    for account in data:
        for post in account.get("posts", []):
            caption = post.get("caption", "")
            hashtags = " ".join(post.get("hashtags", []))
            text_blob = f"{caption} {hashtags}".lower()

            for keyword in all_keywords:
                if keyword.lower() in text_blob and fuzz.partial_ratio(keyword.lower(), text_blob) >= threshold:
                    keyword_counter[keyword] += 1

    top_keywords = keyword_counter.most_common(top_n)
    return pd.DataFrame(top_keywords, columns=["Keyword", "Post Count"])

@st.cache_data(show_spinner=False)
def get_keyword_distribution(data, top_n=15, threshold=60):
    """
    Get keyword distribution for pie chart (top 15 to avoid overcrowding)
    """
    keyword_counter = Counter()

    # Flatten all keywords from THEME_KEYWORDS
    all_keywords = []
    for theme, keywords in THEME_KEYWORDS.items():
        all_keywords.extend(keywords)

    for account in data:
        for post in account.get("posts", []):
            caption = post.get("caption", "")
            hashtags = " ".join(post.get("hashtags", []))
            text_blob = f"{caption} {hashtags}".lower()

            for keyword in all_keywords:
                if keyword.lower() in text_blob and fuzz.partial_ratio(keyword.lower(), text_blob) >= threshold:
                    keyword_counter[keyword] += 1

    top_keywords = keyword_counter.most_common(top_n)
    return pd.DataFrame(top_keywords, columns=["Keyword", "Post Count"])

@st.cache_data(show_spinner=False)
def get_keyword_trend_over_time(data, _top_keywords, threshold=60):
    """
    Get trend of specific keywords over time
    """
    keyword_monthly_counts = defaultdict(lambda: defaultdict(int))

    for account in data:
        for post in account.get("posts", []):
            caption = post.get("caption", "")
            hashtags = " ".join(post.get("hashtags", []))
            text_blob = f"{caption} {hashtags}".lower()
            upload_date = post.get("upload_date")

            if not upload_date:
                continue

            try:
                month = datetime.strptime(upload_date, "%Y-%m-%d").strftime("%Y-%m")
            except ValueError:
                continue

            for keyword in _top_keywords:
                if keyword.lower() in text_blob and fuzz.partial_ratio(keyword.lower(), text_blob) >= threshold:
                    keyword_monthly_counts[keyword][month] += 1

    records = []
    for keyword, monthly_data in keyword_monthly_counts.items():
        for month, count in monthly_data.items():
            records.append({"Keyword": keyword, "Month": month, "Post Count": count})

    if records:
        df = pd.DataFrame(records)
        df["Month"] = pd.to_datetime(df["Month"])
        return df.sort_values("Month")
    else:
        return pd.DataFrame(columns=["Keyword", "Month", "Post Count"])

@st.cache_data(show_spinner=False)
def get_top_growing_keywords(data, top_n=5, threshold=60):
    """
    Calculate growth trends for keywords and return top growing keywords
    """
    keyword_monthly_counts = defaultdict(lambda: defaultdict(int))

    # Flatten all keywords from THEME_KEYWORDS
    all_keywords = []
    for theme, keywords in THEME_KEYWORDS.items():
        all_keywords.extend(keywords)

    # Collect monthly data for all keywords
    for account in data:
        for post in account.get("posts", []):
            caption = post.get("caption", "")
            hashtags = " ".join(post.get("hashtags", []))
            text_blob = f"{caption} {hashtags}".lower()
            upload_date = post.get("upload_date")

            if not upload_date:
                continue

            try:
                month = datetime.strptime(upload_date, "%Y-%m-%d").strftime("%Y-%m")
            except ValueError:
                continue

            for keyword in all_keywords:
                if keyword.lower() in text_blob and fuzz.partial_ratio(keyword.lower(), text_blob) >= threshold:
                    keyword_monthly_counts[keyword][month] += 1

    # Calculate growth rates for each keyword
    keyword_growth_rates = {}
    
    for keyword, monthly_data in keyword_monthly_counts.items():
        if len(monthly_data) < 2:  # Need at least 2 months for trend calculation
            continue
            
        months = sorted(monthly_data.keys())
        counts = [monthly_data[month] for month in months]
        
        # Convert months to numeric values for regression
        month_nums = list(range(len(months)))
        
        if len(month_nums) >= 2 and sum(counts) > 0:  # Ensure we have data
            # Use linear regression to calculate growth trend
            slope, intercept, r_value, p_value, std_err = linregress(month_nums, counts)
            
            # Store growth rate (slope) and R-squared for filtering
            keyword_growth_rates[keyword] = {
                'growth_rate': slope,
                'r_squared': r_value ** 2,
                'total_posts': sum(counts)
            }

    # Filter keywords with meaningful growth
    growing_keywords = {
        keyword: data for keyword, data in keyword_growth_rates.items()
        if data['growth_rate'] > 0 and data['total_posts'] >= 3  # Lower threshold since using predefined keywords
    }
    
    # Sort by growth rate and get top N
    top_growing = sorted(growing_keywords.items(), key=lambda x: x[1]['growth_rate'], reverse=True)[:top_n]
    
    # Prepare data for the trend chart
    records = []
    for keyword, _ in top_growing:
        monthly_data = keyword_monthly_counts[keyword]
        for month, count in monthly_data.items():
            records.append({"Keyword": keyword, "Month": month, "Post Count": count})

    if records:
        df = pd.DataFrame(records)
        df["Month"] = pd.to_datetime(df["Month"])
        return df.sort_values("Month")
    else:
        return pd.DataFrame(columns=["Keyword", "Month", "Post Count"])

@st.cache_data(show_spinner=False)
def get_keyword_growth_rates(data, top_n=8, threshold=60):
    """
    Get growth rates for keywords to display in a bar chart
    """
    keyword_monthly_counts = defaultdict(lambda: defaultdict(int))

    # Flatten all keywords from THEME_KEYWORDS
    all_keywords = []
    for theme, keywords in THEME_KEYWORDS.items():
        all_keywords.extend(keywords)

    # Collect monthly data for all keywords
    for account in data:
        for post in account.get("posts", []):
            caption = post.get("caption", "")
            hashtags = " ".join(post.get("hashtags", []))
            text_blob = f"{caption} {hashtags}".lower()
            upload_date = post.get("upload_date")

            if not upload_date:
                continue

            try:
                month = datetime.strptime(upload_date, "%Y-%m-%d").strftime("%Y-%m")
            except ValueError:
                continue

            for keyword in all_keywords:
                if keyword.lower() in text_blob and fuzz.partial_ratio(keyword.lower(), text_blob) >= threshold:
                    keyword_monthly_counts[keyword][month] += 1

    # Calculate growth rates for each keyword
    keyword_growth_data = []
    
    for keyword, monthly_data in keyword_monthly_counts.items():
        if len(monthly_data) < 2:
            continue
            
        months = sorted(monthly_data.keys())
        counts = [monthly_data[month] for month in months]
        month_nums = list(range(len(months)))
        
        if len(month_nums) >= 2 and sum(counts) > 0:
            slope, intercept, r_value, p_value, std_err = linregress(month_nums, counts)
            
            keyword_growth_data.append({
                'Keyword': keyword,
                'Growth Rate': round(slope, 2),
                'Total Posts': sum(counts),
                'R-Squared': round(r_value ** 2, 3)
            })

    # Filter and sort
    growing_keywords = [
        item for item in keyword_growth_data 
        if item['Growth Rate'] > 0 and item['Total Posts'] >= 3  # Lower threshold since using predefined keywords
    ]
    
    # Sort by growth rate and get top N
    growing_keywords = sorted(growing_keywords, key=lambda x: x['Growth Rate'], reverse=True)[:top_n]
    
    return pd.DataFrame(growing_keywords)