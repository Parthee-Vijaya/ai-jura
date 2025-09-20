"""
Simplified version of The Judge for quick startup
"""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, List, Any

# Configure Streamlit page
st.set_page_config(
    page_title="The Judge - AI Compliance",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mock data and functions since we can't install dependencies
class MockProject:
    def __init__(self, name, description, ai_type, sector, personal_data=False, automated_decisions=False):
        self.name = name
        self.description = description
        self.ai_type = ai_type
        self.sector = sector
        self.personal_data = personal_data
        self.automated_decisions = automated_decisions

def assess_ai_act_risk(project):
    """Mock AI Act risk assessment"""
    description_lower = project.description.lower()

    # Check for prohibited practices
    if any(word in description_lower for word in ["social scoring", "subliminal", "manipulation"]):
        return "unacceptable", ["Potential prohibited practice detected"]

    # Check for high risk
    if project.sector.lower() in ["healthcare", "finance", "employment"] and project.automated_decisions:
        return "high", ["High-risk sector with automated decision-making"]

    if "biometric" in description_lower or "facial recognition" in description_lower:
        return "high", ["Biometric identification system"]

    # Check for limited risk
    if "chatbot" in description_lower or "generative" in project.ai_type.lower():
        return "limited", ["AI system interacting with users"]

    return "minimal", ["No high-risk indicators identified"]

def assess_gdpr_compliance(project):
    """Mock GDPR assessment"""
    if not project.personal_data:
        return {"score": 90, "issues": ["No personal data processing"], "dpia_required": False}

    score = 70
    issues = []

    if project.automated_decisions:
        score -= 20
        issues.append("Automated decision-making requires special safeguards")

    if "health" in project.sector.lower():
        score -= 10
        issues.append("Health data requires explicit consent")

    dpia_required = score < 60 or project.automated_decisions

    return {
        "score": score,
        "issues": issues,
        "dpia_required": dpia_required
    }

def main():
    st.title("⚖️ The Judge - AI Compliance Platform")
    st.markdown("**Comprehensive compliance checking for AI systems under EU AI Act, GDPR and Danish regulations**")

    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select Page",
        ["🏠 Home", "🔍 Quick Check", "📊 Dashboard", "📚 Knowledge Base"]
    )

    if page == "🏠 Home":
        show_home_page()
    elif page == "🔍 Quick Check":
        show_quick_check_page()
    elif page == "📊 Dashboard":
        show_dashboard_page()
    elif page == "📚 Knowledge Base":
        show_knowledge_base_page()

def show_home_page():
    """Home page"""
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
        2. View analytics in **Dashboard**
        3. Learn more in **Knowledge Base**
        4. Export compliance reports
        """)

    # Statistics
    st.divider()
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

def show_quick_check_page():
    """Quick compliance check"""
    st.header("🔍 Quick Compliance Check")
    st.markdown("Get instant feedback on your AI system's compliance status")

    with st.form("quick_check_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Project Name", placeholder="My AI Project")
            description = st.text_area(
                "Describe your AI system",
                placeholder="E.g., AI-powered recruitment tool that screens CVs",
                height=100
            )
            ai_type = st.selectbox(
                "AI System Type",
                ["generative_ai", "predictive_ai", "classification", "recommendation",
                 "computer_vision", "nlp", "robotics", "other"]
            )

        with col2:
            sector = st.selectbox(
                "Industry Sector",
                ["Healthcare", "Finance", "Education", "Employment", "Government",
                 "Technology", "Retail", "Manufacturing", "Other"]
            )
            personal_data = st.checkbox("Processes personal data")
            automated_decisions = st.checkbox("Makes automated decisions")

        submitted = st.form_submit_button("Run Quick Check", type="primary")

    if submitted:
        if not description:
            st.error("Please provide a description of your AI system")
        else:
            with st.spinner("Analyzing compliance..."):
                # Create mock project
                project = MockProject(name, description, ai_type, sector, personal_data, automated_decisions)

                # Run assessments
                risk_level, risk_reasons = assess_ai_act_risk(project)
                gdpr_result = assess_gdpr_compliance(project)

                st.success("Quick check completed!")

                # Results
                col1, col2, col3 = st.columns(3)

                with col1:
                    risk_color = "🔴" if risk_level == "high" else "🟡" if risk_level == "limited" else "🟢"
                    st.markdown(f"""
                    ### AI Act Risk Level
                    {risk_color} **{risk_level.upper()}**
                    """)

                with col2:
                    gdpr_applicable = "Yes" if personal_data else "No"
                    st.markdown(f"""
                    ### GDPR Applicable
                    **{gdpr_applicable}**
                    """)

                with col3:
                    score_color = "🔴" if gdpr_result["score"] < 60 else "🟡" if gdpr_result["score"] < 80 else "🟢"
                    st.markdown(f"""
                    ### Compliance Score
                    {score_color} **{gdpr_result["score"]}%**
                    """)

                # Details
                st.divider()
                st.subheader("Analysis Details")

                st.write("**AI Act Risk Factors:**")
                for reason in risk_reasons:
                    st.write(f"• {reason}")

                if personal_data:
                    st.write("**GDPR Considerations:**")
                    for issue in gdpr_result["issues"]:
                        st.write(f"• {issue}")

                    if gdpr_result["dpia_required"]:
                        st.warning("⚠️ Data Protection Impact Assessment (DPIA) required")

                # Recommendations
                st.divider()
                st.subheader("Recommendations")

                if risk_level == "unacceptable":
                    st.error("🚨 CRITICAL: System cannot be deployed - involves prohibited practices")
                elif risk_level == "high":
                    st.warning("⚠️ HIGH: Implement all high-risk AI system requirements")
                    st.info("• Conduct conformity assessment")
                    st.info("• Implement risk management system")
                    st.info("• Prepare technical documentation")
                elif risk_level == "limited":
                    st.info("ℹ️ Implement transparency measures")
                    st.info("• Inform users about AI interaction")
                else:
                    st.success("✅ Minimal compliance requirements")

                if personal_data:
                    st.info("• Establish lawful basis for processing")
                    st.info("• Implement data subject rights")

def show_dashboard_page():
    """Dashboard with mock analytics"""
    st.header("📊 Compliance Dashboard")

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Assessments", "127", "+12%")
    with col2:
        st.metric("Average Score", "78%", "+3%")
    with col3:
        st.metric("High Risk", "34", "-5%")
    with col4:
        st.metric("Compliant", "89", "+8%")

    st.divider()

    # Mock data for charts
    risk_data = {"Minimal": 45, "Limited": 32, "High": 20, "Unacceptable": 3}

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Risk Level Distribution")
        st.bar_chart(risk_data)

    with col2:
        st.subheader("Compliance Trends")
        import random
        trend_data = {f"Week {i}": random.randint(70, 85) for i in range(1, 9)}
        st.line_chart(trend_data)

def show_knowledge_base_page():
    """Knowledge base"""
    st.header("📚 Knowledge Base")

    tab1, tab2, tab3 = st.tabs(["AI Act", "GDPR", "Resources"])

    with tab1:
        st.subheader("EU AI Act Guide")
        st.markdown("""
        ### Risk Categories

        **🚫 Unacceptable Risk (Prohibited)**
        - Subliminal techniques beyond consciousness
        - Exploitation of vulnerable groups
        - Social scoring by public authorities
        - Real-time biometric identification in public spaces

        **⚠️ High Risk**
        - Critical infrastructure management
        - Education and vocational training
        - Employment and worker management
        - Essential services (credit, insurance)
        - Law enforcement purposes
        - Migration and border control
        - Justice and democratic processes

        **ℹ️ Limited Risk**
        - Chatbots and virtual assistants
        - Emotion recognition systems
        - Generative AI systems

        **✅ Minimal Risk**
        - AI-enabled video games
        - Spam filters
        - Inventory management systems
        """)

    with tab2:
        st.subheader("GDPR for AI Systems")
        st.markdown("""
        ### Key Requirements

        **Legal Basis (Article 6)**
        - Consent of data subject
        - Contract necessity
        - Legal obligation
        - Vital interests protection
        - Public task performance
        - Legitimate interests

        **Special Considerations for AI**
        - Automated decision-making (Article 22)
        - Right to explanation
        - Data minimization principle
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
        st.subheader("Additional Resources")
        st.markdown("""
        ### Legal Sources
        - [EU AI Act Full Text](https://eur-lex.europa.eu/)
        - [GDPR Official Text](https://gdpr.eu/)
        - [Datatilsynet AI Guidance](https://www.datatilsynet.dk/)

        ### Standards
        - ISO/IEC 23053 (AI Trustworthiness)
        - ISO/IEC 23894 (AI Risk Management)
        - IEEE Standards for AI Ethics

        ### National Guidelines
        - Danish AI Strategy
        - Datatilsynet Guidelines
        - Sector-specific requirements
        """)

if __name__ == "__main__":
    main()