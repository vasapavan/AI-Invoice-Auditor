"""
Invoice Auditor Workflow - Main LangGraph implementation
"""
from typing import TypedDict
from pathlib import Path
from datetime import datetime
import json
from langgraph.graph import StateGraph, START, END

from agents.extractor_agent import ExtractorAgent
from agents.translation_agent import TranslationAgent
from agents.validation_agent import ValidationAgent
from agents.reporting_agent import ReportingAgent
from agents.rag_agents.rag_pipeline import RAGPipeline

# Define the state schema
class InvoiceState(TypedDict):
    """State for invoice auditor workflow"""
    # Input
    file_path: str
    
    # Extraction
    raw_text: str
    
    # Translation
    translated_text: str
    original_language: str
    translation_confidence: float
    was_translated: bool
    
    # Structured data
    invoice_data: dict
    
    # Validation
    validation_result: dict
    
    # Reporting
    report_text: str
    report_path: str
    
    # RAG Query
    rag_query: str
    rag_answer: str
    rag_sources: list
    rag_evaluation: dict
    
    # Status
    status: str
    error: str

class InvoiceAuditorWorkflow:
    """Main LangGraph workflow for invoice auditing"""
    
    def __init__(self):
        # Initialize agents
        self.extractor = ExtractorAgent()
        self.translator = TranslationAgent()
        self.validator = ValidationAgent()
        self.reporter = ReportingAgent()
        self.rag_pipeline = RAGPipeline()
        
        # Review queue for human-in-the-loop
        self.review_queue_file = Path("./data/review_queue.json")
        self.review_queue_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Build the graph
        self.graph = self._build_graph()
        
        print("🚀 Invoice Auditor Workflow initialized")
    
    def _build_graph(self):
        """Build main LangGraph workflow"""
        
        # Create graph
        workflow = StateGraph(InvoiceState)
        
        # Add nodes
        workflow.add_node("extraction", self._extraction_node)
        workflow.add_node("translation", self._translation_node)
        workflow.add_node("structured_extraction", self._structured_extraction_node)
        workflow.add_node("validation", self._validation_node)
        workflow.add_node("reporting", self._reporting_node)
        workflow.add_node("indexing", self._indexing_node)
        workflow.add_node("rag_subgraph", self._rag_subgraph_node)
        
        # Add edges (linear flow up to validation)
        workflow.add_edge(START, "extraction")
        workflow.add_edge("extraction", "translation")
        workflow.add_edge("translation", "structured_extraction")
        workflow.add_edge("structured_extraction", "validation")
        
        # Conditional edge after validation
        workflow.add_conditional_edges(
            "validation",
            self._should_continue_or_pause,
            {
                "continue": "reporting",    # Auto-approve/reject continues
                "pause": END                # Manual review pauses
            }
        )
        
        # Continue normal flow
        workflow.add_edge("reporting", "indexing")
        workflow.add_edge("indexing", "rag_subgraph")
        workflow.add_edge("rag_subgraph", END)
        
        # Compile
        return workflow.compile()
    
    def _extraction_node(self, state: InvoiceState) -> InvoiceState:
        """Node: Extract raw text from document"""
        print(f"\n📄 [Extraction Node] Processing: {Path(state['file_path']).name}")
        
        try:
            raw_text = self.extractor.extract_raw_text(state['file_path'])
            state['raw_text'] = raw_text
            state['status'] = 'extracted'
            print(f"   ✅ Extracted {len(raw_text)} characters")
        except Exception as e:
            state['error'] = f"Extraction failed: {e}"
            print(f"   ❌ Error: {e}")
        
        return state
    
    def _translation_node(self, state: InvoiceState) -> InvoiceState:
        """Node: Translate text to English"""
        print(f"🌐 [Translation Node] Processing...")
        
        try:
            translation_result = self.translator.translate_raw_text(state['raw_text'])
            
            state['translated_text'] = translation_result['translated_text']
            state['original_language'] = translation_result['original_language']
            state['translation_confidence'] = translation_result['translation_confidence']
            state['was_translated'] = translation_result['was_translated']
            state['status'] = 'translated'
            
            print(f"   ✅ Language: {state['original_language']}, Translated: {state['was_translated']}")
        except Exception as e:
            state['error'] = f"Translation failed: {e}"
            print(f"   ❌ Error: {e}")
        
        return state
    
    def _structured_extraction_node(self, state: InvoiceState) -> InvoiceState:
        """Node: Extract structured data using LLM"""
        print(f"📋 [Structured Extraction Node] Parsing invoice data...")
        
        try:
            invoice_data = self.extractor.extract_structured_data(state['translated_text'])
            
            # Add translation metadata
            invoice_data['original_language'] = state['original_language']
            invoice_data['translation_confidence'] = state['translation_confidence']
            invoice_data['was_translated'] = state['was_translated']
            
            state['invoice_data'] = invoice_data
            state['status'] = 'structured'
            
            print(f"   ✅ Invoice: {invoice_data.get('invoice_no')}, Items: {len(invoice_data.get('line_items', []))}")
        except Exception as e:
            state['error'] = f"Structured extraction failed: {e}"
            print(f"   ❌ Error: {e}")
        
        return state
    
    def _validation_node(self, state: InvoiceState) -> InvoiceState:
        """Node: Validate invoice"""
        print(f"✅ [Validation Node] Validating invoice...")
        
        try:
            validation_result = self.validator.validate(state['invoice_data'])
            state['validation_result'] = validation_result
            
            recommendation = validation_result['recommendation']
            
            # Check if needs human review
            if recommendation == 'manual_review':
                state['status'] = 'awaiting_human_review'
                print(f"   ⏸️  PAUSED for human review - Added to review queue")
                
                # Save to review queue
                self._add_to_review_queue(state)
                
                # Return early - workflow pauses here
                return state
            else:
                state['status'] = 'validated'
                print(f"   ✅ Recommendation: {recommendation.upper()}")
            
        except Exception as e:
            state['error'] = f"Validation failed: {e}"
            print(f"   ❌ Error: {e}")
        
        return state
    
    def _reporting_node(self, state: InvoiceState) -> InvoiceState:
        """Node: Generate audit report"""
        try:
            report_text = ""
            f_path = ""
            folder = Path("./outputs/reports")
            invoice_no = state['invoice_data'].get('invoice_no', 'UNKNOWN')
            print(f"Hi, {invoice_no}")
        
            if not folder.exists():
                print(f"Folder '{folder}' does not exist.")
            else:
                for file_path in folder.glob("*.json"):  # iterate over JSON files
                    # Debug print
                    print(f"Checking file: {file_path.name}")
                    
                    if file_path.name.startswith(f"RPT-{invoice_no}"):
                        print(f"You have already generated report for invoice {invoice_no} before.")
        
                        # Load JSON
                        with open(file_path, 'r') as f:
                            data = json.load(f)
        
                        # Extract 'report' value
                        report_text = data.get('report', "")
                        
                        # Store relative path
                        f_path = str("./outputs/reports/"+file_path.name)
                        
                        # Stop after first match
                        state['report_text'] = report_text
                        state['report_path'] = f_path
                        state['status'] = 'reported'
                        return state
        
        except Exception as e:
            print("There is some error at _reporting_node:", str(e))
        
        print(f"📊 [Reporting Node] Generating report...")
        
        try:
            report_result = self.reporter.generate_report(
                state['invoice_data'], 
                state['validation_result']
            )
            
            state['report_text'] = report_result['report_text']
            state['report_path'] = report_result['json_path']
            state['status'] = 'reported'
            
            # Print report
            print(f"\n{'=' * 60}")
            print(f"📊 AUDIT REPORT")
            print(f"{'=' * 60}")
            print(report_result['report_text'])
            print(f"{'=' * 60}\n")
            
        except Exception as e:
            state['error'] = f"Reporting failed: {e}"
            print(f"   ❌ Error: {e}")
        
        return state
    
    def _indexing_node(self, state: InvoiceState) -> InvoiceState:
        """Node: Index invoice for RAG"""
        print(f"📝 [Indexing Node] Indexing for RAG...")
        
        try:
            self.rag_pipeline.index_document(
                state['invoice_data'],
                state['validation_result'],
                state['report_text']
            )
            
            state['status'] = 'indexed'
            print(f"   ✅ Invoice indexed successfully")
            
        except Exception as e:
            state['error'] = f"Indexing failed: {e}"
            print(f"   ⚠️  Warning: {e}")
        
        return state
    
    def _rag_subgraph_node(self, state: InvoiceState) -> InvoiceState:
        """Node: RAG Subgraph - Query processed invoices"""
        print(f"🔍 [RAG Subgraph Node] Querying indexed invoices...")
        
        try:
            # Generate automatic query about this invoice
            invoice_no = state['invoice_data'].get('invoice_no', 'this invoice')
            auto_query = f"Summarize the validation results and key findings for invoice {invoice_no}"
            
            state['rag_query'] = auto_query
            print(f"   Query: {auto_query}")
            
            # Execute RAG subgraph (Retrieval -> Generation -> Reflection)
            rag_result = self.rag_pipeline.query(auto_query, evaluate=True)
            
            state['rag_answer'] = rag_result.get('answer', '')
            state['rag_sources'] = rag_result.get('sources', [])
            state['rag_evaluation'] = rag_result.get('evaluation', {})
            state['status'] = 'completed'
            
            print(f"   ✅ RAG Query completed")
            print(f"\n{'=' * 60}")
            print(f"🔍 RAG SUMMARY")
            print(f"{'=' * 60}")
            print(f"{state['rag_answer']}")
            print(f"{'=' * 60}\n")
            
        except Exception as e:
            state['error'] = f"RAG query failed: {e}"
            print(f"   ⚠️  Warning: {e}")
            state['status'] = 'completed'
        
        return state
    
    def process_invoice(self, file_path: str) -> dict:
        """Execute the complete workflow for an invoice"""
        print(f"\n{'=' * 60}")
        print(f"🚀 Starting Invoice Auditor Workflow")
        print(f"{'=' * 60}")
        
        # Initialize state
        initial_state = {
            'file_path': file_path,
            'raw_text': '',
            'translated_text': '',
            'original_language': '',
            'translation_confidence': 0.0,
            'was_translated': False,
            'invoice_data': {},
            'validation_result': {},
            'report_text': '',
            'report_path': '',
            'rag_query': '',
            'rag_answer': '',
            'rag_sources': [],
            'rag_evaluation': {},
            'status': 'started',
            'error': ''
        }
        
        # Run workflow
        final_state = self.graph.invoke(initial_state)
        
        # Print summary
        print(f"\n{'=' * 60}")
        print(f"✅ Workflow Complete")
        print(f"{'=' * 60}")
        print(f"Status: {final_state['status']}")
        print(f"Invoice: {final_state['invoice_data'].get('invoice_no', 'N/A')}")
        print(f"Recommendation: {final_state['validation_result'].get('recommendation', 'N/A').upper()}")
        print(f"Report: {final_state['report_path']}")
        
        if final_state.get('error'):
            print(f"⚠️  Errors: {final_state['error']}")
        
        print(f"{'=' * 60}\n")
        
        return final_state
    
    def get_graph(self):
        """Return compiled graph for visualization"""
        return self.graph
    
    def get_rag_pipeline(self):
        """Return RAG pipeline for querying"""
        return self.rag_pipeline
    
    def _should_continue_or_pause(self, state: InvoiceState) -> str:
        """Decide if workflow continues or pauses"""
        if state['status'] == 'awaiting_human_review':
            return "pause"
        return "continue"
    
    def _add_to_review_queue(self, state: InvoiceState):
        """Add invoice to review queue if not already present"""
        invoice_no = state['invoice_data'].get('invoice_no')
        queue_item = {
            'invoice_no': invoice_no,
            'file_path': state['file_path'],
            'state': state,
            'timestamp': datetime.now().isoformat()
        }
    
        # Load existing queue
        queue = []
        if self.review_queue_file.exists():
            with open(self.review_queue_file, 'r') as f:
                queue = json.load(f)
    
        # Check if invoice already in queue (based on invoice_no)
        if any(item.get('invoice_no') == invoice_no for item in queue):
            print(f"Data {invoice_no} already in queue for processing.")
            return  # Skip adding
    
        # Append and save
        queue.append(queue_item)
        with open(self.review_queue_file, 'w') as f:
            json.dump(queue, f, indent=2, default=str)
    
    def get_review_queue(self) -> list:
        """Get all invoices awaiting human review"""
        if self.review_queue_file.exists():
            with open(self.review_queue_file, 'r') as f:
                return json.load(f)
        return []
    
    def remove_from_review_queue(self, invoice_no: str):
        """Remove invoice from review queue after processing"""
        queue = self.get_review_queue()
        queue = [item for item in queue if item.get('invoice_no') != invoice_no]
        
        with open(self.review_queue_file, 'w') as f:
            json.dump(queue, f, indent=2, default=str)
    
    def resume_workflow(self, state: InvoiceState) -> dict:
        """Resume workflow from validation node after human review"""
        print(f"\n{'=' * 60}")
        print(f"▶️  Resuming Workflow for {state['invoice_data'].get('invoice_no')}")
        print(f"{'=' * 60}")
        
        # Update status
        state['status'] = 'validated'
        
        # Continue from reporting node
        state = self._reporting_node(state)
        state = self._indexing_node(state)
        state = self._rag_subgraph_node(state)
        
        # Mark as completed
        state['status'] = 'completed'
        
        print(f"\n{'=' * 60}")
        print(f"✅ Workflow Complete (Resumed)")
        print(f"{'=' * 60}")
        print(f"Status: {state['status']}")
        print(f"Invoice: {state['invoice_data'].get('invoice_no', 'N/A')}")
        print(f"Recommendation: {state['validation_result'].get('recommendation', 'N/A').upper()}")
        print(f"Report: {state['report_path']}")
        print(f"{'=' * 60}\n")
        
        return state
