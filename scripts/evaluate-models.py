#!/usr/bin/env python3
"""
😐 Model Evaluation: 0.5b vs 1.5b
Testing local models for tightly scoped development tasks
"""

import json
import time
from pathlib import Path
from typing import Dict, Any
import psutil
import os

from llama_cpp import Llama

# Test prompt: Representative development task
TEST_PROMPT = """Implement a Python function `validate_layer_count(layers: int, min_layers: int = 3, max_layers: int = 7) -> bool` that:
1. Returns True if layers is between min_layers and max_layers (inclusive)
2. Raises ValueError with a message if layers is invalid
3. Has a Google-style docstring with Harold persona comments (use 😐 emoji)
4. Includes type hints

Generate only the function code."""

MODELS = {
    "0.5b": {
        "file": "qwen2.5-coder-0.5b-instruct-q4_k_m.gguf",
        "size_mb": 469,
        "n_ctx": 4096,  # Smaller context for smaller model
    },
    "1.5b": {
        "file": "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
        "size_mb": 1100,
        "n_ctx": 8192,  # Larger context for larger model
    },
}


def get_process_memory_mb() -> float:
    """Get current process memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def evaluate_model(model_name: str, model_config: Dict[str, Any], models_dir: Path, results_dir: Path) -> Dict:
    """Evaluate a single model on the test task"""
    
    print(f"\n😐 Evaluating {model_name} model...")
    print(f"  Model file: {model_config['file']}")
    print(f"  Size: {model_config['size_mb']}MB")
    
    model_path = models_dir / model_config['file']
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    # Measure baseline memory
    baseline_memory = get_process_memory_mb()
    
    # Load model
    print("  📦 Loading model...")
    load_start = time.time()
    
    llm = Llama(
        model_path=str(model_path),
        n_ctx=model_config['n_ctx'],
        n_threads=8,  # Use all cores
        verbose=False,
    )
    
    load_time = time.time() - load_start
    model_loaded_memory = get_process_memory_mb()
    model_memory_mb = model_loaded_memory - baseline_memory
    
    print(f"  ✓ Model loaded in {load_time:.2f}s ({model_memory_mb:.0f}MB)")
    
    # Generate response using chat format
    print("  🤖 Generating code...")
    gen_start = time.time()
    
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": "You are a Python code generator for the EraserHead project. Use Harold persona (😐 emoji for comments). Generate clean, well-documented code."},
            {"role": "user", "content": TEST_PROMPT},
        ],
        max_tokens=512,
        temperature=0.1,
    )
    
    gen_time = time.time() - gen_start
    peak_memory = get_process_memory_mb()
    
    # Extract response from chat completion
    generated_text = response['choices'][0]['message']['content']
    prompt_tokens = response['usage']['prompt_tokens']
    completion_tokens = response['usage']['completion_tokens']
    tokens_per_sec = completion_tokens / gen_time if gen_time > 0 else 0
    
    print(f"  ✓ Generated {completion_tokens} tokens in {gen_time:.2f}s ({tokens_per_sec:.1f} t/s)")
    
    # Save generated code
    output_file = results_dir / f"{model_name}-generated.py"
    output_file.write_text(generated_text)
    
    # Quality checks
    quality = {
        "has_docstring": '"""' in generated_text or "'''" in generated_text,
        "has_type_hints": "-> bool" in generated_text or ": int" in generated_text,
        "has_harold_emoji": "😐" in generated_text or "🌑" in generated_text,
        "has_raises": "raise" in generated_text.lower() and "valueerror" in generated_text.lower(),
        "has_function_def": "def validate_layer_count" in generated_text,
        "code_length": len(generated_text.strip()),
    }
    quality["score"] = sum([
        quality["has_docstring"],
        quality["has_type_hints"],
        quality["has_harold_emoji"],
        quality["has_raises"],
        quality["has_function_def"],
    ])
    
    print(f"  📊 Quality score: {quality['score']}/5")
    
    # Compile results
    results = {
        "model_name": model_name,
        "model_file": model_config['file'],
        "model_size_mb": model_config['size_mb'],
        "performance": {
            "load_time_seconds": round(load_time, 2),
            "generation_time_seconds": round(gen_time, 2),
            "total_time_seconds": round(load_time + gen_time, 2),
            "model_memory_mb": round(model_memory_mb, 0),
            "peak_memory_mb": round(peak_memory, 0),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "tokens_per_second": round(tokens_per_sec, 1),
        },
        "quality": quality,
        "generated_code": generated_text,
    }
    
    # Save results JSON
    results_file = results_dir / f"{model_name}-evaluation.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    del llm  # Free memory
    
    return results


def compare_results(results_05b: Dict, results_15b: Dict, results_dir: Path):
    """Generate comparison report"""
    
    print("\n😐 Generating comparison report...")
    
    with open(results_dir / "comparison.md", 'w') as f:
        f.write("# 😐 Local Model Evaluation: 0.5b vs 1.5b\n\n")
        f.write("**Date**: February 10, 2026\n")
        f.write("**System**: Ubuntu 25.04, 8 cores, 14GB RAM\n")
        f.write("**Task**: Implement `validate_layer_count()` with Harold persona\n\n")
        
        f.write("## Performance Comparison\n\n")
        f.write("| Metric | 0.5b | 1.5b | Winner |\n")
        f.write("|--------|------|------|--------|\n")
        
        perf_05b = results_05b['performance']
        perf_15b = results_15b['performance']
        
        # Load time
        winner = "0.5b" if perf_05b['load_time_seconds'] < perf_15b['load_time_seconds'] else "1.5b"
        f.write(f"| Load Time | {perf_05b['load_time_seconds']}s | {perf_15b['load_time_seconds']}s | ✅ {winner} |\n")
        
        # Generation time
        winner = "0.5b" if perf_05b['generation_time_seconds'] < perf_15b['generation_time_seconds'] else "1.5b"
        f.write(f"| Generation Time | {perf_05b['generation_time_seconds']}s | {perf_15b['generation_time_seconds']}s | ✅ {winner} |\n")
        
        # Total time
        winner = "0.5b" if perf_05b['total_time_seconds'] < perf_15b['total_time_seconds'] else "1.5b"
        f.write(f"| **Total Time** | **{perf_05b['total_time_seconds']}s** | **{perf_15b['total_time_seconds']}s** | ✅ **{winner}** |\n")
        
        # Memory
        winner = "0.5b" if perf_05b['peak_memory_mb'] < perf_15b['peak_memory_mb'] else "1.5b"
        f.write(f"| Peak Memory | {perf_05b['peak_memory_mb']:.0f}MB | {perf_15b['peak_memory_mb']:.0f}MB | ✅ {winner} |\n")
        
        # Tokens/sec
        winner = "1.5b" if perf_15b['tokens_per_second'] > perf_05b['tokens_per_second'] else "0.5b"
        f.write(f"| Tokens/Second | {perf_05b['tokens_per_second']} | {perf_15b['tokens_per_second']} | ✅ {winner} |\n")
        
        # Quality
        qual_05b = results_05b['quality']
        qual_15b = results_15b['quality']
        winner = "1.5b" if qual_15b['score'] > qual_05b['score'] else "0.5b"
        f.write(f"| **Quality Score** | **{qual_05b['score']}/5** | **{qual_15b['score']}/5** | ✅ **{winner}** |\n\n")
        
        f.write("## Quality Breakdown\n\n")
        f.write("| Feature | 0.5b | 1.5b |\n")
        f.write("|---------|------|------|\n")
        f.write(f"| Function Definition | {'✅' if qual_05b['has_function_def'] else '❌'} | {'✅' if qual_15b['has_function_def'] else '❌'} |\n")
        f.write(f"| Docstring | {'✅' if qual_05b['has_docstring'] else '❌'} | {'✅' if qual_15b['has_docstring'] else '❌'} |\n")
        f.write(f"| Type Hints | {'✅' if qual_05b['has_type_hints'] else '❌'} | {'✅' if qual_15b['has_type_hints'] else '❌'} |\n")
        f.write(f"| Harold Emoji | {'✅' if qual_05b['has_harold_emoji'] else '❌'} | {'✅' if qual_15b['has_harold_emoji'] else '❌'} |\n")
        f.write(f"| Raises ValueError | {'✅' if qual_05b['has_raises'] else '❌'} | {'✅' if qual_15b['has_raises'] else '❌'} |\n")
        f.write(f"| Code Length | {qual_05b['code_length']} chars | {qual_15b['code_length']} chars |\n\n")
        
        f.write("## Generated Code\n\n")
        f.write("### 0.5b Model Output\n\n")
        f.write("```python\n")
        f.write(results_05b['generated_code'])
        f.write("\n```\n\n")
        
        f.write("### 1.5b Model Output\n\n")
        f.write("```python\n")
        f.write(results_15b['generated_code'])
        f.write("\n```\n\n")
        
        f.write("## Recommendation\n\n")
        
        # Calculate scores
        speed_score_05b = (1 / perf_05b['total_time_seconds']) * 100
        speed_score_15b = (1 / perf_15b['total_time_seconds']) * 100
        
        memory_score_05b = (1000 / perf_05b['peak_memory_mb']) * 100
        memory_score_15b = (1000 / perf_15b['peak_memory_mb']) * 100
        
        quality_score_05b = (qual_05b['score'] / 5) * 100
        quality_score_15b = (qual_15b['score'] / 5) * 100
        
        # Weights: Quality > Speed > Memory
        total_05b = (quality_score_05b * 0.5) + (speed_score_05b * 0.3) + (memory_score_05b * 0.2)
        total_15b = (quality_score_15b * 0.5) + (speed_score_15b * 0.3) + (memory_score_15b * 0.2)
        
        if total_15b > total_05b:
            f.write("**Winner: 1.5b model** 🏆\n\n")
            f.write(f"Despite being {perf_15b['total_time_seconds'] / perf_05b['total_time_seconds']:.1f}x slower, ")
            f.write("the 1.5b model produces significantly higher quality code ")
            f.write(f"({qual_15b['score']}/5 vs {qual_05b['score']}/5). ")
            f.write("For tightly scoped development tasks where code quality matters, ")
            f.write("the extra time is worth it.\n\n")
            recommended = "1.5b"
        else:
            f.write("**Winner: 0.5b model** 🏆\n\n")
            f.write(f"The 0.5b model is {perf_05b['total_time_seconds'] / perf_15b['total_time_seconds']:.1f}x faster ")
            f.write(f"with {(1 - perf_05b['peak_memory_mb'] / perf_15b['peak_memory_mb']) * 100:.0f}% less memory usage. ")
            f.write("For rapid iteration and simple tasks, it provides excellent value.\n\n")
            recommended = "0.5b"
        
        f.write("### Harold's Take 😐\n\n")
        if recommended == "1.5b":
            f.write("*\"The 1.5b model takes longer, but at least it won't embarrass you in code review. ")
            f.write("Dark Harold notes that faster bugs are still bugs.\"*\n\n")
        else:
            f.write("*\"The 0.5b model is fast enough that you might actually use it. ")
            f.write("Dark Harold reminds you that no model prevents production failures.\"*\n\n")
        
        # Save recommendation
        with open(results_dir / "recommended.txt", 'w') as rec_file:
            rec_file.write(f"{recommended}\n")


def main():
    # Setup paths
    project_root = Path(__file__).parent.parent
    models_dir = project_root / "models" / "llama-cpp"
    results_dir = project_root / "model-evaluation-results"
    results_dir.mkdir(exist_ok=True)
    
    print("😐 Model Evaluation: 0.5b vs 1.5b for Development")
    print("=" * 60)
    print(f"Models directory: {models_dir}")
    print(f"Results directory: {results_dir}")
    print(f"System: {psutil.cpu_count()} cores, {psutil.virtual_memory().total / (1024**3):.1f}GB RAM")
    
    # Evaluate both models
    results_05b = evaluate_model("0.5b", MODELS["0.5b"], models_dir, results_dir)
    results_15b = evaluate_model("1.5b", MODELS["1.5b"], models_dir, results_dir)
    
    # Generate comparison
    compare_results(results_05b, results_15b, results_dir)
    
    print("\n✅ Evaluation complete!")
    print(f"\nResults saved to: {results_dir}/")
    print(f"View comparison: cat {results_dir}/comparison.md")
    
    # Print quick summary
    recommended = (results_dir / "recommended.txt").read_text().strip()
    print(f"\n🏆 Recommended model: {recommended}")


if __name__ == "__main__":
    main()
