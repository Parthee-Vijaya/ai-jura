"""
Example usage of The Judge - AI Compliance Platform
Demonstrates different use cases and scenarios
"""

import asyncio
from src.core.models import ProjectInput, AISystemType
from src.compliance.ai_act_checker import AIActComplianceChecker
from src.compliance.gdpr_checker import GDPRComplianceChecker
from src.agents.compliance_orchestrator import ComplianceOrchestrator
import json
from typing import Dict, Any


def print_section(title: str):
    """Pretty print section headers"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def print_result(label: str, value: Any, indent: int = 0):
    """Pretty print results"""
    prefix = "  " * indent + "• " if indent > 0 else ""
    print(f"{prefix}{label}: {value}")


async def example_1_healthcare_ai():
    """Example: High-risk healthcare AI system"""
    print_section("EXAMPLE 1: Healthcare AI Diagnosis System")

    project = ProjectInput(
        name="AI Medical Diagnosis Assistant",
        description="An AI system that analyzes patient symptoms, medical history, and test results to suggest potential diagnoses and treatment recommendations to healthcare professionals",
        ai_type=AISystemType.PREDICTIVE_AI,
        sector="Healthcare",
        personal_data=True,
        data_types=["health records", "medical history", "test results", "biometric data"],
        automated_decision_making=False,  # Assists doctors, doesn't make final decisions
        target_users=["Healthcare professionals", "Doctors", "Nurses"],
        deployment_region=["EU", "Denmark"]
    )

    # Run compliance checks
    ai_act_checker = AIActComplianceChecker()
    gdpr_checker = GDPRComplianceChecker()

    print("\n🔍 Running AI Act compliance check...")
    risk_level, risk_reasons = ai_act_checker.assess_risk_level(project)
    ai_act_result = ai_act_checker.check_compliance(project)

    print_result("Risk Level", risk_level.value)
    print_result("Risk Reasons", "")
    for reason in risk_reasons:
        print_result(reason, "", indent=1)

    print("\n🔍 Running GDPR compliance check...")
    gdpr_result = gdpr_checker.assess_gdpr_compliance(project)

    print_result("GDPR Score", f"{gdpr_result['compliance_score']:.1f}%")
    print_result("Requires DPIA", gdpr_result['high_risk_processing'])
    print_result("Key Issues", "")
    for issue in gdpr_result['compliance_issues'][:3]:
        print_result(issue, "", indent=1)

    return project, ai_act_result, gdpr_result


async def example_2_recruitment_ai():
    """Example: Employment sector AI with automated decisions"""
    print_section("EXAMPLE 2: AI Recruitment Screening Tool")

    project = ProjectInput(
        name="SmartRecruit AI",
        description="AI-powered recruitment tool that screens CVs, ranks candidates, and automatically rejects applications that don't meet minimum criteria",
        ai_type=AISystemType.CLASSIFICATION,
        sector="Employment",
        personal_data=True,
        data_types=["name", "email", "education", "work history", "skills"],
        automated_decision_making=True,  # Automatically rejects candidates
        target_users=["HR departments", "Recruiters"],
        deployment_region=["EU", "Denmark", "Sweden", "Norway"]
    )

    print("\n🔍 Running compliance analysis...")
    orchestrator = ComplianceOrchestrator()

    # Note: This would normally use the full async workflow
    ai_act_checker = AIActComplianceChecker()
    risk_level, risk_reasons = ai_act_checker.assess_risk_level(project)

    print_result("Risk Level", risk_level.value)
    print("\n⚠️ Critical Findings:")
    print_result("Automated decision-making in employment", "HIGH RISK", indent=1)
    print_result("Article 22 GDPR applies", "Special requirements", indent=1)
    print_result("Requires human oversight", "Mandatory", indent=1)

    return project


async def example_3_chatbot():
    """Example: Limited risk chatbot"""
    print_section("EXAMPLE 3: Customer Service Chatbot")

    project = ProjectInput(
        name="HelpBot Pro",
        description="AI chatbot that answers customer questions about products and services using generative AI",
        ai_type=AISystemType.GENERATIVE_AI,
        sector="Retail",
        personal_data=False,  # No personal data collected
        data_types=[],
        automated_decision_making=False,
        target_users=["General public", "Customers"],
        deployment_region=["EU"]
    )

    ai_act_checker = AIActComplianceChecker()
    risk_level, risk_reasons = ai_act_checker.assess_risk_level(project)

    print_result("Risk Level", risk_level.value)
    print_result("Main Requirement", "Transparency - inform users they're interacting with AI")
    print_result("GDPR Applicable", "No (no personal data)")

    return project


async def example_4_prohibited_system():
    """Example: Prohibited AI system"""
    print_section("EXAMPLE 4: Social Scoring System (PROHIBITED)")

    project = ProjectInput(
        name="Citizen Score AI",
        description="AI system for social scoring that evaluates citizens' behavior and trustworthiness based on their social interactions, financial history, and public behavior",
        ai_type=AISystemType.PREDICTIVE_AI,
        sector="Government",
        personal_data=True,
        data_types=["behavioral data", "financial records", "social media", "criminal records"],
        automated_decision_making=True,
        target_users=["Government officials", "Public services"],
        deployment_region=["EU"]
    )

    ai_act_checker = AIActComplianceChecker()
    risk_level, risk_reasons = ai_act_checker.assess_risk_level(project)

    print_result("Risk Level", f"🚫 {risk_level.value}")
    print("\n❌ CRITICAL COMPLIANCE FAILURE:")
    print_result("Status", "PROHIBITED under EU AI Act Article 5", indent=1)
    print_result("Reason", risk_reasons[0], indent=1)
    print_result("Action Required", "System cannot be deployed in the EU", indent=1)

    return project


async def example_5_biometric_system():
    """Example: Biometric identification system"""
    print_section("EXAMPLE 5: Workplace Biometric Access Control")

    project = ProjectInput(
        name="SecureEntry AI",
        description="Facial recognition system for employee access control in office buildings, tracks entry/exit times",
        ai_type=AISystemType.COMPUTER_VISION,
        sector="Technology",
        personal_data=True,
        data_types=["biometric data", "facial images", "employee ID", "access logs"],
        automated_decision_making=True,
        target_users=["Employees", "Security personnel"],
        deployment_region=["Denmark"]
    )

    print("\n🔍 Running comprehensive analysis...")

    # Quick assessment
    ai_act_checker = AIActComplianceChecker()
    gdpr_checker = GDPRComplianceChecker()

    risk_level, _ = ai_act_checker.assess_risk_level(project)
    gdpr_result = gdpr_checker.assess_gdpr_compliance(project)

    print_result("AI Act Risk", risk_level.value)
    print_result("GDPR Concerns", "")
    print_result("Biometric data (special category)", "Explicit consent required", indent=1)
    print_result("Workplace surveillance", "Employee rights consideration", indent=1)
    print_result("Danish law", "Datatilsynet approval may be required", indent=1)

    return project


def create_compliance_summary(ai_act_result: Dict, gdpr_result: Dict) -> str:
    """Create a summary report from results"""
    summary = []
    summary.append("\n📋 COMPLIANCE SUMMARY REPORT")
    summary.append("="*50)

    # Overall status
    risk_level = ai_act_result['risk_level']
    gdpr_score = gdpr_result['compliance_score']

    if risk_level.value == "unacceptable":
        overall = "❌ NON-COMPLIANT (Prohibited)"
    elif risk_level.value == "high" and gdpr_score < 50:
        overall = "⚠️ HIGH RISK - Major compliance work needed"
    elif gdpr_score >= 70:
        overall = "✅ Generally compliant with some requirements"
    else:
        overall = "⚠️ Compliance gaps identified"

    summary.append(f"Overall Status: {overall}")
    summary.append(f"AI Act Risk Level: {risk_level.value.upper()}")
    summary.append(f"GDPR Compliance Score: {gdpr_score:.1f}%")

    # Key requirements
    summary.append("\n🔑 Key Requirements:")
    req_count = len(ai_act_result.get('requirements', []))
    summary.append(f"  • {req_count} AI Act requirements identified")

    if gdpr_result['high_risk_processing']:
        summary.append("  • Data Protection Impact Assessment (DPIA) required")

    if gdpr_result['automated_decisions']:
        summary.append("  • Article 22 GDPR safeguards required")

    # Next steps
    summary.append("\n📌 Priority Actions:")
    for i, step in enumerate(ai_act_result.get('next_steps', [])[:3], 1):
        summary.append(f"  {i}. {step}")

    return "\n".join(summary)


async def run_all_examples():
    """Run all examples"""
    print("\n" + "⚖️ THE JUDGE - AI COMPLIANCE SCENARIOS".center(60))
    print("="*60)

    # Example 1: Healthcare
    project1, ai_act1, gdpr1 = await example_1_healthcare_ai()
    print(create_compliance_summary(ai_act1, gdpr1))

    # Example 2: Recruitment
    await example_2_recruitment_ai()

    # Example 3: Chatbot
    await example_3_chatbot()

    # Example 4: Prohibited
    await example_4_prohibited_system()

    # Example 5: Biometric
    await example_5_biometric_system()

    print("\n" + "="*60)
    print("✅ All examples completed!".center(60))
    print("="*60)


if __name__ == "__main__":
    # Run examples
    asyncio.run(run_all_examples())

    print("\n💡 To start the full platform:")
    print("   Backend:  python main.py")
    print("   Frontend: streamlit run streamlit_app.py")
    print("\n📚 Visit http://localhost:8501 for the web interface")