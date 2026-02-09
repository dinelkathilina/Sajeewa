"""
Validation Engine for QS Checks
Implements validation logic for variation proposals
"""
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session as DBSession
from .database import Variation, VariationDetail, BOQItem, Activity


class ValidationEngine:
    """Handles QS validation checks for variation proposals"""
    
    def __init__(self, db: DBSession):
        self.db = db
    
    def validate_variation(self, variation_id: int) -> Dict[str, Any]:
        """
        Perform comprehensive validation on a variation
        
        Returns:
            Dictionary with validation results
        """
        variation = self.db.query(Variation).filter(Variation.id == variation_id).first()
        if not variation:
            return {'valid': False, 'error': 'Variation not found'}
        
        validation_results = {
            'variation_id': variation_id,
            'valid': True,
            'warnings': [],
            'errors': [],
            'checks': {}
        }
        
        # Run all validation checks
        validation_results['checks']['double_counting'] = self.check_double_counting(variation)
        validation_results['checks']['omission_valuation'] = self.validate_omission_valuation(variation)
        validation_results['checks']['delay_propagation'] = self.verify_delay_propagation(variation)
        validation_results['checks']['rate_reasonableness'] = self.check_rate_reasonableness(variation)
        
        # Collect warnings and errors
        for check_name, check_result in validation_results['checks'].items():
            if check_result.get('warnings'):
                validation_results['warnings'].extend(check_result['warnings'])
            if check_result.get('errors'):
                validation_results['errors'].extend(check_result['errors'])
        
        # Determine overall validity
        if validation_results['errors']:
            validation_results['valid'] = False
            validation_results['status'] = 'failed'
        elif validation_results['warnings']:
            validation_results['status'] = 'warnings'
        else:
            validation_results['status'] = 'passed'
        
        # Update variation record
        variation.validation_status = validation_results['status']
        variation.validation_notes = self._format_validation_notes(validation_results)
        self.db.commit()
        
        return validation_results
    
    def check_double_counting(self, variation: Variation) -> Dict[str, Any]:
        """
        Check for potential double counting of costs
        
        Returns:
            Dictionary with check results
        """
        result = {
            'passed': True,
            'warnings': [],
            'errors': [],
            'details': {}
        }
        
        # Get all variation details
        details = variation.details
        if not details:
            return result
        
        # Check for duplicate BOQ items
        boq_item_ids = [d.boq_item_id for d in details if d.boq_item_id]
        duplicates = [item_id for item_id in set(boq_item_ids) if boq_item_ids.count(item_id) > 1]
        
        if duplicates:
            result['warnings'].append(
                f"Potential double counting detected: BOQ items {duplicates} appear multiple times"
            )
            result['details']['duplicate_items'] = duplicates
        
        # Check for overlapping descriptions
        descriptions = [d.original_description.lower() for d in details]
        for i, desc1 in enumerate(descriptions):
            for j, desc2 in enumerate(descriptions[i+1:], start=i+1):
                # Simple similarity check (can be enhanced)
                common_words = set(desc1.split()) & set(desc2.split())
                if len(common_words) > 3:  # More than 3 common words
                    result['warnings'].append(
                        f"Potential overlap between items {i+1} and {j+1}: similar descriptions"
                    )
        
        return result
    
    def validate_omission_valuation(self, variation: Variation) -> Dict[str, Any]:
        """
        Validate that omissions are correctly valued
        
        Returns:
            Dictionary with check results
        """
        result = {
            'passed': True,
            'warnings': [],
            'errors': [],
            'details': {}
        }
        
        # Check if this is an omission variation (Type 4)
        if variation.variation_type_id == 4:  # Type 4: Omission of Work
            details = variation.details
            
            for detail in details:
                # Omissions should have negative cost impact
                if detail.cost_impact > 0:
                    result['errors'].append(
                        f"Omission item '{detail.original_description}' has positive cost impact. "
                        f"Omissions should reduce contract value."
                    )
                    result['passed'] = False
                
                # New quantity should be less than original for omissions
                if detail.new_quantity >= detail.original_quantity:
                    result['warnings'].append(
                        f"Omission item '{detail.original_description}' has new quantity >= original. "
                        f"Verify this is correct."
                    )
        
        # Check for any negative quantities in non-omission variations
        elif variation.details:
            for detail in variation.details:
                if detail.new_quantity < 0:
                    result['warnings'].append(
                        f"Item '{detail.original_description}' has negative quantity. "
                        f"Consider using Omission variation type."
                    )
        
        return result
    
    def verify_delay_propagation(self, variation: Variation) -> Dict[str, Any]:
        """
        Verify that delay propagation logic is correct
        
        Returns:
            Dictionary with check results
        """
        result = {
            'passed': True,
            'warnings': [],
            'errors': [],
            'details': {}
        }
        
        # Check if variation has time impact
        if variation.time_impact == 0:
            return result  # No time impact to validate
        
        # Get affected activities
        affected_activities = variation.affected_activities or []
        
        if not affected_activities:
            result['warnings'].append(
                f"Variation claims {variation.time_impact} days EOT but no affected activities identified"
            )
            return result
        
        # Load activities from database
        activities = self.db.query(Activity).filter(
            Activity.project_id == variation.project_id,
            Activity.activity_id.in_(affected_activities)
        ).all()
        
        # Check if affected activities are on critical path
        critical_activities = [a for a in activities if a.is_critical == 1]
        
        if variation.time_impact > 0 and not critical_activities:
            result['warnings'].append(
                "EOT claimed but affected activities are not on critical path. "
                "Verify that delay exceeds available float."
            )
        
        # Check if EOT is reasonable compared to activity durations
        total_activity_duration = sum(a.duration for a in activities)
        if variation.time_impact > total_activity_duration * 2:
            result['warnings'].append(
                f"EOT of {variation.time_impact} days seems excessive compared to "
                f"affected activity durations ({total_activity_duration} days total)"
            )
        
        result['details']['affected_activities_count'] = len(activities)
        result['details']['critical_activities_count'] = len(critical_activities)
        
        return result
    
    def check_rate_reasonableness(self, variation: Variation) -> Dict[str, Any]:
        """
        Check if rates are reasonable compared to original BOQ
        
        Returns:
            Dictionary with check results
        """
        result = {
            'passed': True,
            'warnings': [],
            'errors': [],
            'details': {}
        }
        
        details = variation.details
        if not details:
            return result
        
        excessive_increases = []
        for detail in details:
            if detail.original_rate > 0:
                rate_increase_pct = ((detail.new_rate - detail.original_rate) / detail.original_rate) * 100
                
                # Flag increases > 50%
                if rate_increase_pct > 50:
                    excessive_increases.append({
                        'item': detail.original_description,
                        'original_rate': detail.original_rate,
                        'new_rate': detail.new_rate,
                        'increase_pct': rate_increase_pct
                    })
                    
                    result['warnings'].append(
                        f"Item '{detail.original_description}': Rate increased by {rate_increase_pct:.1f}% "
                        f"(from {detail.original_rate} to {detail.new_rate}). Ensure justification is provided."
                    )
        
        result['details']['excessive_increases'] = excessive_increases
        
        return result
    
    def _format_validation_notes(self, validation_results: Dict) -> str:
        """Format validation results into readable notes"""
        notes = []
        
        if validation_results['status'] == 'passed':
            notes.append("All validation checks passed.")
        elif validation_results['status'] == 'warnings':
            notes.append(f"Validation passed with {len(validation_results['warnings'])} warning(s):")
            for warning in validation_results['warnings']:
                notes.append(f"  - {warning}")
        else:
            notes.append(f"Validation failed with {len(validation_results['errors'])} error(s):")
            for error in validation_results['errors']:
                notes.append(f"  - {error}")
        
        return "\n".join(notes)
    
    def generate_validation_report(self, variation_id: int) -> str:
        """
        Generate a comprehensive validation report
        
        Returns:
            Formatted validation report string
        """
        validation_results = self.validate_variation(variation_id)
        
        report = []
        report.append("=" * 60)
        report.append("VARIATION VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"Variation ID: {variation_id}")
        report.append(f"Overall Status: {validation_results['status'].upper()}")
        report.append("")
        
        # Individual checks
        report.append("VALIDATION CHECKS:")
        report.append("-" * 60)
        for check_name, check_result in validation_results['checks'].items():
            status = "✓ PASS" if check_result['passed'] else "✗ FAIL"
            report.append(f"{check_name.replace('_', ' ').title()}: {status}")
            
            if check_result.get('warnings'):
                for warning in check_result['warnings']:
                    report.append(f"  ⚠ {warning}")
            
            if check_result.get('errors'):
                for error in check_result['errors']:
                    report.append(f"  ✗ {error}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
