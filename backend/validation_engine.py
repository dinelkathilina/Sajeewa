"""
Validation Engine for QS Checks
Implements validation logic for variation proposals
"""
from typing import Dict, List, Any, Optional
from .storage_manager import StorageManager


class ValidationEngine:
    """Handles QS validation checks for variation proposals using StorageManager"""
    
    def __init__(self, storage: StorageManager):
        self.storage = storage
    
    def validate_variation(self, project_id: int, variation_id: int) -> Dict[str, Any]:
        """Perform comprehensive validation on a variation"""
        variation = self.storage.get_variation(project_id, variation_id)
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
        validation_results['checks']['delay_propagation'] = self.verify_delay_propagation(project_id, variation)
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
        
        # Update variation record in storage
        variation['validation_status'] = validation_results['status']
        variation['validation_notes'] = self._format_validation_notes(validation_results)
        
        # Save updated variation
        project = self.storage.get_project(project_id)
        for i, v in enumerate(project.get("variations", [])):
            if v["id"] == variation_id:
                project["variations"][i] = variation
                break
        self.storage.update_project(project_id, {"variations": project["variations"]})
        
        return validation_results
    
    def check_double_counting(self, variation: Dict) -> Dict[str, Any]:
        """Check for potential double counting of costs"""
        result = {'passed': True, 'warnings': [], 'errors': [], 'details': {}}
        
        details = variation.get('details', [])
        if not details: return result
        
        boq_item_ids = [d.get('boq_item_id') for d in details if d.get('boq_item_id')]
        duplicates = [item_id for item_id in set(boq_item_ids) if boq_item_ids.count(item_id) > 1]
        
        if duplicates:
            result['warnings'].append(f"Potential double counting: BOQ items {duplicates} appear multiple times")
            result['details']['duplicate_items'] = duplicates
        
        descriptions = [d.get('original_description', '').lower() for d in details]
        for i, desc1 in enumerate(descriptions):
            for j, desc2 in enumerate(descriptions[i+1:], start=i+1):
                common_words = set(desc1.split()) & set(desc2.split())
                if len(common_words) > 3:
                    result['warnings'].append(f"Potential overlap between item {i+1} and {j+1}: similar descriptions")
        
        return result
    
    def validate_omission_valuation(self, variation: Dict) -> Dict[str, Any]:
        """Validate that omissions are correctly valued"""
        result = {'passed': True, 'warnings': [], 'errors': [], 'details': {}}
        
        # Assuming variation_type check (FIDIC Type 4 is omission)
        metadata = variation.get('metadata', {})
        if metadata.get('variation_type') == 'TYPE4':
            details = variation.get('details', [])
            for detail in details:
                if detail.get('cost_impact', 0) > 0:
                    result['errors'].append(f"Omission item '{detail.get('original_description')}' has positive cost impact.")
                    result['passed'] = False
                
                if detail.get('new_quantity', 0) >= detail.get('original_quantity', 0):
                    result['warnings'].append(f"Omission item '{detail.get('original_description')}' has new quantity >= original.")
        
        elif variation.get('details'):
            for detail in variation['details']:
                if detail.get('new_quantity', 0) < 0:
                    result['warnings'].append(f"Item '{detail.get('original_description')}' has negative quantity.")
        
        return result
    
    def verify_delay_propagation(self, project_id: int, variation: Dict) -> Dict[str, Any]:
        """Verify that delay propagation logic is correct"""
        result = {'passed': True, 'warnings': [], 'errors': [], 'details': {}}
        
        if variation.get('time_impact', 0) == 0:
            return result
        
        affected_activities = variation.get('affected_activities') or []
        if not affected_activities:
            result['warnings'].append(f"Variation claims {variation['time_impact']} days EOT but no activities identified")
            return result
        
        project = self.storage.get_project(project_id)
        activities = [a for a in project.get('activities', []) if a['activity_id'] in affected_activities]
        critical_activities = [a for a in activities if a.get('is_critical') == 1]
        
        if variation['time_impact'] > 0 and not critical_activities:
            result['warnings'].append("EOT claimed but affected activities are not on critical path.")
        
        total_activity_duration = sum(a.get('duration', 0) for a in activities)
        if variation['time_impact'] > total_activity_duration * 2:
            result['warnings'].append(f"EOT seems excessive compared to activity durations.")
        
        return result
    
    def check_rate_reasonableness(self, variation: Dict) -> Dict[str, Any]:
        """Check if rates are reasonable compared to original BOQ"""
        result = {'passed': True, 'warnings': [], 'errors': [], 'details': {}}
        
        details = variation.get('details', [])
        if not details: return result
        
        excessive_increases = []
        for detail in details:
            orig_rate = detail.get('original_rate', 0)
            new_rate = detail.get('new_rate', 0)
            if orig_rate > 0:
                rate_increase_pct = ((new_rate - orig_rate) / orig_rate) * 100
                if rate_increase_pct > 50:
                    excessive_increases.append({'item': detail.get('original_description'), 'increase_pct': rate_increase_pct})
                    result['warnings'].append(f"Item '{detail.get('original_description')}': Rate increased by {rate_increase_pct:.1f}%")
        
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
    
    def generate_validation_report(self, project_id: int, variation_id: int) -> str:
        """Generate a comprehensive validation report"""
        validation_results = self.validate_variation(project_id, variation_id)
        
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
