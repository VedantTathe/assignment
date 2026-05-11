from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, JSON
from sqlalchemy.sql import func
from app.db.session import Base

class PromptRegistry(Base):
    __tablename__ = "prompt_registry"
    id = Column(Integer, primary_key=True)
    agent_name = Column(String, index=True)
    version = Column(Integer)
    prompt_text = Column(Text)
    is_active = Column(Boolean, default=False)
    avg_eval_score = Column(Float, nullable=True)

class PromptRewriteAudit(Base):
    __tablename__ = "prompt_rewrite_audit"
    id = Column(Integer, primary_key=True)
    agent_name = Column(String)
    old_prompt = Column(Text)
    proposed_prompt = Column(Text)
    justification = Column(Text)
    approved = Column(Boolean, default=False)
    performance_delta = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())

class EvalRun(Base):
    __tablename__ = "eval_runs"
    id = Column(Integer, primary_key=True)
    dataset_name = Column(String, index=True)
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    provider_metadata = Column(JSON, nullable=True)  # captures provider/model

class EvalCaseResult(Base):
    __tablename__ = "eval_case_results"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, index=True)
    case_id = Column(String, index=True)
    thread_id = Column(String, index=True)
    execution_trace_id = Column(Integer, nullable=True) # Direct link to ExecutionTrace
    input_query = Column(Text)
    final_response = Column(Text, nullable=True)
    success_status = Column(String)  # success, failed
    error_details = Column(Text, nullable=True)
    failure_types = Column(JSON, nullable=True) # Stores List[EvalFailureType]
    
    # Traceability
    prompt_version = Column(String, nullable=True)
    prompt_checksum = Column(String, nullable=True)
    adversarial = Column(Boolean, default=False)
    tags = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())

class EvalScore(Base):
    __tablename__ = "eval_scores"
    id = Column(Integer, primary_key=True)
    result_id = Column(Integer, index=True)
    dimension = Column(String, index=True)  # answer_correctness, tool_efficiency, etc
    score = Column(Float)
    justification = Column(Text)
    metadata_json = Column(JSON, nullable=True)

class ExecutionTrace(Base):
    __tablename__ = "execution_traces"
    id = Column(Integer, primary_key=True)
    thread_id = Column(String, index=True)
    correlation_id = Column(String, index=True)
    agent_name = Column(String, index=True)
    event_type = Column(String, index=True)
    token_count = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    timestamp = Column(DateTime, default=func.now())
    state_snapshot = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)

class ToolExecutionTrace(Base):
    __tablename__ = "tool_execution_traces"
    id = Column(Integer, primary_key=True)
    correlation_id = Column(String, index=True)
    thread_id = Column(String, index=True)
    tool_name = Column(String, index=True)
    input_payload = Column(JSON, nullable=True)
    output_payload = Column(JSON, nullable=True)
    status = Column(String)
    latency_ms = Column(Integer, default=0)
    timestamp = Column(DateTime, default=func.now())

class PolicyViolationTrace(Base):
    __tablename__ = "policy_violation_traces"
    id = Column(Integer, primary_key=True)
    correlation_id = Column(String, index=True)
    thread_id = Column(String, index=True)
    violation_type = Column(String, index=True)
    description = Column(Text)
    span = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=func.now())
