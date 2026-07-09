"""
Validation Agent - Invoice Data Validation + Business Validation
"""
import yaml
import requests
from pathlib import Path
from typing import Dict, List, Any

class ValidationAgent:
    def __init__(self):
        # Load rules
        rules_path = Path(__file__).parent.parent / "configs" / "rules.yaml"
        with open(rules_path, 'r', encoding='utf-8') as f:
            self.rules = yaml.safe_load(f)
        
        self.erp_url = "http://localhost:8001"
        self.tolerances = self.rules['tolerances']
        self.required_fields = self.rules['required_fields']
        self.accepted_currencies = self.rules['accepted_currencies']
    
    def validate(self, invoice_data: Dict) -> Dict:
        """
        Complete validation: Data validation + Business validation
        """
        print(f"Starting validation for Invoice {invoice_data.get('invoice_no')}")
        
        # Step 1: Data Validation
        data_validation = self.data_validation(invoice_data)
        
        # Step 2: Business Validation (ERP comparison)
        business_validation = self.business_validation(invoice_data)
        
        # Combine results
        all_discrepancies = data_validation['discrepancies'] + business_validation['discrepancies']
        
        # Determine recommendation
        recommendation = self._determine_recommendation(
            data_validation, 
            business_validation, 
            invoice_data
        )
        
        result = {
            'invoice_no': invoice_data.get('invoice_no'),
            'is_valid': len(all_discrepancies) == 0,
            'recommendation': recommendation,
            'discrepancies': all_discrepancies,
            'missing_fields': data_validation['missing_fields'],
            'data_validation_passed': data_validation['passed'],
            'business_validation_passed': business_validation['passed'],
            'erp_match_status': business_validation.get('erp_status', 'not_checked')
        }
        print(f"Result: {result['recommendation']}")
        print(f"Discrepancies: {len(all_discrepancies)}")
        return result
    
    def data_validation(self, invoice_data: Dict) -> Dict:
        """Invoice Data Validation - Check completeness and totals"""
        print(f"Data Validation...")
        
        discrepancies = []
        missing_fields = []
        
        # Check required header fields (excluding vendor_id)
        required_header = [f for f in self.required_fields['header'] if f != 'vendor_id']
        for field in required_header:
            if not invoice_data.get(field) or invoice_data.get(field) == 'null':
                missing_fields.append(field)
                discrepancies.append({
                    'field': field,
                    'issue': 'missing',
                    'severity': 'warning',
                    'message': f'Required field {field} is missing'
                })
        
        # Check currency
        currency = invoice_data.get('currency')
        if currency and currency not in self.accepted_currencies:
            discrepancies.append({
                'field': 'currency',
                'issue': 'invalid_currency',
                'severity': 'error',
                'expected': self.accepted_currencies,
                'actual': currency,
                'message': f'Currency {currency} not in accepted list'
            })
        
        # Check line items completeness
        for idx, item in enumerate(invoice_data.get('line_items', [])):
            for field in self.required_fields['line_item']:
                if not item.get(field):
                    discrepancies.append({
                        'field': f'line_items[{idx}].{field}',
                        'issue': 'missing',
                        'severity': 'warning',
                        'message': f'Line item {idx+1} missing {field}'
                    })
            
            # Verify line item total calculation
            if item.get('qty') and item.get('unit_price') and item.get('total'):
                expected_total = round(item['qty'] * item['unit_price'], 2)
                actual_total = round(item['total'], 2)
                if abs(expected_total - actual_total) > 0.01:
                    discrepancies.append({
                        'field': f'line_items[{idx}].total',
                        'issue': 'calculation_error',
                        'severity': 'error',
                        'expected': expected_total,
                        'actual': actual_total,
                        'message': f'Line item {item.get("item_code")} total mismatch'
                    })
        
        passed = len(discrepancies) == 0
        print(f"Data Validation: {'PASS' if passed else 'FAIL'} ({len(discrepancies)} issues)")
        
        return {
            'passed': passed,
            'discrepancies': discrepancies,
            'missing_fields': missing_fields
        }
    
    def business_validation(self, invoice_data: Dict) -> Dict:
        """Business Validation - Compare with ERP data"""
        print(f"Business Validation (ERP)...")
        
        discrepancies = []
        po_number = invoice_data.get('po_number')
        
        if not po_number:
            return {
                'passed': False,
                'discrepancies': [{
                    'field': 'po_number',
                    'issue': 'missing_po',
                    'severity': 'error',
                    'message': 'Cannot validate without PO number'
                }],
                'erp_status': 'no_po'
            }
        
        try:
            # Get PO from ERP
            response = requests.get(f"{self.erp_url}/po/{po_number}", timeout=5)
            
            if response.status_code == 404:
                discrepancies.append({
                    'field': 'po_number',
                    'issue': 'po_not_found',
                    'severity': 'error',
                    'actual': po_number,
                    'message': f'PO {po_number} not found in ERP'
                })
                return {
                    'passed': False,
                    'discrepancies': discrepancies,
                    'erp_status': 'po_not_found'
                }
            
            response.raise_for_status()
            erp_po = response.json()
            
            # Compare line items
            erp_items = {item['item_code']: item for item in erp_po['line_items']}
            
            for invoice_item in invoice_data.get('line_items', []):
                item_code = invoice_item.get('item_code')
                invoice_desc = invoice_item.get('description', '').lower()
                
                # Try to find item by code first
                erp_item = None
                if item_code and item_code in erp_items:
                    erp_item = erp_items[item_code]
                else:
                    # Try to match by description if code not found
                    for erp_code, erp_data in erp_items.items():
                        erp_desc = erp_data.get('description', '').lower()
                        # Check if descriptions match (case-insensitive partial match)
                        if invoice_desc and erp_desc and (invoice_desc in erp_desc or erp_desc in invoice_desc):
                            erp_item = erp_data
                            print(f"      Matched by description: '{invoice_item.get('description')}' → '{erp_data.get('description')}'")
                            break
                
                if not erp_item:
                    discrepancies.append({
                        'field': f'line_item.{item_code}',
                        'issue': 'item_not_in_po',
                        'severity': 'error',
                        'actual': item_code or invoice_desc,
                        'message': f'Item {item_code or invoice_desc} not found in PO {po_number}'
                    })
                    continue
                
                # Check quantity (must match exactly)
                if invoice_item.get('qty') != erp_item['qty']:
                    discrepancies.append({
                        'field': f'{item_code}.qty',
                        'issue': 'quantity_mismatch',
                        'severity': 'error',
                        'expected': erp_item['qty'],
                        'actual': invoice_item.get('qty'),
                        'message': f'{item_code}: Quantity mismatch'
                    })
                
                # Check unit price (5% tolerance)
                invoice_price = invoice_item.get('unit_price', 0)
                erp_price = erp_item['unit_price']
                price_diff_percent = abs((invoice_price - erp_price) / erp_price * 100) if erp_price else 0
                
                if price_diff_percent > self.tolerances['price_difference_percent']:
                    discrepancies.append({
                        'field': f'{item_code}.unit_price',
                        'issue': 'price_discrepancy',
                        'severity': 'warning',
                        'expected': erp_price,
                        'actual': invoice_price,
                        'difference_percent': round(price_diff_percent, 2),
                        'message': f'{item_code}: Price differs by {price_diff_percent:.1f}% (tolerance: {self.tolerances["price_difference_percent"]}%)'
                    })
            
            passed = len(discrepancies) == 0
            erp_status = 'match' if passed else 'discrepancy'
            
            print(f"Business Validation: {'PASS' if passed else 'FAIL'} ({len(discrepancies)} issues)")
            
            return {
                'passed': passed,
                'discrepancies': discrepancies,
                'erp_status': erp_status,
                'erp_po': erp_po
            }
            
        except requests.exceptions.ConnectionError:
            print(f"ERP API not available")
            return {
                'passed': False,
                'discrepancies': [{
                    'field': 'erp',
                    'issue': 'erp_unavailable',
                    'severity': 'warning',
                    'message': 'ERP API not available for validation'
                }],
                'erp_status': 'unavailable'
            }
        except Exception as e:
            print(f"ERP validation error: {e}")
            return {
                'passed': False,
                'discrepancies': [{
                    'field': 'erp',
                    'issue': 'validation_error',
                    'severity': 'error',
                    'message': str(e)
                }],
                'erp_status': 'error'
            }
    
    def _determine_recommendation(self, data_val: Dict, biz_val: Dict, invoice_data: Dict) -> str:
        """Determine final recommendation"""
        # Check translation confidence
        translation_confidence = invoice_data.get('translation_confidence', 1.0)
        auto_approve_threshold = self.rules['validation_policies']['auto_approve_confidence_threshold']
        
        # Count severity
        errors = sum(1 for d in data_val['discrepancies'] + biz_val['discrepancies'] if d.get('severity') == 'error')
        warnings = sum(1 for d in data_val['discrepancies'] + biz_val['discrepancies'] if d.get('severity') == 'warning')
        
        # Only approve or manual_review (no auto-reject)
        # Human must explicitly reject if needed
        if errors > 0:
            return 'reject'  # Changed from 'reject' to 'manual_review'
        elif warnings > 0 or translation_confidence < auto_approve_threshold:
            return 'manual_review'
        else:
            return 'approve'
