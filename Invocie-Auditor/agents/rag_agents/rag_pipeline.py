"""
RAG Pipeline - LangGraph-based orchestration
"""
from .indexing_agent import IndexingAgent
from .rag_graph import RAGGraph

class RAGPipeline:
    def __init__(self):
        self.indexing_agent = IndexingAgent()
        self.rag_graph = None
        
        # Initialize graph if retriever available
        retriever = self.indexing_agent.get_retriever()
        if retriever:
            self.rag_graph = RAGGraph(retriever)
            print("RAG Pipeline initialized with LangGraph")
        else:
            print("RAG Pipeline initialized (no documents yet)")
    
    def index_document(self, invoice_data: dict, validation_result: dict, report_text: str):
        """Index invoice for querying"""
        self.indexing_agent.index_invoice(invoice_data, validation_result, report_text)
        
        # Reinitialize graph with updated retriever
        retriever = self.indexing_agent.get_retriever()
        if retriever:
            self.rag_graph = RAGGraph(retriever)
    
    def query(self, question: str, evaluate: bool = True) -> dict:
        """
        Query using LangGraph RAG subgraph
        """
        if self.rag_graph is None:
            return {
                'query': question,
                'answer': 'No indexed documents found. Please process some invoices first.',
                'sources': [],
                'evaluation': None
            }
        
        # Execute graph
        result = self.rag_graph.invoke(question)
        
        return result
    
    def get_stats(self) -> dict:
        """Get statistics about indexed documents"""
        if self.indexing_agent.vector_store is None:
            return {
                'total_documents': 0,
                'total_chunks': 0,
                'invoices': []
            }
        
        # Count unique invoices from metadata
        try:
            # Get all documents from vector store
            all_docs = self.indexing_agent.vector_store.docstore._dict
            unique_invoices = set()
            invoice_details = {}
            
            for doc_id, doc in all_docs.items():
                invoice_no = doc.metadata.get('invoice_no')
                if invoice_no:
                    unique_invoices.add(invoice_no)
                    if invoice_no not in invoice_details:
                        invoice_details[invoice_no] = {
                            'invoice_no': invoice_no,
                            'vendor': doc.metadata.get('vendor'),
                            'po_number': doc.metadata.get('po_number'),
                            'recommendation': doc.metadata.get('recommendation')
                        }
            
            return {
                'total_documents': len(unique_invoices),
                'total_chunks': len(all_docs),
                'invoices': list(invoice_details.values())
            }
        except:
            # Fallback if unable to access docstore
            return {
                'total_documents': 'Unknown',
                'total_chunks': 'Unknown',
                'invoices': []
            }
    
    def get_graph(self):
        """Get compiled LangGraph for visualization or integration"""
        if self.rag_graph:
            return self.rag_graph.get_graph()
        return None

