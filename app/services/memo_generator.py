"""Memo generation utilities using weightage inputs."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple


class MemoGenerator:
    """Generate memo drafts using heuristics.

    In production this service should call Gemini 2.5 (via Vertex AI) to build a
    contextual memo. For local development we generate deterministic text so the
    API remains functional without external dependencies.
    """

    def generate(
        self,
        *,
        company_name: str,
        sector: str,
        founders: List[str],
        extracted_text: Dict[str, str],
        weightage: Dict[str, int],
    ) -> Tuple[Dict[str, Any], datetime]:
        pitch_text = extracted_text.get("pitch_deck", "")
        founder_profiles = [
            {
                "name": name,
                "education": "Not provided",
                "professional_background": "Pending founder interview",
                "previous_ventures": "",
            }
            for name in founders
        ] or [
            {
                "name": "Founder Information Pending",
                "education": "",
                "professional_background": "",
                "previous_ventures": "",
            }
        ]

        summary = pitch_text[:300] + ("..." if len(pitch_text) > 300 else "")
        risk_score = round(
            (weightage.get("team_strength", 20) + weightage.get("traction", 20)) / 40 * 5,
            2,
        )

        memo_body: Dict[str, Any] = {
            "company_overview": {
                "name": company_name,
                "sector": sector,
                "founders": founder_profiles,
                "technology": "Insights require detailed parsing of the pitch deck",
            },
            "market_analysis": {
                "industry_size_and_growth": {
                    "total_addressable_market": {
                        "name": "Total Addressable Market",
                        "value": "Pending validation",
                        "cagr": "Pending",
                        "source": "Requires analyst input",
                    },
                    "serviceable_obtainable_market": {
                        "name": "Serviceable Obtainable Market",
                        "value": "Pending validation",
                        "projection": "Pending",
                        "cagr": "Pending",
                        "source": "Requires analyst input",
                    },
                    "commentary": "Auto-generated summary from available material.",
                },
                "sub_segment_opportunities": ["Further research required"],
                "competitor_details": [
                    {
                        "name": "Competitor Placeholder",
                        "category": sector,
                        "business_model": "Comparable startup",
                        "funding": "Unknown",
                        "margins": "Unknown",
                        "commentary": "Add manually once public data is aggregated.",
                    }
                ],
                "recent_news": "News scraping pipeline not configured in local mode.",
            },
            "business_model": {
                "revenue_streams": "Derived from pitch materials: " + summary,
                "pricing": "Requires analyst confirmation.",
                "unit_economics": "Awaiting data from founder conversation.",
                "scalability": "Linked to team execution and market pull.",
            },
            "financials": {
                "arr_mrr": {
                    "current_booked_arr": "Unavailable",
                    "current_mrr": "Unavailable",
                },
                "burn_and_runway": {
                    "funding_ask": "Pending",
                    "stated_runway": "Pending",
                    "implied_net_burn": "Pending",
                },
                "funding_history": "Provide deal history once verified.",
                "valuation_rationale": "Will be generated from financial data ingestion.",
                "projections": [
                    {
                        "year": "Year 1",
                        "revenue": "To be forecasted",
                    }
                ],
            },
            "claims_analysis": [
                {
                    "claim": "Key growth claim extracted from memo.",
                    "analysis_method": "Simulation placeholder",
                    "input_dataset_length": "0",
                    "simulation_assumptions": "Awaiting dataset",
                    "simulated_probability": f"{max(weightage.get('traction', 20), 1)}%",
                    "result": "Pending validation",
                }
            ],
            "risk_metrics": {
                "composite_risk_score": risk_score,
                "score_interpretation": "Lower is better. Replace once risk engine is integrated.",
                "narrative_justification": "Generated using default heuristics.",
            },
            "conclusion": {
                "overall_attractiveness": "Automatic draft. Requires investment committee review.",
            },
        }

        return memo_body, datetime.utcnow()

