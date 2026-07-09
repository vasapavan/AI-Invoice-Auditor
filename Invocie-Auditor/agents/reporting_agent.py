"""
Reporting Agent - Generates concise audit reports using LLM
"""
import json
import yaml
import time
from pathlib import Path
from datetime import datetime
from typing import Dict
from litellm import completion, RateLimitError


class ReportingAgent:
    def __init__(self):
        # Load persona configuration
        config_path = Path(__file__).parent.parent / "configs" / "persona_reporting_agent.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.model = self.config['model']
        self.temperature = self.config['temperature']
        self.max_tokens = self.config['max_tokens']

        self.reports_dir = Path("./outputs/reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, invoice_data: Dict, validation_result: Dict) -> Dict:
        """
        Generate concise audit report using LLM with retry and delay
        """
        invoice_no = invoice_data.get('invoice_no', 'UNKNOWN')
        print(f"Generating report for Invoice {invoice_no}...")

        # Check if human override exists
        human_override = validation_result.get('human_override', {})
        has_human_verification = bool(human_override)

        # Prepare data for LLM
        discrepancies_list = self._format_discrepancies(validation_result.get('discrepancies', []))

        # Add human verification info to prompt if applicable
        human_verification_text = ""
        if has_human_verification:
            human_verification_text = f"""
            HUMAN VERIFICATION:
            - Original Recommendation: {human_override.get('original_recommendation', 'N/A').upper()}
            - Human Decision: {human_override.get('decision', validation_result.get('recommendation')).upper()}
            - Reason: {human_override.get('reason', 'No reason provided')}
            - Verified by: Human Reviewer
            """

        # Create prompt
        prompt = self.config['report_generation_prompt'].format(
            invoice_no=invoice_data.get('invoice_no', 'N/A'),
            po_number=invoice_data.get('po_number', 'N/A'),
            vendor_name=invoice_data.get('vendor_name', 'N/A'),
            invoice_date=invoice_data.get('invoice_date', 'N/A'),
            currency=invoice_data.get('currency', 'N/A'),
            total_amount=invoice_data.get('total_amount', 0),
            line_items_count=len(invoice_data.get('line_items', [])),
            original_language=invoice_data.get('original_language', 'Unknown'),
            was_translated=invoice_data.get('was_translated', False),
            translation_confidence=invoice_data.get('translation_confidence', 1.0),
            data_validation_passed='PASS' if validation_result.get('data_validation_passed') else 'FAIL',
            business_validation_passed='PASS' if validation_result.get('business_validation_passed') else 'FAIL',
            erp_match_status=validation_result.get('erp_match_status', 'not_checked'),
            discrepancies_count=len(validation_result.get('discrepancies', [])),
            discrepancies_list=discrepancies_list,
            missing_fields=', '.join(validation_result.get('missing_fields', [])) or 'None',
            recommendation=validation_result.get('recommendation', 'unknown').upper()
        )

        # Add human verification info
        if has_human_verification:
            prompt += f"\n\n{human_verification_text}"
            prompt += "\n\nIMPORTANT: Include in the report that this invoice was HUMAN VERIFIED and mention the human's decision and reasoning."

        # --- Retry logic for rate limits ---
        retries = 5
        delay = 30
        for attempt in range(retries):
            try:
                response = completion(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.config['system_prompt']},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                break
            except RateLimitError as e:
                print(f"⚠️ Rate limit hit. Waiting {delay} seconds before retrying... ({attempt+1}/{retries})")
                time.sleep(delay)
            except Exception as e:
                print(f"❌ Unexpected LLM error: {e}")
                return None
        else:
            print("❌ Failed after multiple retries due to rate limits.")
            return None

        # --- Process the successful response ---
        report_text = response.choices[0].message.content.strip()

        if has_human_verification:
            report_text = f"HUMAN VERIFIED \n\n{report_text}"

        report_data = {
            'report_id': f"RPT-{invoice_no}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'generated_at': datetime.now().isoformat(),
            'human_verified': has_human_verification,
            'invoice_summary': {
                'invoice_no': invoice_data.get('invoice_no'),
                'po_number': invoice_data.get('po_number'),
                'vendor_name': invoice_data.get('vendor_name'),
                'total_amount': invoice_data.get('total_amount'),
                'currency': invoice_data.get('currency')
            },
            'recommendation': validation_result.get('recommendation'),
            'discrepancies_count': len(validation_result.get('discrepancies', [])),
            'human_override': human_override if has_human_verification else None,
            'report': report_text,
            'full_data': {
                'invoice_data': invoice_data,
                'validation_result': validation_result
            }
        }

        json_path = self._save_json(report_data)
        print(f"✅ Report generated and saved: {json_path.name}")
        if has_human_verification:
            print("👤 Human verification included in report.")

        return {
            'report_id': report_data['report_id'],
            'report_text': report_text,
            'json_path': str(json_path),
            'human_verified': has_human_verification
        }

    def _format_discrepancies(self, discrepancies: list) -> str:
        """Format discrepancies for LLM prompt"""
        if not discrepancies:
            return "None"

        formatted = []
        for i, disc in enumerate(discrepancies[:5], 1):  # Top 5
            severity = disc.get('severity', 'info').upper()
            message = disc.get('message', 'Unknown issue')
            formatted.append(f"{i}. [{severity}] {message}")

        return '\n'.join(formatted)

    def _save_json(self, report_data: Dict) -> Path:
        """Save JSON report"""
        filename = f"{report_data['report_id']}.json"
        file_path = self.reports_dir / filename

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        return file_path
