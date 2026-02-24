"""
What-If Analyzer Service
Scenario analysis and sensitivity testing for rank & rent decisions
"""

from typing import List, Dict, Optional
import copy


class WhatIfAnalyzer:
    def __init__(self):
        from services.scoring_engine import ScoringEngine
        self.scoring_engine = ScoringEngine()
    
    def analyze_scenario(self, scenario: Dict) -> Dict:
        """
        Run a what-if scenario analysis.
        Supports weight changes, threshold changes, and category focus.
        """
        scenario_type = scenario.get("type", "weight_change")
        
        if scenario_type == "weight_change":
            return self._analyze_weight_change(scenario)
        elif scenario_type == "threshold_change":
            return self._analyze_threshold_change(scenario)
        elif scenario_type == "category_focus":
            return self._analyze_category_focus(scenario)
        elif scenario_type == "site_score":
            return self._analyze_site_score_change(scenario)
        else:
            return {"error": f"Unknown scenario type: {scenario_type}"}
    
    def _analyze_weight_change(self, scenario: Dict) -> Dict:
        """Analyze impact of changing criterion weights"""
        weight_changes = scenario.get("weight_changes", {})
        
        # Get current portfolio
        original_portfolio = self.scoring_engine.portfolio.copy()
        original_summary = self.scoring_engine.get_portfolio_summary()
        
        # Store original weights
        original_weights = {
            criterion: data["weight"] 
            for criterion, data in self.scoring_engine.criteria.items()
        }
        
        # Apply weight changes
        new_weights = original_weights.copy()
        for criterion, new_weight in weight_changes.items():
            if criterion in new_weights:
                new_weights[criterion] = new_weight
        
        # Normalize weights to 100
        total_weight = sum(new_weights.values())
        if total_weight != 100:
            factor = 100 / total_weight
            new_weights = {k: v * factor for k, v in new_weights.items()}
        
        # Recalculate all scores with new weights
        recalculated_sites = []
        for site in original_portfolio:
            # Create site data for scoring
            site_data = {
                "name": site["name"],
                "category": site["category"],
                "city": site["city"],
                "state": site["state"]
            }
            # Add any existing criteria scores
            site_data.update(site.get("criteria_scores", {}))
            
            # Temporarily update weights
            for criterion, weight in new_weights.items():
                if criterion in self.scoring_engine.criteria:
                    self.scoring_engine.criteria[criterion]["weight"] = weight
            
            # Calculate new score
            result = self.scoring_engine.calculate_score(site_data)
            recalculated_sites.append({
                "id": site["id"],
                "name": site["name"],
                "category": site["category"],
                "original_score": site["score"],
                "new_score": result["score"],
                "score_change": round(result["score"] - site["score"], 2),
                "original_tier": site["tier"],
                "new_tier": result["tier"],
                "tier_changed": site["tier"] != result["tier"]
            })
        
        # Restore original weights
        for criterion, weight in original_weights.items():
            if criterion in self.scoring_engine.criteria:
                self.scoring_engine.criteria[criterion]["weight"] = weight
        
        # Calculate new tier distribution
        new_activate = len([s for s in recalculated_sites if s["new_tier"] == "activate"])
        new_watchlist = len([s for s in recalculated_sites if s["new_tier"] == "watchlist"])
        new_sunset = len([s for s in recalculated_sites if s["new_tier"] == "sunset"])
        
        # Sites that changed tiers
        tier_changes = [s for s in recalculated_sites if s["tier_changed"]]
        
        return {
            "scenario_type": "weight_change",
            "weight_changes": weight_changes,
            "normalized_weights": new_weights,
            "impact_summary": {
                "sites_rescored": len(recalculated_sites),
                "tier_changes": len(tier_changes),
                "average_score_change": round(
                    sum(s["score_change"] for s in recalculated_sites) / len(recalculated_sites), 2
                )
            },
            "tier_distribution": {
                "original": {
                    "activate": original_summary["tier_distribution"]["activate"],
                    "watchlist": original_summary["tier_distribution"]["watchlist"],
                    "sunset": original_summary["tier_distribution"]["sunset"]
                },
                "new": {
                    "activate": new_activate,
                    "watchlist": new_watchlist,
                    "sunset": new_sunset
                },
                "changes": {
                    "activate": new_activate - original_summary["tier_distribution"]["activate"],
                    "watchlist": new_watchlist - original_summary["tier_distribution"]["watchlist"],
                    "sunset": new_sunset - original_summary["tier_distribution"]["sunset"]
                }
            },
            "tier_change_details": tier_changes,
            "all_sites_rescored": sorted(recalculated_sites, key=lambda x: x["new_score"], reverse=True)
        }
    
    def _analyze_threshold_change(self, scenario: Dict) -> Dict:
        """Analyze impact of changing tier thresholds"""
        activate_threshold = scenario.get("activate_threshold", 3.7)
        watchlist_threshold = scenario.get("watchlist_threshold", 3.2)
        
        portfolio = self.scoring_engine.portfolio
        original_summary = self.scoring_engine.get_portfolio_summary()
        
        def get_tier(score):
            if score >= activate_threshold:
                return "activate"
            elif score >= watchlist_threshold:
                return "watchlist"
            else:
                return "sunset"
        
        recategorized = []
        for site in portfolio:
            new_tier = get_tier(site["score"])
            recategorized.append({
                "id": site["id"],
                "name": site["name"],
                "score": site["score"],
                "original_tier": site["tier"],
                "new_tier": new_tier,
                "tier_changed": site["tier"] != new_tier
            })
        
        new_activate = len([s for s in recategorized if s["new_tier"] == "activate"])
        new_watchlist = len([s for s in recategorized if s["new_tier"] == "watchlist"])
        new_sunset = len([s for s in recategorized if s["new_tier"] == "sunset"])
        
        tier_changes = [s for s in recategorized if s["tier_changed"]]
        
        return {
            "scenario_type": "threshold_change",
            "thresholds": {
                "original": {"activate": 3.7, "watchlist": 3.2},
                "new": {"activate": activate_threshold, "watchlist": watchlist_threshold}
            },
            "impact_summary": {
                "tier_changes": len(tier_changes),
                "sites_promoted": len([s for s in tier_changes 
                    if (s["original_tier"] == "sunset" and s["new_tier"] == "watchlist") or
                       (s["original_tier"] == "sunset" and s["new_tier"] == "activate") or
                       (s["original_tier"] == "watchlist" and s["new_tier"] == "activate")]),
                "sites_demoted": len([s for s in tier_changes 
                    if (s["original_tier"] == "activate" and s["new_tier"] == "watchlist") or
                       (s["original_tier"] == "activate" and s["new_tier"] == "sunset") or
                       (s["original_tier"] == "watchlist" and s["new_tier"] == "sunset")])
            },
            "tier_distribution": {
                "original": original_summary["tier_distribution"],
                "new": {
                    "activate": new_activate,
                    "watchlist": new_watchlist,
                    "sunset": new_sunset
                }
            },
            "tier_change_details": tier_changes
        }
    
    def _analyze_category_focus(self, scenario: Dict) -> Dict:
        """Analyze portfolio if focused on specific categories"""
        focus_categories = scenario.get("categories", [])
        
        portfolio = self.scoring_engine.portfolio
        original_summary = self.scoring_engine.get_portfolio_summary()
        
        # Filter to focus categories
        focused_portfolio = [s for s in portfolio if s["category"] in focus_categories]
        excluded_portfolio = [s for s in portfolio if s["category"] not in focus_categories]
        
        # Calculate focused metrics
        focused_activate = [s for s in focused_portfolio if s["tier"] == "activate"]
        focused_watchlist = [s for s in focused_portfolio if s["tier"] == "watchlist"]
        focused_sunset = [s for s in focused_portfolio if s["tier"] == "sunset"]
        
        focused_potential = sum(s["monthly_potential"] for s in focused_portfolio)
        excluded_potential = sum(s["monthly_potential"] for s in excluded_portfolio)
        
        return {
            "scenario_type": "category_focus",
            "focus_categories": focus_categories,
            "impact_summary": {
                "focused_sites": len(focused_portfolio),
                "excluded_sites": len(excluded_portfolio),
                "focused_potential": focused_potential,
                "excluded_potential": excluded_potential,
                "potential_retained_pct": round(focused_potential / original_summary["revenue_potential"]["total_monthly"] * 100, 1)
            },
            "focused_tier_distribution": {
                "activate": len(focused_activate),
                "watchlist": len(focused_watchlist),
                "sunset": len(focused_sunset)
            },
            "focused_sites": sorted(focused_portfolio, key=lambda x: x["score"], reverse=True),
            "excluded_sites": sorted(excluded_portfolio, key=lambda x: x["score"], reverse=True),
            "recommendation": self._get_focus_recommendation(focus_categories, focused_portfolio, excluded_portfolio)
        }
    
    def _get_focus_recommendation(self, categories: List[str], 
                                  focused: List[Dict], 
                                  excluded: List[Dict]) -> str:
        """Generate recommendation for category focus scenario"""
        focused_avg = sum(s["score"] for s in focused) / len(focused) if focused else 0
        excluded_avg = sum(s["score"] for s in excluded) / len(excluded) if excluded else 0
        
        if focused_avg >= 3.5 and len(focused) >= 10:
            return f"RECOMMENDED: Focusing on {', '.join(categories)} captures high-performing sites with avg score {focused_avg:.2f}"
        elif focused_avg >= 3.2:
            return f"MODERATE: This focus has avg score {focused_avg:.2f}. Consider adding more categories for better coverage."
        else:
            return f"NOT RECOMMENDED: Avg score of {focused_avg:.2f} is below optimal. Expand category selection."
    
    def _analyze_site_score_change(self, scenario: Dict) -> Dict:
        """Analyze impact of specific score changes on individual sites"""
        site_changes = scenario.get("site_changes", {})
        
        portfolio = copy.deepcopy(self.scoring_engine.portfolio)
        
        results = []
        for site_id, new_score in site_changes.items():
            site = next((s for s in portfolio if s["id"] == site_id), None)
            if site:
                original_score = site["score"]
                original_tier = site["tier"]
                
                new_tier = self.scoring_engine._get_tier(new_score)
                
                results.append({
                    "site_id": site_id,
                    "name": site["name"],
                    "original_score": original_score,
                    "new_score": new_score,
                    "score_change": round(new_score - original_score, 2),
                    "original_tier": original_tier,
                    "new_tier": new_tier,
                    "tier_changed": original_tier != new_tier
                })
        
        return {
            "scenario_type": "site_score_change",
            "changes_analyzed": len(results),
            "tier_changes": len([r for r in results if r["tier_changed"]]),
            "details": results
        }
    
    def weight_sensitivity_analysis(self, site_id: str = None, 
                                   criterion: str = "local_search_demand",
                                   range_min: float = 0, 
                                   range_max: float = 20,
                                   steps: int = 10) -> Dict:
        """
        Analyze how changing a specific weight affects scores.
        Can analyze overall portfolio or a specific site.
        """
        step_size = (range_max - range_min) / steps
        test_weights = [range_min + i * step_size for i in range(steps + 1)]
        
        results = []
        
        original_weight = self.scoring_engine.criteria.get(criterion, {}).get("weight", 10)
        
        for test_weight in test_weights:
            # Temporarily set weight
            if criterion in self.scoring_engine.criteria:
                self.scoring_engine.criteria[criterion]["weight"] = test_weight
            
            if site_id:
                # Analyze specific site
                site = self.scoring_engine.get_site_by_id(site_id)
                if site:
                    site_data = {
                        "name": site["name"],
                        "category": site["category"],
                        "city": site["city"],
                        "state": site["state"]
                    }
                    result = self.scoring_engine.calculate_score(site_data)
                    results.append({
                        "weight": test_weight,
                        "score": result["score"],
                        "tier": result["tier"]
                    })
            else:
                # Analyze portfolio
                portfolio = self.scoring_engine.portfolio
                activate_count = 0
                watchlist_count = 0
                sunset_count = 0
                total_score = 0
                
                for site in portfolio:
                    site_data = {
                        "name": site["name"],
                        "category": site["category"],
                        "city": site["city"],
                        "state": site["state"]
                    }
                    result = self.scoring_engine.calculate_score(site_data)
                    total_score += result["score"]
                    if result["tier"] == "activate":
                        activate_count += 1
                    elif result["tier"] == "watchlist":
                        watchlist_count += 1
                    else:
                        sunset_count += 1
                
                results.append({
                    "weight": test_weight,
                    "avg_score": round(total_score / len(portfolio), 2),
                    "activate_count": activate_count,
                    "watchlist_count": watchlist_count,
                    "sunset_count": sunset_count
                })
        
        # Restore original weight
        if criterion in self.scoring_engine.criteria:
            self.scoring_engine.criteria[criterion]["weight"] = original_weight
        
        return {
            "criterion": criterion,
            "original_weight": original_weight,
            "test_range": {"min": range_min, "max": range_max, "steps": steps},
            "site_id": site_id,
            "results": results,
            "insights": self._generate_sensitivity_insights(criterion, results, site_id)
        }
    
    def _generate_sensitivity_insights(self, criterion: str, 
                                       results: List[Dict], 
                                       site_id: str) -> List[str]:
        """Generate insights from sensitivity analysis"""
        insights = []
        
        if site_id:
            # Site-specific insights
            scores = [r["score"] for r in results]
            score_range = max(scores) - min(scores)
            insights.append(f"Score varies by {score_range:.2f} across weight range")
            
            tier_changes = len(set(r["tier"] for r in results))
            if tier_changes > 1:
                insights.append(f"Tier changes at different weights - sensitive criterion")
            else:
                insights.append(f"Tier remains stable - low sensitivity to this criterion")
        else:
            # Portfolio insights
            activate_range = max(r["activate_count"] for r in results) - min(r["activate_count"] for r in results)
            insights.append(f"Activate tier varies by {activate_range} sites across weight range")
            
            if activate_range >= 5:
                insights.append(f"{criterion} is HIGH IMPACT - significantly affects tier distribution")
            elif activate_range >= 2:
                insights.append(f"{criterion} has MODERATE IMPACT on tier distribution")
            else:
                insights.append(f"{criterion} has LOW IMPACT - consider reducing weight")
        
        return insights
    
    def tier_threshold_analysis(self, activate_threshold: float = 3.7,
                               watchlist_threshold: float = 3.2) -> Dict:
        """Analyze impact of changing tier thresholds"""
        return self._analyze_threshold_change({
            "activate_threshold": activate_threshold,
            "watchlist_threshold": watchlist_threshold
        })
    
    def category_focus_analysis(self, categories: List[str]) -> Dict:
        """Analyze portfolio focused on specific categories"""
        return self._analyze_category_focus({"categories": categories})

# Singleton instance for import
whatif_analyzer = WhatIfAnalyzer()
