"""
RAG Subgraph - LangGraph implementation of RAG pipeline
"""
from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, START, END
from .retrieval_agent import RetrievalAgent
from .generation_agent import GenerationAgent
from .reflection_agent import ReflectionAgent

# Define the state schema
class RAGState(TypedDict):
    """State for RAG workflow"""
    query: str
    retrieved_docs: List
    answer: str
    sources: List[str]
    evaluation: dict
    error: str

class RAGGraph:
    """LangGraph-based RAG workflow"""
    
    def __init__(self, retriever):
        self.retrieval_agent = RetrievalAgent(retriever)
        self.generation_agent = GenerationAgent()
        self.reflection_agent = ReflectionAgent()
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Build LangGraph workflow"""
        
        # Create graph
        workflow = StateGraph(RAGState)
        
        # Add nodes
        workflow.add_node("retrieval", self._retrieval_node)
        workflow.add_node("generation", self._generation_node)
        workflow.add_node("reflection", self._reflection_node)
        
        # Add edges
        workflow.add_edge(START, "retrieval")
        workflow.add_edge("retrieval", "generation")
        workflow.add_edge("generation", "reflection")
        workflow.add_edge("reflection", END)
        
        # Compile
        return workflow.compile()
    
    def _retrieval_node(self, state: RAGState) -> RAGState:
        """Node: Retrieve relevant documents"""
        print(f"[Retrieval Node] Processing query...")
        
        query = state.get("query", "")
        docs = self.retrieval_agent.retrieve(query)
        
        state["retrieved_docs"] = docs
        
        if not docs:
            state["error"] = "No relevant documents found"
        
        return state
    
    def _generation_node(self, state: RAGState) -> RAGState:
        """Node: Generate answer"""
        print(f"[Generation Node] Generating answer...")
        
        query = state.get("query", "")
        docs = state.get("retrieved_docs", [])
        
        if not docs:
            state["answer"] = "No relevant information found."
            state["sources"] = []
            return state
        
        answer = self.generation_agent.generate(query, docs)
        
        # Extract sources
        sources = list(set([
            doc.metadata.get('invoice_no') for doc in docs if doc.metadata.get('invoice_no')
        ]))
        
        state["answer"] = answer
        state["sources"] = sources
        
        return state
    
    def _reflection_node(self, state: RAGState) -> RAGState:
        """Node: Evaluate answer quality"""
        print(f"🔬 [Reflection Node] Evaluating quality...")
        
        query = state.get("query", "")
        answer = state.get("answer", "")
        docs = state.get("retrieved_docs", [])
        
        evaluation = self.reflection_agent.evaluate(query, answer, docs)
        
        state["evaluation"] = evaluation
        
        return state
    
    def invoke(self, query: str) -> dict:
        """Execute RAG workflow"""
        print(f"\n{'=' * 60}")
        print(f"RAG Subgraph Execution")
        print(f"{'=' * 60}")
        
        # Initialize state
        initial_state = {
            "query": query,
            "retrieved_docs": [],
            "answer": "",
            "sources": [],
            "evaluation": {},
            "error": ""
        }
        
        # Run graph
        final_state = self.graph.invoke(initial_state)
        
        return {
            "query": final_state.get("query"),
            "answer": final_state.get("answer"),
            "sources": final_state.get("sources", []),
            "evaluation": final_state.get("evaluation"),
            "error": final_state.get("error", "")
        }
    
    def get_graph(self):
        """Return compiled graph for integration"""
        return self.graph
