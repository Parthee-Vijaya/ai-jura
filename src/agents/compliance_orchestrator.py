"""
Main Compliance Orchestrator using LangGraph
Coordinates multiple specialized agents for comprehensive compliance analysis
"""

from typing import Dict, List, Any, TypedDict, Annotated, Sequence
from datetime import datetime
import operator
from enum import Enum

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

from src.core.models import (
    ProjectInput, ComplianceAssessment, RiskLevel,
    ComplianceStatus, AgentState
)
from src.compliance.ai_act_checker import AIActComplianceChecker
from src.compliance.gdpr_checker import GDPRComplianceChecker

import logging
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ComplianceState(TypedDict):
    """State definition for compliance workflow"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    project_input: ProjectInput
    ai_act_analysis: Dict[str, Any]
    gdpr_analysis: Dict[str, Any]
    legal_research: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    compliance_gaps: List[Dict[str, Any]]
    recommendations: List[str]
    final_report: Dict[str, Any]
    current_step: str
    errors: List[str]


class WorkflowStep(str, Enum):
    """Workflow steps in compliance analysis"""
    INITIALIZATION = "initialization"
    AI_ACT_CHECK = "ai_act_check"
    GDPR_CHECK = "gdpr_check"
    LEGAL_RESEARCH = "legal_research"
    RISK_ASSESSMENT = "risk_assessment"
    GAP_ANALYSIS = "gap_analysis"
    REPORT_GENERATION = "report_generation"
    COMPLETE = "complete"


class ComplianceOrchestrator:
    """
    Main orchestrator that coordinates all compliance checking agents
    Using LangGraph for workflow management
    """

    def __init__(self, llm_model: str = None):
        self.llm_model = llm_model or os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")

        # Initialize LLM
        if "claude" in self.llm_model.lower():
            self.llm = ChatAnthropic(
                model=self.llm_model,
                temperature=0.1,
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
        else:
            self.llm = ChatOpenAI(
                model=self.llm_model,
                temperature=0.1,
                api_key=os.getenv("OPENAI_API_KEY")
            )

        # Initialize compliance checkers
        self.ai_act_checker = AIActComplianceChecker()
        self.gdpr_checker = GDPRComplianceChecker()

        # Build the workflow
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(ComplianceState)

        # Define nodes
        workflow.add_node("initialize", self._initialize_node)
        workflow.add_node("check_ai_act", self._check_ai_act_node)
        workflow.add_node("check_gdpr", self._check_gdpr_node)
        workflow.add_node("research_legal", self._legal_research_node)
        workflow.add_node("assess_risk", self._assess_risk_node)
        workflow.add_node("analyze_gaps", self._analyze_gaps_node)
        workflow.add_node("generate_report", self._generate_report_node)

        # Define edges
        workflow.set_entry_point("initialize")

        workflow.add_edge("initialize", "check_ai_act")
        workflow.add_edge("check_ai_act", "check_gdpr")
        workflow.add_edge("check_gdpr", "research_legal")
        workflow.add_edge("research_legal", "assess_risk")
        workflow.add_edge("assess_risk", "analyze_gaps")
        workflow.add_edge("analyze_gaps", "generate_report")
        workflow.add_edge("generate_report", END)

        return workflow.compile()

    def _initialize_node(self, state: ComplianceState) -> ComplianceState:
        """Initialize the compliance checking process"""
        logger.info(f"Initializing compliance check for project: {state['project_input'].name}")

        state["messages"].append(
            SystemMessage(content=f"Starting compliance analysis for {state['project_input'].name}")
        )
        state["current_step"] = WorkflowStep.INITIALIZATION

        return state

    def _check_ai_act_node(self, state: ComplianceState) -> ComplianceState:
        """Run AI Act compliance check"""
        logger.info("Running AI Act compliance check")
        state["current_step"] = WorkflowStep.AI_ACT_CHECK

        try:
            ai_act_result = self.ai_act_checker.check_compliance(state["project_input"])
            state["ai_act_analysis"] = ai_act_result

            state["messages"].append(
                AIMessage(content=f"AI Act Analysis Complete: Risk Level = {ai_act_result['risk_level'].value}")
            )
        except Exception as e:
            logger.error(f"AI Act check failed: {e}")
            state["errors"].append(f"AI Act check error: {str(e)}")
            state["ai_act_analysis"] = {"error": str(e)}

        return state

    def _check_gdpr_node(self, state: ComplianceState) -> ComplianceState:
        """Run GDPR compliance check"""
        logger.info("Running GDPR compliance check")
        state["current_step"] = WorkflowStep.GDPR_CHECK

        try:
            gdpr_result = self.gdpr_checker.assess_gdpr_compliance(state["project_input"])
            state["gdpr_analysis"] = gdpr_result

            state["messages"].append(
                AIMessage(content=f"GDPR Analysis Complete: Score = {gdpr_result['compliance_score']:.1f}%")
            )
        except Exception as e:
            logger.error(f"GDPR check failed: {e}")
            state["errors"].append(f"GDPR check error: {str(e)}")
            state["gdpr_analysis"] = {"error": str(e)}

        return state

    def _legal_research_node(self, state: ComplianceState) -> ComplianceState:
        """Perform legal research for relevant regulations"""
        logger.info("Performing legal research")
        state["current_step"] = WorkflowStep.LEGAL_RESEARCH

        # Create research prompt
        research_prompt = self._create_legal_research_prompt(state)

        try:
            response = self.llm.invoke([
                SystemMessage(content="You are a legal research expert specializing in AI and data protection law."),
                HumanMessage(content=research_prompt)
            ])

            # Parse response
            legal_research = {
                "relevant_laws": self._extract_relevant_laws(response.content),
                "sector_specific": self._extract_sector_requirements(state["project_input"].sector, response.content),
                "danish_requirements": self._extract_danish_requirements(response.content),
                "additional_frameworks": self._extract_additional_frameworks(response.content),
                "research_summary": response.content
            }

            state["legal_research"] = legal_research
            state["messages"].append(AIMessage(content="Legal research completed"))

        except Exception as e:
            logger.error(f"Legal research failed: {e}")
            state["errors"].append(f"Legal research error: {str(e)}")
            state["legal_research"] = {"error": str(e)}

        return state

    def _assess_risk_node(self, state: ComplianceState) -> ComplianceState:
        """Comprehensive risk assessment"""
        logger.info("Assessing compliance risks")
        state["current_step"] = WorkflowStep.RISK_ASSESSMENT

        risk_prompt = self._create_risk_assessment_prompt(state)

        try:
            response = self.llm.invoke([
                SystemMessage(content="You are a risk assessment expert for AI systems."),
                HumanMessage(content=risk_prompt)
            ])

            risk_assessment = {
                "overall_risk_level": self._determine_overall_risk(state),
                "compliance_risks": self._identify_compliance_risks(state),
                "operational_risks": self._identify_operational_risks(state),
                "reputational_risks": self._identify_reputational_risks(state),
                "mitigation_strategies": self._generate_mitigation_strategies(state),
                "risk_summary": response.content
            }

            state["risk_assessment"] = risk_assessment
            state["messages"].append(AIMessage(content="Risk assessment completed"))

        except Exception as e:
            logger.error(f"Risk assessment failed: {e}")
            state["errors"].append(f"Risk assessment error: {str(e)}")
            state["risk_assessment"] = {"error": str(e)}

        return state

    def _analyze_gaps_node(self, state: ComplianceState) -> ComplianceState:
        """Analyze compliance gaps"""
        logger.info("Analyzing compliance gaps")
        state["current_step"] = WorkflowStep.GAP_ANALYSIS

        # Collect all requirements
        all_requirements = []

        if "requirements" in state.get("ai_act_analysis", {}):
            all_requirements.extend(state["ai_act_analysis"]["requirements"])

        if "requirements" in state.get("gdpr_analysis", {}):
            all_requirements.extend(state["gdpr_analysis"]["requirements"])

        # Identify gaps
        gaps = []
        for req in all_requirements:
            if req.compliance_status in [ComplianceStatus.NON_COMPLIANT, ComplianceStatus.NEEDS_REVIEW]:
                gaps.append({
                    "requirement": req.description,
                    "framework": req.framework.value,
                    "status": req.compliance_status.value,
                    "recommendations": req.recommendations
                })

        state["compliance_gaps"] = gaps

        # Generate prioritized recommendations
        state["recommendations"] = self._generate_prioritized_recommendations(state)

        state["messages"].append(
            AIMessage(content=f"Gap analysis complete: {len(gaps)} gaps identified")
        )

        return state

    def _generate_report_node(self, state: ComplianceState) -> ComplianceState:
        """Generate final compliance report"""
        logger.info("Generating compliance report")
        state["current_step"] = WorkflowStep.REPORT_GENERATION

        report = {
            "project_name": state["project_input"].name,
            "assessment_date": datetime.now().isoformat(),
            "executive_summary": self._generate_executive_summary(state),
            "ai_act_compliance": state.get("ai_act_analysis", {}),
            "gdpr_compliance": state.get("gdpr_analysis", {}),
            "legal_research": state.get("legal_research", {}),
            "risk_assessment": state.get("risk_assessment", {}),
            "compliance_gaps": state.get("compliance_gaps", []),
            "recommendations": state.get("recommendations", []),
            "next_steps": self._generate_next_steps(state),
            "errors": state.get("errors", [])
        }

        state["final_report"] = report
        state["messages"].append(AIMessage(content="Compliance report generated"))

        return state

    # Helper methods
    def _create_legal_research_prompt(self, state: ComplianceState) -> str:
        """Create prompt for legal research"""
        project = state["project_input"]
        return f"""
        Analyze legal requirements for the following AI system:

        Project: {project.name}
        Description: {project.description}
        Sector: {project.sector}
        AI Type: {project.ai_type}
        Deployment Region: {', '.join(project.deployment_region)}

        Please identify:
        1. All applicable EU regulations beyond AI Act and GDPR
        2. Danish specific requirements and implementations
        3. Sector-specific regulations
        4. Any additional compliance frameworks
        5. Potential legal conflicts or uncertainties

        Focus on practical compliance requirements.
        """

    def _create_risk_assessment_prompt(self, state: ComplianceState) -> str:
        """Create prompt for risk assessment"""
        return f"""
        Based on the compliance analysis performed, assess the risks for this AI system:

        AI Act Risk Level: {state.get('ai_act_analysis', {}).get('risk_level', 'Unknown')}
        GDPR Compliance Score: {state.get('gdpr_analysis', {}).get('compliance_score', 0):.1f}%
        Compliance Gaps: {len(state.get('compliance_gaps', []))}

        Identify:
        1. Critical compliance risks
        2. Operational risks
        3. Reputational risks
        4. Financial risks
        5. Mitigation strategies

        Prioritize risks by severity and likelihood.
        """

    def _extract_relevant_laws(self, content: str) -> List[str]:
        """Extract relevant laws from LLM response"""
        # This would parse the LLM response to extract specific laws
        # For now, return common ones
        return [
            "EU AI Act (Regulation 2024/1689)",
            "GDPR (Regulation 2016/679)",
            "Digital Services Act",
            "Digital Markets Act",
            "Product Liability Directive"
        ]

    def _extract_sector_requirements(self, sector: str, content: str) -> Dict[str, Any]:
        """Extract sector-specific requirements"""
        sector_reqs = {
            "sector": sector,
            "specific_regulations": [],
            "compliance_notes": ""
        }

        sector_lower = sector.lower()
        if "health" in sector_lower:
            sector_reqs["specific_regulations"] = ["MDR", "IVDR", "Health Data Act"]
        elif "finance" in sector_lower:
            sector_reqs["specific_regulations"] = ["MiFID II", "PSD2", "DORA"]
        elif "education" in sector_lower:
            sector_reqs["specific_regulations"] = ["Education regulations", "Child protection laws"]

        return sector_reqs

    def _extract_danish_requirements(self, content: str) -> Dict[str, Any]:
        """Extract Danish-specific requirements"""
        return {
            "danish_data_act": "Applicable",
            "danish_ai_guidelines": "Follow Datatilsynet guidelines",
            "sector_authorities": ["Datatilsynet", "Relevant sector authority"]
        }

    def _extract_additional_frameworks(self, content: str) -> List[str]:
        """Extract additional compliance frameworks"""
        return [
            "ISO/IEC 23053 (AI trustworthiness)",
            "ISO/IEC 23894 (AI risk management)",
            "IEEE standards for AI ethics"
        ]

    def _determine_overall_risk(self, state: ComplianceState) -> str:
        """Determine overall risk level"""
        ai_act_risk = state.get("ai_act_analysis", {}).get("risk_level", RiskLevel.MINIMAL)
        gdpr_score = state.get("gdpr_analysis", {}).get("compliance_score", 100)

        if ai_act_risk == RiskLevel.UNACCEPTABLE:
            return "CRITICAL"
        elif ai_act_risk == RiskLevel.HIGH or gdpr_score < 50:
            return "HIGH"
        elif ai_act_risk == RiskLevel.LIMITED or gdpr_score < 70:
            return "MEDIUM"
        else:
            return "LOW"

    def _identify_compliance_risks(self, state: ComplianceState) -> List[Dict[str, Any]]:
        """Identify compliance risks"""
        risks = []

        if state.get("ai_act_analysis", {}).get("risk_level") == RiskLevel.HIGH:
            risks.append({
                "risk": "High-risk AI system requiring conformity assessment",
                "severity": "HIGH",
                "likelihood": "CERTAIN"
            })

        if state.get("gdpr_analysis", {}).get("automated_decisions"):
            risks.append({
                "risk": "Automated decision-making without proper safeguards",
                "severity": "HIGH",
                "likelihood": "HIGH"
            })

        return risks

    def _identify_operational_risks(self, state: ComplianceState) -> List[Dict[str, Any]]:
        """Identify operational risks"""
        return [
            {
                "risk": "Implementation complexity",
                "severity": "MEDIUM",
                "likelihood": "MEDIUM"
            }
        ]

    def _identify_reputational_risks(self, state: ComplianceState) -> List[Dict[str, Any]]:
        """Identify reputational risks"""
        return [
            {
                "risk": "Public trust in AI system",
                "severity": "MEDIUM",
                "likelihood": "LOW"
            }
        ]

    def _generate_mitigation_strategies(self, state: ComplianceState) -> List[str]:
        """Generate risk mitigation strategies"""
        strategies = [
            "Implement comprehensive compliance program",
            "Regular compliance audits",
            "Staff training on AI regulations",
            "Technical documentation maintenance",
            "Incident response procedures"
        ]

        if state.get("ai_act_analysis", {}).get("risk_level") == RiskLevel.HIGH:
            strategies.insert(0, "Prepare for conformity assessment")

        return strategies

    def _generate_prioritized_recommendations(self, state: ComplianceState) -> List[str]:
        """Generate prioritized recommendations"""
        recommendations = []

        # Priority 1: Critical compliance issues
        if state.get("ai_act_analysis", {}).get("risk_level") == RiskLevel.UNACCEPTABLE:
            recommendations.append("CRITICAL: Redesign system to avoid prohibited AI practices")

        # Priority 2: High-risk requirements
        if state.get("ai_act_analysis", {}).get("risk_level") == RiskLevel.HIGH:
            recommendations.append("HIGH: Implement all high-risk AI system requirements")

        # Priority 3: GDPR compliance
        if state.get("gdpr_analysis", {}).get("compliance_score", 100) < 70:
            recommendations.append("HIGH: Address GDPR compliance gaps urgently")

        # Priority 4: Documentation
        recommendations.append("MEDIUM: Complete technical documentation package")

        # Priority 5: Ongoing compliance
        recommendations.append("ONGOING: Establish compliance monitoring procedures")

        return recommendations

    def _generate_executive_summary(self, state: ComplianceState) -> str:
        """Generate executive summary"""
        project = state["project_input"]
        ai_act_risk = state.get("ai_act_analysis", {}).get("risk_level", RiskLevel.MINIMAL)
        gdpr_score = state.get("gdpr_analysis", {}).get("compliance_score", 0)
        gaps_count = len(state.get("compliance_gaps", []))

        summary = f"""
        Compliance Assessment for {project.name}

        AI Act Risk Level: {ai_act_risk.value}
        GDPR Compliance Score: {gdpr_score:.1f}%
        Identified Compliance Gaps: {gaps_count}

        This AI system has been thoroughly assessed against EU AI Act, GDPR, and relevant sector-specific regulations.
        """

        if ai_act_risk == RiskLevel.UNACCEPTABLE:
            summary += "\n\nCRITICAL: System involves prohibited AI practices and cannot be deployed."
        elif ai_act_risk == RiskLevel.HIGH:
            summary += "\n\nSystem is classified as high-risk and requires comprehensive compliance measures."

        return summary

    def _generate_next_steps(self, state: ComplianceState) -> List[str]:
        """Generate next steps"""
        steps = []

        # Based on findings
        if state.get("ai_act_analysis", {}).get("risk_level") == RiskLevel.HIGH:
            steps.append("Schedule conformity assessment with notified body")

        if state.get("gdpr_analysis", {}).get("high_risk_processing"):
            steps.append("Conduct Data Protection Impact Assessment (DPIA)")

        steps.extend([
            "Review and implement all recommendations",
            "Establish compliance monitoring procedures",
            "Train staff on compliance requirements",
            "Schedule regular compliance reviews"
        ])

        return steps

    async def analyze_project(self, project: ProjectInput) -> ComplianceAssessment:
        """
        Main entry point to analyze a project for compliance
        """
        logger.info(f"Starting compliance analysis for: {project.name}")

        # Initialize state
        initial_state = {
            "messages": [],
            "project_input": project,
            "ai_act_analysis": {},
            "gdpr_analysis": {},
            "legal_research": {},
            "risk_assessment": {},
            "compliance_gaps": [],
            "recommendations": [],
            "final_report": {},
            "current_step": WorkflowStep.INITIALIZATION,
            "errors": []
        }

        # Run workflow
        try:
            final_state = await self.workflow.ainvoke(initial_state)

            # Create ComplianceAssessment from final state
            assessment = self._create_compliance_assessment(final_state)

            logger.info("Compliance analysis completed successfully")
            return assessment

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            raise

    def _create_compliance_assessment(self, state: ComplianceState) -> ComplianceAssessment:
        """Create ComplianceAssessment from workflow state"""
        report = state.get("final_report", {})

        # Determine overall compliance status
        ai_act_risk = state.get("ai_act_analysis", {}).get("risk_level", RiskLevel.MINIMAL)
        gdpr_score = state.get("gdpr_analysis", {}).get("compliance_score", 0)

        if ai_act_risk == RiskLevel.UNACCEPTABLE:
            overall_status = ComplianceStatus.NON_COMPLIANT
        elif gdpr_score >= 80 and ai_act_risk in [RiskLevel.MINIMAL, RiskLevel.LIMITED]:
            overall_status = ComplianceStatus.COMPLIANT
        elif gdpr_score >= 50:
            overall_status = ComplianceStatus.PARTIALLY_COMPLIANT
        else:
            overall_status = ComplianceStatus.NON_COMPLIANT

        # Combine all requirements
        all_requirements = []
        if "requirements" in state.get("ai_act_analysis", {}):
            all_requirements.extend(state["ai_act_analysis"]["requirements"])
        if "requirements" in state.get("gdpr_analysis", {}):
            all_requirements.extend(state["gdpr_analysis"]["requirements"])

        return ComplianceAssessment(
            project_id=f"proj_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            project_name=state["project_input"].name,
            risk_level=ai_act_risk,
            overall_status=overall_status,
            compliance_score=gdpr_score,
            ai_act_compliance=state.get("ai_act_analysis", {}),
            gdpr_compliance=state.get("gdpr_analysis", {}),
            sector_compliance=state.get("legal_research", {}).get("sector_specific", {}),
            requirements=all_requirements,
            identified_risks=state.get("risk_assessment", {}).get("compliance_risks", []),
            recommendations=state.get("recommendations", []),
            action_items=[{"action": step, "priority": "HIGH"} for step in report.get("next_steps", [])]
        )
