# common.py

# --- Imports ---
from typing_extensions import TypedDict, Literal
from typing import List, Dict, Any, Optional, Annotated
import os, re, requests, json, operator, feedparser
from urllib.parse import quote

from pydantic import BaseModel, Field, ValidationError
from IPython.display import Image, display

# LangChain / LangGraph imports
from langchain_core.tools import tool
from langchain_experimental.tools.python.tool import PythonAstREPLTool
from langchain_aws import ChatBedrockConverse, BedrockEmbeddings
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ValidationNode, create_react_agent, ToolNode
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt
from langchain_core.messages import (
    BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
)
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda, RunnableConfig

# --- Global LLM instance ---
llm = ChatBedrockConverse(
    model_id="amazon.nova-lite-v1:0",
    region_name="us-east-1",
    temperature=0.5,
    max_tokens=1000
)