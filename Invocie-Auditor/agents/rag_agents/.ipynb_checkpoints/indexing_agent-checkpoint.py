"""
Indexing Agent - Simple FAISS indexing with Bedrock embeddings
"""
import json
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import BedrockEmbeddings
from langchain.docstore.document import Document

class IndexingAgent:
    def __init__(self):
        # Initialize Bedrock embeddings
        self.embeddings = BedrockEmbeddings(
            model_id="cohere.embed-english-v3",
            region_name="us-east-1"
        )
        
        self.vector_store_path = Path("./data/faiss_index")
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing index or create new
        index_file = self.vector_store_path / "index.faiss"
        if index_file.exists():
            self.vector_store = FAISS.load_local(
                str(self.vector_store_path), 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            print(f"Loaded existing FAISS index")
        else:
            self.vector_store = None
            print(f"New FAISS index will be created")
        
        # Text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=100
        )
    
    def index_invoice(self, invoice_data: dict, validation_result: dict, report_text: str):
        """
        Index invoice data into FAISS
        """
        invoice_no = invoice_data.get('invoice_no', 'UNKNOWN')
        
        # Check if invoice already indexed
        if self._is_invoice_indexed(invoice_no):
            print(f"Invoice {invoice_no} already indexed. Skipping to avoid duplicates.")
            return
        
        print(f"Indexing Invoice {invoice_no}...")
        
        # Combine all data into text
        full_text = self._create_document_text(invoice_data, validation_result, report_text)
        
        # Split into chunks
        chunks = self.text_splitter.split_text(full_text)
        
        # Create Document objects with metadata
        documents = [
            Document(
                page_content=chunk,
                metadata={
                    'invoice_no': invoice_no,
                    'po_number': invoice_data.get('po_number'),
                    'vendor': invoice_data.get('vendor_name'),
                    'recommendation': validation_result.get('recommendation'),
                    'chunk_type': 'detail'
                }
            )
            for chunk in chunks
        ]
        
        # Add a special summary document for "list all invoices" queries
        summary_doc = Document(
            page_content=f"""Invoice {invoice_no} has been processed and indexed. 
            Invoice Number: {invoice_no}
            PO Number: {invoice_data.get('po_number')}
            Vendor: {invoice_data.get('vendor_name')}
            Total: {invoice_data.get('currency')} {invoice_data.get('total_amount')}
            Status: {validation_result.get('recommendation')}
            This invoice is available in the system.
            """,
            metadata={
                'invoice_no': invoice_no,
                'po_number': invoice_data.get('po_number'),
                'vendor': invoice_data.get('vendor_name'),
                'recommendation': validation_result.get('recommendation'),
                'chunk_type': 'summary'
            }
        )
        documents.append(summary_doc)
        
        # Add to FAISS
        if self.vector_store is None:
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
        else:
            self.vector_store.add_documents(documents)
        
        # Save index
        self.vector_store.save_local(str(self.vector_store_path))
        
        print(f"Indexed {len(documents)} chunks from Invoice {invoice_no}")
    
    def _is_invoice_indexed(self, invoice_no: str) -> bool:
        """Check if invoice is already indexed"""
        if self.vector_store is None:
            return False
        
        try:
            # Check if any document has this invoice_no in metadata
            all_docs = self.vector_store.docstore._dict
            for doc_id, doc in all_docs.items():
                if doc.metadata.get('invoice_no') == invoice_no:
                    return True
            return False
        except:
            return False
    
    def _create_document_text(self, invoice_data: dict, validation_result: dict, report_text: str) -> str:
        """Combine all invoice information into one text"""
        
        # Invoice summary
        text = f"""
        INVOICE INFORMATION
        Invoice Number: {invoice_data.get('invoice_no')}
        PO Number: {invoice_data.get('po_number')}
        Vendor: {invoice_data.get('vendor_name')}
        Date: {invoice_data.get('invoice_date')}
        Currency: {invoice_data.get('currency')}
        Total Amount: {invoice_data.get('total_amount')}
        Language: {invoice_data.get('original_language')}
        Was Translated: {invoice_data.get('was_translated')}
        
        LINE ITEMS:
        """
        
        # Add line items
        for item in invoice_data.get('line_items', []):
            text += f"""
            - {item.get('item_code')}: {item.get('description')}
              Quantity: {item.get('qty')}, Unit Price: {item.get('unit_price')}, Total: {item.get('total')}
            """
        
        # Validation results
        text += f"""
        VALIDATION RESULTS
        Recommendation: {validation_result.get('recommendation')}
        Data Validation: {'PASS' if validation_result.get('data_validation_passed') else 'FAIL'}
        Business Validation: {'PASS' if validation_result.get('business_validation_passed') else 'FAIL'}
        ERP Status: {validation_result.get('erp_match_status')}
        Discrepancies: {len(validation_result.get('discrepancies', []))}
        """
        
        # Add discrepancies
        if validation_result.get('discrepancies'):
            text += "\nDISCREPANCY DETAILS:\n"
            for disc in validation_result.get('discrepancies', []):
                text += f"- [{disc.get('severity')}] {disc.get('message')}\n"
        
        # Add audit report
        text += f"""
        AUDIT REPORT
        {report_text}
        """
        return text
    
    def get_retriever(self):
        """Get FAISS retriever"""
        if self.vector_store is None:
            return None
        retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})
        return retriever
