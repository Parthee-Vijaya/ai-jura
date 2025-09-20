"""
Streamlit Frontend for The Judge - AI Compliance Platform
"""

import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any
import time

# Configure Streamlit page
st.set_page_config(
    page_title="The Judge - AI Compliance",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Custom CSS
st.markdown("""
<style>
    .stAlert {
        margin-top: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .risk-high {
        color: #ff4b4b;
        font-weight: bold;
    }
    .risk-medium {
        color: #ffa500;
        font-weight: bold;
    }
    .risk-low {
        color: #00cc00;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def main():
    st.title("⚖️ The Judge - AI Compliance Platform")
    st.markdown("**Comprehensive compliance checking for AI systems under EU AI Act, GDPR and Danish regulations**")

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select Page",
        ["🏠 Home", "🔍 Quick Check", "📋 Full Assessment", "📊 Dashboard", "📚 Knowledge Base"]
    )

    if page == "🏠 Home":
        show_home_page()
    elif page == "🔍 Quick Check":
        show_quick_check_page()
    elif page == "📋 Full Assessment":
        show_full_assessment_page()
    elif page == "📊 Dashboard":
        show_dashboard_page()
    elif page == "📚 Knowledge Base":
        show_knowledge_base_page()


def show_home_page():
    """Home page with overview"""
    st.header("Welcome to The Judge")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        ### 🎯 Key Features
        - EU AI Act compliance checking
        - GDPR analysis for AI systems
        - Danish regulatory compliance
        - Risk assessment & mitigation
        - Automated documentation
        """)

    with col2:
        st.markdown("""
        ### 📋 Supported Frameworks
        - EU AI Act (2024)
        - GDPR (2016/679)
        - Danish Data Protection
        - Sector-specific regulations
        - ISO/IEC standards
        """)

    with col3:
        st.markdown("""
        ### 🚀 Get Started
        1. Use **Quick Check** for instant feedback
        2. Run **Full Assessment** for comprehensive analysis
        3. View results in **Dashboard**
        4. Learn more in **Knowledge Base**
        """)

    st.divider()

    # Statistics
    st.subheader("Platform Statistics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Assessments Completed", "127", "+12 this week")
    with col2:
        st.metric("Average Compliance Score", "78%", "+3%")
    with col3:
        st.metric("High-Risk Systems", "34", "-2")
    with col4:
        st.metric("Active Projects", "45", "+5")

    # Recent updates
    st.divider()
    st.subheader("📰 Recent Updates")

    updates = [
        {"date": "2024-10-15", "title": "AI Act Final Text Published", "type": "regulation"},
        {"date": "2024-10-10", "title": "New GDPR Guidelines for AI", "type": "guideline"},
        {"date": "2024-10-05", "title": "Danish AI Strategy Updated", "type": "national"}
    ]

    for update in updates:
        st.info(f"**{update['date']}** - {update['title']} ({update['type']})")


def show_quick_check_page():
    """Quick compliance check page"""
    st.header("🔍 Quick Compliance Check")
    st.markdown("Get instant feedback on your AI system's compliance status")

    with st.form("quick_check_form"):
        col1, col2 = st.columns(2)

        with col1:
            description = st.text_area(
                "Describe your AI system",
                placeholder="E.g., AI-powered recruitment tool that screens CVs and ranks candidates",
                height=100
            )

            ai_type = st.selectbox(
                "AI System Type",
                ["generative_ai", "predictive_ai", "classification", "recommendation",
                 "computer_vision", "nlp", "robotics", "other"]
            )

            sector = st.selectbox(
                "Industry Sector",
                ["Healthcare", "Finance", "Education", "Employment", "Government",
                 "Technology", "Retail", "Manufacturing", "Other"]
            )

        with col2:
            uses_personal_data = st.checkbox("Processes personal data")
            automated_decisions = st.checkbox("Makes automated decisions with legal/significant effects")

            if uses_personal_data:
                data_types = st.multiselect(
                    "Types of personal data",
                    ["Name", "Email", "Address", "Financial", "Health", "Biometric",
                     "Location", "Behavioral", "Other"]
                )

        submitted = st.form_submit_button("Run Quick Check", type="primary")

    if submitted:
        if not description:
            st.error("Please provide a description of your AI system")
        else:
            with st.spinner("Analyzing compliance..."):
                # Simulate API call
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/api/compliance/quick-check",
                        json={
                            "description": description,
                            "ai_type": ai_type,
                            "sector": sector,
                            "uses_personal_data": uses_personal_data,
                            "automated_decisions": automated_decisions
                        }
                    )

                    if response.status_code == 200:
                        result = response.json()
                        show_quick_check_results(result)
                    else:
                        st.error("Analysis failed. Please try again.")

                except Exception as e:
                    st.error(f"Error connecting to API: {str(e)}")


def show_quick_check_results(result: Dict[str, Any]):
    """Display quick check results"""
    st.success("Quick check completed!")

    # Risk level display
    col1, col2, col3 = st.columns(3)

    with col1:
        risk_level = result["ai_act"]["risk_level"]
        risk_color = get_risk_color(risk_level)
        st.markdown(f"""
        ### AI Act Risk Level
        <div class="{risk_color}">{risk_level.upper()}</div>
        """, unsafe_allow_html=True)

    with col2:
        gdpr_relevant = "Yes" if result["gdpr"]["relevant"] else "No"
        st.markdown(f"""
        ### GDPR Applicable
        **{gdpr_relevant}**
        """)
        if result["gdpr"]["high_risk"]:
            st.warning("High-risk processing detected")

    with col3:
        needs_full = "Yes" if result["needs_full_assessment"] else "No"
        st.markdown(f"""
        ### Full Assessment Needed
        **{needs_full}**
        """)

    # AI Act details
    st.divider()
    st.subheader("AI Act Analysis")
    for reason in result["ai_act"]["reasons"]:
        st.write(f"• {reason}")

    # GDPR details
    if result["gdpr"]["relevant"]:
        st.subheader("GDPR Considerations")
        if result["gdpr"]["requires_dpia"]:
            st.warning("⚠️ Data Protection Impact Assessment (DPIA) required")

    # Recommendations
    st.divider()
    st.subheader("Quick Recommendations")
    for rec in result["quick_recommendations"]:
        if "CRITICAL" in rec:
            st.error(f"🚨 {rec}")
        elif "HIGH" in rec:
            st.warning(f"⚠️ {rec}")
        else:
            st.info(f"ℹ️ {rec}")

    # Action button
    if result["needs_full_assessment"]:
        st.button("Run Full Assessment", type="primary")


def show_full_assessment_page():
    """Full compliance assessment page"""
    st.header("📋 Full Compliance Assessment")

    tab1, tab2, tab3 = st.tabs(["New Assessment", "View Results", "Export Reports"])

    with tab1:
        st.subheader("Create New Assessment")

        with st.form("full_assessment_form"):
            # Basic Information
            st.markdown("### Basic Information")
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Project Name", placeholder="My AI Project")
                sector = st.selectbox(
                    "Sector",
                    ["Healthcare", "Finance", "Education", "Employment", "Government",
                     "Technology", "Retail", "Manufacturing", "Other"]
                )
                ai_type = st.selectbox(
                    "AI Type",
                    ["generative_ai", "predictive_ai", "classification", "recommendation",
                     "computer_vision", "nlp", "robotics", "other"]
                )

            with col2:
                description = st.text_area(
                    "Detailed Description",
                    placeholder="Provide comprehensive description of your AI system...",
                    height=150
                )

            # Data Processing
            st.markdown("### Data Processing")
            col1, col2 = st.columns(2)

            with col1:
                personal_data = st.checkbox("Processes personal data")
                if personal_data:
                    data_types = st.multiselect(
                        "Data Types",
                        ["Name", "Email", "Financial", "Health", "Biometric", "Location", "Other"]
                    )

            with col2:
                automated_decision_making = st.checkbox("Automated decision-making")
                if automated_decision_making:
                    st.info("Special requirements will apply under Article 22 GDPR")

            # Deployment
            st.markdown("### Deployment Information")
            deployment_regions = st.multiselect(
                "Deployment Regions",
                ["EU", "Denmark", "Sweden", "Norway", "Germany", "France", "Other"],
                default=["EU", "Denmark"]
            )

            target_users = st.multiselect(
                "Target User Groups",
                ["General public", "Employees", "Students", "Patients", "Customers",
                 "Government officials", "Other"]
            )

            # Additional options
            st.markdown("### Additional Options")
            include_legal_research = st.checkbox("Include comprehensive legal research", value=True)
            include_mitigation = st.checkbox("Generate risk mitigation strategies", value=True)

            submitted = st.form_submit_button("Start Full Assessment", type="primary")

        if submitted:
            if not name or not description:
                st.error("Please provide project name and description")
            else:
                with st.spinner("Running comprehensive compliance analysis... This may take a few minutes."):
                    # Progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    # Simulate progress
                    steps = [
                        "Initializing analysis...",
                        "Checking AI Act compliance...",
                        "Analyzing GDPR requirements...",
                        "Performing legal research...",
                        "Assessing risks...",
                        "Identifying compliance gaps...",
                        "Generating recommendations...",
                        "Creating report..."
                    ]

                    for i, step in enumerate(steps):
                        status_text.text(step)
                        progress_bar.progress((i + 1) / len(steps))
                        time.sleep(0.5)

                    # Make API call
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/api/compliance/analyze",
                            json={
                                "name": name,
                                "description": description,
                                "ai_type": ai_type,
                                "sector": sector,
                                "personal_data": personal_data,
                                "automated_decision_making": automated_decision_making,
                                "data_types": data_types if personal_data else [],
                                "deployment_region": deployment_regions,
                                "target_users": target_users
                            }
                        )

                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"✅ Assessment completed! Assessment ID: {result['assessment_id']}")
                            st.session_state['last_assessment_id'] = result['assessment_id']
                            show_assessment_summary(result)
                        else:
                            st.error("Assessment failed. Please try again.")

                    except Exception as e:
                        st.error(f"Error: {str(e)}")

    with tab2:
        st.subheader("View Assessment Results")

        # List available assessments
        assessment_id = st.text_input("Enter Assessment ID",
                                     value=st.session_state.get('last_assessment_id', ''))

        if st.button("Load Assessment"):
            if assessment_id:
                try:
                    response = requests.get(f"{API_BASE_URL}/api/compliance/assessment/{assessment_id}")
                    if response.status_code == 200:
                        assessment = response.json()
                        show_detailed_assessment(assessment)
                    else:
                        st.error("Assessment not found")
                except Exception as e:
                    st.error(f"Error loading assessment: {str(e)}")

    with tab3:
        st.subheader("Export Compliance Reports")

        export_format = st.selectbox("Export Format", ["PDF", "Word", "JSON", "CSV"])

        if st.button("Generate Report"):
            st.info(f"Generating {export_format} report...")
            # In production, this would trigger report generation


def show_assessment_summary(result: Dict[str, Any]):
    """Show assessment summary"""
    st.divider()
    st.subheader("Assessment Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Risk Level", result["risk_level"])
    with col2:
        st.metric("Compliance Score", f"{result['compliance_score']:.1f}%")
    with col3:
        st.metric("Overall Status", result["overall_status"])
    with col4:
        st.metric("Gaps Found", result["summary"]["gaps_count"])


def show_detailed_assessment(assessment: Dict[str, Any]):
    """Show detailed assessment results"""
    st.divider()

    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Project", assessment["project_name"])
    with col2:
        st.metric("Risk Level", assessment["risk_level"])
    with col3:
        st.metric("Compliance Score", f"{assessment['compliance_score']:.1f}%")
    with col4:
        st.metric("Status", assessment["overall_status"])

    # Detailed tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["AI Act", "GDPR", "Requirements", "Risks", "Recommendations"]
    )

    with tab1:
        st.subheader("AI Act Compliance")
        ai_act = assessment.get("ai_act_compliance", {})
        st.json(ai_act)  # In production, format this nicely

    with tab2:
        st.subheader("GDPR Compliance")
        gdpr = assessment.get("gdpr_compliance", {})
        st.json(gdpr)  # In production, format this nicely

    with tab3:
        st.subheader("Compliance Requirements")
        requirements = assessment.get("requirements", [])
        for req in requirements:
            with st.expander(f"{req['framework']} - {req['description'][:50]}..."):
                st.write(f"**Status:** {req['status']}")
                st.write(f"**Mandatory:** {req['mandatory']}")
                st.write("**Recommendations:**")
                for rec in req.get("recommendations", []):
                    st.write(f"• {rec}")

    with tab4:
        st.subheader("Identified Risks")
        risks = assessment.get("identified_risks", [])
        for risk in risks:
            st.warning(f"⚠️ {risk}")

    with tab5:
        st.subheader("Recommendations")
        for rec in assessment.get("recommendations", []):
            if "CRITICAL" in rec:
                st.error(f"🚨 {rec}")
            elif "HIGH" in rec:
                st.warning(f"⚠️ {rec}")
            else:
                st.info(f"ℹ️ {rec}")


def show_dashboard_page():
    """Dashboard with analytics"""
    st.header("📊 Compliance Dashboard")

    # Date filter
    col1, col2 = st.columns([3, 1])
    with col1:
        date_range = st.date_input(
            "Select date range",
            value=(datetime.now().replace(day=1), datetime.now()),
            format="YYYY-MM-DD"
        )

    # Metrics
    st.divider()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Assessments", "127", "+12%")
    with col2:
        st.metric("Average Score", "78%", "+3%")
    with col3:
        st.metric("High Risk", "34", "-5%")
    with col4:
        st.metric("Compliant", "89", "+8%")

    # Charts
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        # Risk distribution pie chart
        fig = go.Figure(data=[go.Pie(
            labels=['Minimal', 'Limited', 'High', 'Unacceptable'],
            values=[45, 32, 20, 3],
            hole=.3
        )])
        fig.update_layout(title="Risk Level Distribution")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Compliance trend line chart
        dates = pd.date_range(start='2024-01-01', periods=10, freq='M')
        scores = [65, 68, 70, 72, 75, 74, 76, 78, 79, 78]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=scores,
            mode='lines+markers',
            name='Compliance Score'
        ))
        fig.update_layout(title="Compliance Score Trend")
        st.plotly_chart(fig, use_container_width=True)

    # Sector breakdown
    st.divider()
    st.subheader("Compliance by Sector")

    sector_data = pd.DataFrame({
        'Sector': ['Healthcare', 'Finance', 'Education', 'Employment', 'Technology'],
        'Assessments': [25, 30, 15, 20, 37],
        'Avg Score': [82, 75, 79, 71, 85],
        'High Risk %': [40, 60, 20, 80, 30]
    })

    st.dataframe(sector_data, use_container_width=True)


def show_knowledge_base_page():
    """Knowledge base and documentation"""
    st.header("📚 Knowledge Base")

    tab1, tab2, tab3, tab4 = st.tabs(["AI Act", "GDPR", "Danish Law", "Resources"])

    with tab1:
        st.subheader("EU AI Act Guide")
        st.markdown("""
        ### Risk Categories

        **🚫 Unacceptable Risk (Prohibited)**
        - Subliminal techniques
        - Exploitation of vulnerable groups
        - Social scoring by public authorities
        - Real-time biometric identification in public spaces

        **⚠️ High Risk**
        - Critical infrastructure
        - Education and vocational training
        - Employment and worker management
        - Essential services (credit, insurance)
        - Law enforcement
        - Migration and border control
        - Justice and democratic processes

        **ℹ️ Limited Risk**
        - Chatbots and virtual assistants
        - Emotion recognition systems
        - Biometric categorization systems
        - Generative AI (deepfakes)

        **✅ Minimal Risk**
        - AI-enabled video games
        - Spam filters
        - Inventory management systems
        """)

    with tab2:
        st.subheader("GDPR for AI Systems")
        st.markdown("""
        ### Key Requirements

        **Legal Basis**
        - Consent
        - Contract necessity
        - Legal obligation
        - Vital interests
        - Public task
        - Legitimate interests

        **Special Considerations for AI**
        - Automated decision-making (Article 22)
        - Right to explanation
        - Data minimization
        - Privacy by design
        - Data Protection Impact Assessment (DPIA)

        **Data Subject Rights**
        - Right to be informed
        - Right of access
        - Right to rectification
        - Right to erasure
        - Right to restrict processing
        - Right to data portability
        - Right to object
        """)

    with tab3:
        st.subheader("Danish Regulatory Framework")
        st.markdown("""
        ### Danish AI Implementation

        **Datatilsynet Guidelines**
        - Specific guidance on AI and machine learning
        - Interpretation of GDPR for Danish context
        - Sector-specific requirements

        **National AI Strategy**
        - Ethical AI principles
        - Public sector AI use
        - Innovation and regulation balance

        **Key Authorities**
        - Datatilsynet (Data Protection)
        - Relevant sector authorities
        - Danish Business Authority
        """)

    with tab4:
        st.subheader("Additional Resources")

        resources = [
            {"title": "EU AI Act Full Text", "url": "https://eur-lex.europa.eu/", "type": "Legal Text"},
            {"title": "GDPR Official Text", "url": "https://gdpr.eu/", "type": "Legal Text"},
            {"title": "ISO/IEC 23053", "url": "#", "type": "Standard"},
            {"title": "IEEE Ethics Guidelines", "url": "#", "type": "Guideline"},
            {"title": "Datatilsynet AI Guidance", "url": "https://www.datatilsynet.dk/", "type": "National Guidance"}
        ]

        for resource in resources:
            st.markdown(f"📄 **[{resource['title']}]({resource['url']})** - {resource['type']}")


def get_risk_color(risk_level: str) -> str:
    """Get CSS class for risk level"""
    risk_map = {
        "unacceptable": "risk-high",
        "high": "risk-high",
        "limited": "risk-medium",
        "minimal": "risk-low"
    }
    return risk_map.get(risk_level.lower(), "risk-low")


if __name__ == "__main__":
    main()