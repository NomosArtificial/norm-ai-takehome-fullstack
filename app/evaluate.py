"""Evaluation module for the QA system."""
from pathlib import Path
from typing import Any, Dict, List, Tuple
from pydantic import BaseModel
import json
from tqdm import tqdm

from llama_index.core.evaluation import CorrectnessEvaluator
from llama_index.llms.openai import OpenAI

from app.utils import Output, QdrantService, DocumentService


class EvaluationResult(BaseModel):
    """Result of a single evaluation."""
    name: str
    score: float
    explanation: str | None = None


class LLMMatchEvaluator:
    """Evaluator that uses LLM to assess response correctness."""
    
    def __init__(self, model: str = "gpt-4") -> None:
        self.llm = OpenAI(model)
        self.evaluator = CorrectnessEvaluator(llm=self.llm)

    def evaluate(self, response: Output, expected_output: Dict[str, Any]) -> EvaluationResult:
        """Evaluate response against expected output using LLM."""
        reference = expected_output["values"]
        result = self.evaluator.evaluate(
            query=response.query,
            response=response.response,
            reference=reference,
        )
        return EvaluationResult(
            name="response-correctness",
            score=result.score,
            explanation=result.feedback
        )


class PartialListMatchEvaluator:
    """Evaluator that compares citation sources using set operations."""
    
    def evaluate(self, response: Output, expected_output: Dict[str, Any]) -> EvaluationResult:
        """Evaluate citation sources using Jaccard similarity."""
        if expected_output["field"] != "citations-source":
            raise ValueError("Only support partial list match for citations sources currently.")
            
        actual_sources = [citation.source for citation in response.citations]
        expected_sources = expected_output["values"]
        intersection = set(actual_sources) & set(expected_sources)
        union = set(actual_sources) | set(expected_sources)
        score = len(intersection) / len(union) if union else 0.0
        
        return EvaluationResult(
            name="citations-source-match",
            score=score,
            explanation=f"intersection: {intersection}, union: {union}"
        )


# Initialize evaluators
EVALUATOR_MAP = {
    "llm-match": LLMMatchEvaluator(model="gpt-4"),
    "partial-list-match": PartialListMatchEvaluator(),
}


def evaluate(dataset: str | Path, target: Any) -> Tuple[List[Dict[str, EvaluationResult]], Dict[str, float]]:
    """
    Evaluate model responses against a dataset of expected outputs.
    
    Args:
        dataset: Path to the dataset file
        target: QA system to evaluate
    
    Returns:
        Tuple of (instance metrics, aggregated metrics)
    """
    # Load the dataset
    with open(dataset, "r") as f:
        dataset = [json.loads(line) for line in f]

    # For each instance, predict and evaluate
    instance_results = []
    for instance in tqdm(dataset, desc="Evaluating queries"):
        instance_metrics: Dict[str, EvaluationResult] = {}
        query_str = instance["query"]
        response = target.query(query_str)
        
        for expected_output in instance["expected_outputs"]:
            evaluator = EVALUATOR_MAP.get(expected_output["type"])
            if evaluator is None:
                raise ValueError(f"Evaluator {expected_output['type']} not found")
            
            result = evaluator.evaluate(response, expected_output)
            instance_metrics[result.name] = result
        
        instance_results.append(instance_metrics)

    # Aggregate results
    aggregated_results: Dict[str, List[float]] = {}
    for result in instance_results:
        for key, value in result.items():
            if key not in aggregated_results:
                aggregated_results[key] = []
            aggregated_results[key].append(value.score)
    
    aggregated_metrics = {
        k: sum(v) / len(v) for k, v in aggregated_results.items()
    }

    return instance_results, aggregated_metrics


def main() -> None:
    """Run the evaluation pipeline."""
    print("Parsing documents...")
    pdf_path = Path(__file__).parent.parent / "docs" / "laws.pdf"
    doc_service = DocumentService(pdf_path)
    docs = doc_service.create_documents()

    print("Indexing documents...")
    index = QdrantService()
    index.connect()
    index.load(docs)

    print("Evaluating...")
    instance_metrics, aggregated_metrics = evaluate("eval_data/dataset.jsonl", index)
    
    print(f"Aggregated metrics: {aggregated_metrics}")
    print("Instance metrics:")
    for result in instance_metrics:
        scores = {k: v.score for k, v in result.items()}
        print(scores)


if __name__ == "__main__":
    main()
