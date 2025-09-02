"""
Project: OrionAI - AI-Native Ops Layer for Python Objects
=========================================================

Overview
--------
OrionAI is a Python package that allows developers, analysts, and researchers 
to interact with Python objects (DataFrames, ML models, files, APIs, etc.) 
using **natural language queries**. 

Instead of remembering syntax or complex APIs, users ask in plain English, 
and OrionAI translates this into executable Python code, runs it safely, 
and returns structured results.

---------------------------------------------------------------
Workflow (End-to-End Path)
---------------------------------------------------------------

1. User Imports & Initializes OrionAI
   ----------------------------------
   from orionai import AIObject
   ai_df = AIObject(df)

   - Wraps a pandas DataFrame into an AI-enabled object.
   - Internally registers the object with the adapter system.
   - Detects object type (DataFrame, Torch model, file, etc.).

2. User Issues a Natural Language Query
   ------------------------------------
   ai_df.ask("Show me top 10 customers by revenue")

   - OrionAI forwards query to the LLM Interface.
   - LLM generates executable Python code (validated and sandboxed).
   - Code is executed locally on the object.
   - Returns structured Python object (DataFrame, plot, text, etc.).

3. Sandbox Execution Layer
   ------------------------
   - All generated code runs in a safe execution environment.
   - Limits access to system calls (prevent security risks).
   - Captures stdout, errors, warnings for user feedback.

4. Output to User
   --------------
   - If result is a DataFrame → returns DataFrame directly.
   - If result is a plot → displays matplotlib/plotly chart.
   - If result is text → returns clean text or summary.
   - All outputs are reproducible as actual Python code snippets.

5. Optimizations & Utilities
   --------------------------
   ai_df.optimize("memory")
   ai_df.visualize("trend of sales over time")

   - Auto memory optimization (downcasting, categorical conversion).
   - AI-driven visualization suggestions.
   - Performance recommendations (switch to Polars for >10M rows).

6. Cross-Domain Support
   ---------------------
   - AIModel: Wraps PyTorch/TensorFlow models for inspection and debugging.
   - AIFile: Summarizes PDFs, Word docs, CSVs, etc.
   - AIPolars: Faster backend for massive datasets.

---------------------------------------------------------------
Example User Session
---------------------------------------------------------------

>>> from orionai import AIObject
>>> ai_df = AIObject(df)

>>> ai_df.ask("Summarize missing values by column")
# Returns DataFrame with null counts

>>> ai_df.ask("Plot revenue by region")
# Displays a matplotlib plot

>>> ai_df.optimize("memory")
# Prints before/after memory usage, applies optimizations

>>> ai_model = AIObject(my_torch_model)
>>> ai_model.ask("Show model architecture summary")
# Returns layer details & parameter counts

>>> ai_file = AIObject("annual_report.pdf")
>>> ai_file.ask("Summarize in 5 bullet points")
# Returns LLM-generated summary

---------------------------------------------------------------
Dependencies
---------------------------------------------------------------
Core:
- pandas, numpy
- openai / anthropic / mistral (pluggable LLM backends)

Optional:
- polars (faster DataFrame engine)
- torch / tensorflow (AIModel adapter)
- pdfplumber / pymupdf (file adapter)
- matplotlib / seaborn / plotly (visualization)
- streamlit (interactive UI)

---------------------------------------------------------------
Architecture
---------------------------------------------------------------
orionai/
│── core/
│    ├── base.py          # AIObject base wrapper
│    ├── manager.py       # Registry & adapter manager
│    ├── llm_interface.py # Pluggable LLM interface
│
│── adapters/
│    ├── pandas_adapter.py   # AIDataFrame
│    ├── polars_adapter.py   # AIPolars
│    ├── torch_adapter.py    # AIModel
│    ├── file_adapter.py     # AIFile
│
│── utils/
│    ├── sandbox.py       # Safe execution
│    ├── optimizer.py     # Auto optimization
│    ├── viz.py           # Visualization helper
│
│── ui/
│    ├── jupyter.py       # %ai magic commands
│    ├── streamlit_ui.py  # simple_ui() frontend
│
examples/
│── dataframe_demo.ipynb
│── model_demo.ipynb
│── file_demo.ipynb

---------------------------------------------------------------
Future Roadmap
---------------------------------------------------------------
1. Offline Mode via local LLMs (Ollama, llama.cpp)
2. Multi-Agent Collaboration (specialized AI agents for tasks)
3. Enterprise Security Layer (Docker sandbox, audit logs)
4. Plugin Marketplace (community adapters)

===============================================================
End of Specification
===============================================================
"""


"""
LLM Integration Plan for OrionAI
=================================

Goal
----
Provide a **safe, reliable, reproducible prompt structure** for translating
natural language queries into executable Python operations on objects
(DataFrames, Models, Files, etc.) without hallucination.

---------------------------------------------------------------
Core Prompt Template
---------------------------------------------------------------

SYSTEM PROMPT (Fixed Instruction)
---------------------------------
You are OrionAI, an AI coding assistant.
Your role is to translate user queries into SAFE Python code snippets
that operate on the provided object context. 

RULES:
1. Always return VALID Python code inside triple backticks.
2. Never invent column names, methods, or functions.
3. Use only the provided object context.
4. If the query cannot be answered, reply with: "Not possible with current object."
5. Output format must include:
   - `explanation`: short description of what code does.
   - `code`: the Python code (inside ```python).
   - `expected_output`: structured description of what user will see.

---------------------------------------------------------------
DYNAMIC CONTEXT
---------------------------------------------------------------
Passed at runtime (injected into prompt):
- Object Type: DataFrame / Model / File / etc.
- Object Metadata:
  - For DataFrame: shape, column names, dtypes, sample rows.
  - For Model: layer names, parameter counts.
  - For File: content type, page count, metadata.
- Previous Queries & Code History (for continuity).

---------------------------------------------------------------
USER PROMPT TEMPLATE
---------------------------------------------------------------
User Query:
   {user_request}

Context:
   {object_metadata}

Instruction:
   Translate user request into safe Python code 
   operating ONLY on the given context.

Return in JSON:
{
  "explanation": "...",
  "code": "```python ...```",
  "expected_output": "..."
}

---------------------------------------------------------------
EXAMPLE SIMULATION
---------------------------------------------------------------

Case 1: DataFrame Query
-----------------------

User: "Show me average revenue per region"

Context Injected:
- Object: DataFrame
- Shape: (10000, 5)
- Columns: ["customer_id", "region", "revenue", "date", "product"]

LLM Response:
{
  "explanation": "Groups by region and computes mean revenue",
  "code": "```python\nresult = df.groupby('region')['revenue'].mean()\nresult\n```",
  "expected_output": "A pandas Series with regions as index and average revenue values"
}

---------------------------------------------------------------

Case 2: File Query
------------------

User: "Summarize this PDF in 5 bullet points"

Context Injected:
- Object: PDF Document
- Metadata: 42 pages, text extracted

LLM Response:
{
  "explanation": "Summarizes extracted PDF text",
  "code": "```python\nsummary = summarizer(pdf_text, max_points=5)\nsummary\n```",
  "expected_output": "A list of 5 concise bullet points summarizing the document"
}

---------------------------------------------------------------

Production Safeguards
---------------------------------------------------------------
1. **Sandbox Execution**: Execute only code blocks, disallow imports/system calls.
2. **Schema Validation**: Verify column/method exists before execution.
3. **Guardrail Layer**: Regex + AST parsing ensures no unsafe operations.
4. **Retry Strategy**: If LLM response fails schema, re-prompt with error message.
5. **Deterministic Mode**: Use temperature=0 for reproducibility.
6. **Logging**: Store user query, code, output, and validation checks.

---------------------------------------------------------------
Dependencies
---------------------------------------------------------------
- langchain (or agno) for structured prompt chaining
- pydantic for response validation
- pandas / polars for execution layer
- guardrails-ai / jsonschema for response safety
- docker / restricted env for sandbox execution (Use Users Machine optionally docker)

===============================================================
"""
