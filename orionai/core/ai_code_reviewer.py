"""
AI-Powered Code Review Assistant for OrionAI
==========================================

A comprehensive AI-based code review system that uses Large Language Models
for intelligent code analysis, understanding, and recommendations.
"""

import ast
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import traceback


@dataclass
class AICodeIssue:
    """Represents a code issue found during AI review."""
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    category: str  # 'logic', 'security', 'performance', 'maintainability', 'design', 'best_practices'
    message: str
    line_number: int
    column: int
    code_snippet: str
    explanation: str
    suggestion: str
    fix_example: Optional[str] = None
    confidence: float = 0.9  # AI confidence in the issue
    impact: str = "medium"  # 'high', 'medium', 'low'
    learning_note: Optional[str] = None  # Educational explanation for students


@dataclass
class AICodeMetrics:
    """AI-analyzed code quality metrics."""
    readability_score: float  # 0-100
    maintainability_score: float  # 0-100
    complexity_assessment: str  # 'simple', 'moderate', 'complex', 'very_complex'
    design_quality: float  # 0-100
    documentation_quality: float  # 0-100
    test_coverage_assessment: str
    performance_assessment: str
    security_assessment: str
    overall_architecture_score: float  # 0-100


@dataclass
class AICodeReview:
    """Complete AI code review result."""
    file_path: str
    timestamp: datetime
    overall_score: float  # 0-100
    grade: str  # A+, A, B+, B, C+, C, D, F
    summary: str
    issues: List[AICodeIssue]
    metrics: AICodeMetrics
    strengths: List[str]
    improvements: List[str]
    learning_points: List[str]  # For educational purposes
    recommendations: List[str]
    code_style_analysis: str
    architecture_analysis: str
    best_practices_analysis: str
    review_time_seconds: float


class AICodeReviewer:
    """
    AI-Powered Code Review Assistant using Large Language Models.
    
    This class provides intelligent code analysis that goes beyond static analysis
    to understand code semantics, design patterns, business logic, and provides
    contextual recommendations.
    """
    
    def __init__(self, llm_provider=None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the AI Code Reviewer.
        
        Args:
            llm_provider: LLM provider instance for AI analysis
            config: Configuration settings
        """
        self.llm_provider = llm_provider
        self.config = self._load_default_config()
        if config:
            self.config.update(config)
        
        # Cache for performance
        self._analysis_cache = {}
        self._code_patterns_cache = {}
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration for AI review."""
        return {
            "analysis_depth": "comprehensive",  # 'quick', 'standard', 'comprehensive', 'deep'
            "focus_areas": ["security", "performance", "maintainability", "design", "best_practices"],
            "educational_mode": True,  # Provide learning explanations
            "industry_context": "general",  # 'web_dev', 'data_science', 'enterprise', 'startup'
            "review_style": "constructive",  # 'strict', 'constructive', 'mentoring'
            "include_fixes": True,
            "max_issues_per_category": 10,
            "confidence_threshold": 0.7,
            "severity_weights": {
                "critical": 1.0,
                "high": 0.8,
                "medium": 0.6,
                "low": 0.4,
                "info": 0.2
            }
        }
    
    def review_code(self, file_path: Union[str, Path], code_content: Optional[str] = None) -> AICodeReview:
        """
        Perform comprehensive AI-powered code review.
        
        Args:
            file_path: Path to the code file
            code_content: Optional code content (if not provided, reads from file)
            
        Returns:
            AICodeReview with comprehensive analysis
        """
        start_time = datetime.now()
        file_path = Path(file_path)
        
        # Read code content if not provided
        if code_content is None:
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
        
        # Check cache
        file_hash = hashlib.md5(code_content.encode()).hexdigest()
        cache_key = f"{file_path}_{file_hash}_{self.config['analysis_depth']}"
        
        if cache_key in self._analysis_cache:
            return self._analysis_cache[cache_key]
        
        try:
            # Perform AI-powered analysis
            analysis_result = self._perform_ai_analysis(str(file_path), code_content)
            
            # Parse and structure the results
            review = self._structure_review_results(str(file_path), code_content, analysis_result, start_time)
            
            # Cache the result
            self._analysis_cache[cache_key] = review
            
            return review
            
        except Exception as e:
            # Fallback analysis if AI fails
            print(f"⚠️ AI analysis failed, using fallback: {e}")
            return self._fallback_analysis(str(file_path), code_content, start_time)
    
    def _perform_ai_analysis(self, file_path: str, code_content: str) -> Dict[str, Any]:
        """
        Perform the core AI analysis using LLM.
        
        Args:
            file_path: Path to the file being analyzed
            code_content: The code content to analyze
            
        Returns:
            Dictionary containing AI analysis results
        """
        if not self.llm_provider:
            raise ValueError("LLM provider is required for AI code review")
        
        # Prepare the comprehensive analysis prompt
        analysis_prompt = self._create_analysis_prompt(file_path, code_content)
        
        try:
            # Get AI analysis
            ai_response = self.llm_provider.generate(analysis_prompt)
            
            # Parse the structured response
            return self._parse_ai_response(ai_response)
            
        except Exception as e:
            raise Exception(f"AI analysis failed: {e}")
    
    def _create_analysis_prompt(self, file_path: str, code_content: str) -> str:
        """Create comprehensive analysis prompt for the LLM."""
        
        # Get basic file info
        file_info = self._analyze_file_structure(code_content)
        
        prompt = f"""
You are an expert code reviewer with deep knowledge of software engineering, security, performance optimization, and best practices. Please perform a comprehensive review of this Python code.

**FILE INFORMATION:**
- File: {file_path}
- Lines of Code: {len(code_content.split('\n'))}
- Functions: {file_info['functions']}
- Classes: {file_info['classes']}
- Imports: {file_info['imports']}

**CODE TO REVIEW:**
```python
{code_content}
```

**ANALYSIS REQUIREMENTS:**
Please provide a comprehensive analysis in the following JSON format:

```json
{{
    "overall_assessment": {{
        "score": 85,
        "grade": "B+",
        "summary": "Well-structured code with minor improvements needed"
    }},
    "issues": [
        {{
            "severity": "high|medium|low|critical|info",
            "category": "security|performance|maintainability|design|best_practices|logic",
            "message": "Clear description of the issue",
            "line_number": 42,
            "column": 10,
            "code_snippet": "problematic code here",
            "explanation": "Detailed explanation of why this is an issue",
            "suggestion": "How to fix this issue",
            "fix_example": "corrected code example",
            "confidence": 0.9,
            "impact": "high|medium|low",
            "learning_note": "Educational explanation for students"
        }}
    ],
    "metrics": {{
        "readability_score": 85,
        "maintainability_score": 78,
        "complexity_assessment": "moderate",
        "design_quality": 82,
        "documentation_quality": 60,
        "test_coverage_assessment": "needs_improvement",
        "performance_assessment": "good",
        "security_assessment": "secure",
        "overall_architecture_score": 80
    }},
    "strengths": [
        "Clear function names and structure",
        "Good error handling",
        "Efficient algorithms used"
    ],
    "improvements": [
        "Add type hints for better code clarity",
        "Improve documentation coverage",
        "Consider breaking down large functions"
    ],
    "learning_points": [
        "This code demonstrates good use of list comprehensions",
        "The error handling pattern shown is a best practice",
        "Consider learning about design patterns for this use case"
    ],
    "recommendations": [
        "Add unit tests for critical functions",
        "Use logging instead of print statements",
        "Consider using dataclasses for data structures"
    ],
    "detailed_analysis": {{
        "code_style": "Analysis of coding style, conventions, and readability",
        "architecture": "Assessment of overall code structure and design",
        "best_practices": "Evaluation against Python best practices and conventions"
    }}
}}
```

**FOCUS AREAS:**
1. **Code Logic & Correctness**: Look for logical errors, edge cases, potential bugs
2. **Security**: Identify security vulnerabilities, injection risks, data exposure
3. **Performance**: Find bottlenecks, inefficient algorithms, resource usage issues
4. **Maintainability**: Assess code organization, readability, modularity
5. **Design Patterns**: Evaluate architecture, SOLID principles, design patterns
6. **Best Practices**: Python conventions, PEP standards, modern practices
7. **Error Handling**: Exception handling, edge cases, robustness
8. **Documentation**: Code comments, docstrings, clarity
9. **Testing**: Testability, test coverage, test design
10. **Dependencies**: Library usage, version compatibility, security

**REVIEW STYLE:**
- Be constructive and educational
- Provide specific, actionable feedback
- Include code examples for fixes
- Explain the "why" behind recommendations
- Consider both beginner and advanced perspectives
- Focus on practical improvements that add real value

**IMPORTANT:**
- Respond ONLY with valid JSON format
- Be thorough but focus on the most impactful issues
- Provide confidence scores based on certainty
- Include learning explanations for educational value
- Consider industry best practices and modern Python standards
"""
        
        return prompt
    
    def _analyze_file_structure(self, code_content: str) -> Dict[str, Any]:
        """Basic analysis of file structure."""
        try:
            tree = ast.parse(code_content)
            
            functions = []
            classes = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        imports.extend([alias.name for alias in node.names])
                    else:
                        imports.append(node.module or "unknown")
            
            return {
                "functions": len(functions),
                "classes": len(classes),
                "imports": len(set(imports)),
                "function_names": functions[:10],  # Limit for prompt size
                "class_names": classes[:10],
                "import_names": list(set(imports))[:15]
            }
        except Exception:
            return {
                "functions": 0,
                "classes": 0,
                "imports": 0,
                "function_names": [],
                "class_names": [],
                "import_names": []
            }
    
    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse the AI response into structured data."""
        try:
            # Extract JSON from the response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in AI response")
            
            json_str = ai_response[json_start:json_end]
            return json.loads(json_str)
            
        except json.JSONDecodeError as e:
            # Try to clean and parse again
            try:
                # Remove markdown formatting
                cleaned = re.sub(r'```json\s*', '', ai_response)
                cleaned = re.sub(r'```\s*$', '', cleaned)
                cleaned = cleaned.strip()
                
                return json.loads(cleaned)
            except:
                raise ValueError(f"Failed to parse AI response as JSON: {e}")
    
    def _structure_review_results(self, file_path: str, code_content: str, 
                                analysis_result: Dict[str, Any], start_time: datetime) -> AICodeReview:
        """Structure the AI analysis results into a CodeReview object."""
        
        # Extract overall assessment
        overall = analysis_result.get("overall_assessment", {})
        
        # Extract and structure issues
        issues = []
        for issue_data in analysis_result.get("issues", []):
            issue = AICodeIssue(
                severity=issue_data.get("severity", "medium"),
                category=issue_data.get("category", "general"),
                message=issue_data.get("message", "Issue detected"),
                line_number=issue_data.get("line_number", 1),
                column=issue_data.get("column", 0),
                code_snippet=issue_data.get("code_snippet", ""),
                explanation=issue_data.get("explanation", ""),
                suggestion=issue_data.get("suggestion", ""),
                fix_example=issue_data.get("fix_example"),
                confidence=float(issue_data.get("confidence", 0.8)),
                impact=issue_data.get("impact", "medium"),
                learning_note=issue_data.get("learning_note")
            )
            issues.append(issue)
        
        # Extract metrics
        metrics_data = analysis_result.get("metrics", {})
        metrics = AICodeMetrics(
            readability_score=float(metrics_data.get("readability_score", 70)),
            maintainability_score=float(metrics_data.get("maintainability_score", 70)),
            complexity_assessment=metrics_data.get("complexity_assessment", "moderate"),
            design_quality=float(metrics_data.get("design_quality", 70)),
            documentation_quality=float(metrics_data.get("documentation_quality", 50)),
            test_coverage_assessment=metrics_data.get("test_coverage_assessment", "unknown"),
            performance_assessment=metrics_data.get("performance_assessment", "acceptable"),
            security_assessment=metrics_data.get("security_assessment", "needs_review"),
            overall_architecture_score=float(metrics_data.get("overall_architecture_score", 70))
        )
        
        # Extract detailed analysis
        detailed = analysis_result.get("detailed_analysis", {})
        
        # Calculate review time
        review_time = (datetime.now() - start_time).total_seconds()
        
        return AICodeReview(
            file_path=file_path,
            timestamp=start_time,
            overall_score=float(overall.get("score", 70)),
            grade=overall.get("grade", "C"),
            summary=overall.get("summary", "Code analysis completed"),
            issues=issues,
            metrics=metrics,
            strengths=analysis_result.get("strengths", []),
            improvements=analysis_result.get("improvements", []),
            learning_points=analysis_result.get("learning_points", []),
            recommendations=analysis_result.get("recommendations", []),
            code_style_analysis=detailed.get("code_style", "Style analysis not available"),
            architecture_analysis=detailed.get("architecture", "Architecture analysis not available"),
            best_practices_analysis=detailed.get("best_practices", "Best practices analysis not available"),
            review_time_seconds=review_time
        )
    
    def _fallback_analysis(self, file_path: str, code_content: str, start_time: datetime) -> AICodeReview:
        """Provide basic fallback analysis when AI is not available."""
        
        # Basic static analysis
        lines = code_content.split('\n')
        loc = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
        
        # Simple heuristics
        issues = []
        
        # Check for obvious issues
        for i, line in enumerate(lines, 1):
            if len(line) > 100:
                issues.append(AICodeIssue(
                    severity="low",
                    category="style",
                    message="Line too long",
                    line_number=i,
                    column=100,
                    code_snippet=line[:50] + "...",
                    explanation="Long lines reduce readability",
                    suggestion="Break line into multiple lines"
                ))
            
            if 'print(' in line:
                issues.append(AICodeIssue(
                    severity="info",
                    category="best_practices",
                    message="Consider using logging instead of print",
                    line_number=i,
                    column=line.find('print('),
                    code_snippet=line.strip(),
                    explanation="Logging provides better control and formatting",
                    suggestion="Use logging.info(), logging.debug(), etc."
                ))
        
        # Basic metrics
        metrics = AICodeMetrics(
            readability_score=70.0,
            maintainability_score=70.0,
            complexity_assessment="moderate",
            design_quality=70.0,
            documentation_quality=50.0,
            test_coverage_assessment="unknown",
            performance_assessment="unknown",
            security_assessment="unknown",
            overall_architecture_score=70.0
        )
        
        review_time = (datetime.now() - start_time).total_seconds()
        
        return AICodeReview(
            file_path=file_path,
            timestamp=start_time,
            overall_score=70.0,
            grade="C",
            summary=f"Basic analysis completed. {len(issues)} issues found in {loc} lines of code.",
            issues=issues,
            metrics=metrics,
            strengths=["Code is syntactically correct"],
            improvements=["Enable AI analysis for comprehensive review"],
            learning_points=["AI-powered analysis provides deeper insights"],
            recommendations=["Set up LLM provider for enhanced analysis"],
            code_style_analysis="Basic style check completed",
            architecture_analysis="AI analysis required for architecture review",
            best_practices_analysis="AI analysis required for comprehensive best practices review",
            review_time_seconds=review_time
        )
    
    def generate_report(self, review: AICodeReview, format: str = "markdown") -> str:
        """Generate formatted report from review results."""
        
        if format == "markdown":
            return self._generate_markdown_report(review)
        elif format == "json":
            return json.dumps(asdict(review), indent=2, default=str)
        elif format == "html":
            return self._generate_html_report(review)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_markdown_report(self, review: AICodeReview) -> str:
        """Generate comprehensive markdown report."""
        
        report = f"""# 🤖 AI Code Review Report

## 📊 Overall Assessment
- **File**: `{review.file_path}`
- **Score**: {review.overall_score:.1f}/100 ({review.grade})
- **Review Time**: {review.review_time_seconds:.2f}s
- **Timestamp**: {review.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

## 📝 Summary
{review.summary}

## 📈 AI Metrics Analysis
- **Readability**: {review.metrics.readability_score:.1f}/100
- **Maintainability**: {review.metrics.maintainability_score:.1f}/100
- **Design Quality**: {review.metrics.design_quality:.1f}/100
- **Documentation**: {review.metrics.documentation_quality:.1f}/100
- **Architecture**: {review.metrics.overall_architecture_score:.1f}/100
- **Complexity**: {review.metrics.complexity_assessment.title()}
- **Performance**: {review.metrics.performance_assessment.title()}
- **Security**: {review.metrics.security_assessment.title()}
- **Test Coverage**: {review.metrics.test_coverage_assessment.title()}

## ✅ Code Strengths
"""
        
        for strength in review.strengths:
            report += f"- {strength}\n"
        
        report += "\n## 🔧 Areas for Improvement\n"
        for improvement in review.improvements:
            report += f"- {improvement}\n"
        
        if review.issues:
            report += f"\n## 🐛 Issues Found ({len(review.issues)} total)\n\n"
            
            # Group issues by severity
            issues_by_severity = {}
            for issue in review.issues:
                if issue.severity not in issues_by_severity:
                    issues_by_severity[issue.severity] = []
                issues_by_severity[issue.severity].append(issue)
            
            severity_order = ["critical", "high", "medium", "low", "info"]
            severity_icons = {
                "critical": "🚨",
                "high": "🔴", 
                "medium": "🟡",
                "low": "🟢",
                "info": "ℹ️"
            }
            
            for severity in severity_order:
                if severity in issues_by_severity:
                    issues = issues_by_severity[severity]
                    report += f"### {severity_icons[severity]} {severity.title()} Issues ({len(issues)})\n\n"
                    
                    for issue in issues:
                        report += f"#### Line {issue.line_number}: {issue.message}\n"
                        report += f"**Category**: {issue.category} | **Impact**: {issue.impact} | **Confidence**: {issue.confidence:.1f}\n\n"
                        
                        if issue.code_snippet:
                            report += f"**Code:**\n```python\n{issue.code_snippet}\n```\n\n"
                        
                        report += f"**Explanation**: {issue.explanation}\n\n"
                        report += f"**Suggestion**: {issue.suggestion}\n\n"
                        
                        if issue.fix_example:
                            report += f"**Fix Example:**\n```python\n{issue.fix_example}\n```\n\n"
                        
                        if issue.learning_note:
                            report += f"**💡 Learning Note**: {issue.learning_note}\n\n"
                        
                        report += "---\n\n"
        
        # Learning points
        if review.learning_points:
            report += "## 🎓 Learning Points\n"
            for point in review.learning_points:
                report += f"- {point}\n"
            report += "\n"
        
        # Recommendations
        if review.recommendations:
            report += "## 💡 Recommendations\n"
            for rec in review.recommendations:
                report += f"- {rec}\n"
            report += "\n"
        
        # Detailed Analysis
        report += "## 🔍 Detailed Analysis\n\n"
        report += f"### Code Style\n{review.code_style_analysis}\n\n"
        report += f"### Architecture\n{review.architecture_analysis}\n\n"
        report += f"### Best Practices\n{review.best_practices_analysis}\n\n"
        
        report += "---\n"
        report += "*Generated by OrionAI Code Review Assistant*"
        
        return report
    
    def _generate_html_report(self, review: AICodeReview) -> str:
        """Generate HTML report."""
        # Convert markdown to HTML (simplified)
        markdown_report = self._generate_markdown_report(review)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AI Code Review Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .score {{ font-size: 32px; font-weight: bold; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                   gap: 15px; margin: 20px 0; }}
        .metric-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
        .critical {{ color: #d32f2f; border-left: 4px solid #d32f2f; }}
        .high {{ color: #f57c00; border-left: 4px solid #f57c00; }}
        .medium {{ color: #fbc02d; border-left: 4px solid #fbc02d; }}
        .low {{ color: #388e3c; border-left: 4px solid #388e3c; }}
        .info {{ color: #1976d2; border-left: 4px solid #1976d2; }}
        .issue {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; }}
        code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 AI Code Review Report</h1>
        <div class="score">{review.overall_score:.1f}/100 ({review.grade})</div>
        <p>File: {review.file_path}</p>
    </div>
    
    <div class="metrics">
        <div class="metric-card">
            <h3>Readability</h3>
            <div style="font-size: 24px; font-weight: bold;">{review.metrics.readability_score:.0f}/100</div>
        </div>
        <div class="metric-card">
            <h3>Maintainability</h3>
            <div style="font-size: 24px; font-weight: bold;">{review.metrics.maintainability_score:.0f}/100</div>
        </div>
        <div class="metric-card">
            <h3>Design Quality</h3>
            <div style="font-size: 24px; font-weight: bold;">{review.metrics.design_quality:.0f}/100</div>
        </div>
        <div class="metric-card">
            <h3>Security</h3>
            <div style="font-size: 18px; font-weight: bold;">{review.metrics.security_assessment.title()}</div>
        </div>
    </div>
    
    <pre style="white-space: pre-wrap;">{markdown_report}</pre>
</body>
</html>
"""
        return html
    
    def review_directory(self, directory_path: Union[str, Path], 
                        recursive: bool = True,
                        file_patterns: List[str] = None) -> Dict[str, AICodeReview]:
        """Review all Python files in a directory."""
        
        directory_path = Path(directory_path)
        file_patterns = file_patterns or ["*.py"]
        
        results = {}
        
        # Find Python files
        for pattern in file_patterns:
            if recursive:
                files = directory_path.rglob(pattern)
            else:
                files = directory_path.glob(pattern)
            
            for file_path in files:
                # Skip common directories to ignore
                skip_dirs = {"__pycache__", ".git", "node_modules", "venv", ".env", "dist", "build"}
                if any(skip_dir in str(file_path) for skip_dir in skip_dirs):
                    continue
                
                try:
                    review = self.review_code(file_path)
                    results[str(file_path)] = review
                except Exception as e:
                    print(f"⚠️ Error reviewing {file_path}: {e}")
        
        return results


# Integration function for AIPython
def create_ai_code_review_method(llm_provider):
    """Create AI code review method for AIPython integration."""
    
    def ai_code_review(self, 
                      file_or_directory: str,
                      analysis_depth: str = "comprehensive",
                      output_format: str = "markdown",
                      educational_mode: bool = True,
                      save_report: bool = True) -> Any:
        """
        AI-powered code review with intelligent analysis and recommendations.
        
        Args:
            file_or_directory: Path to Python file or directory to review
            analysis_depth: 'quick', 'standard', 'comprehensive', 'deep'
            output_format: 'markdown', 'json', 'html'
            educational_mode: Include learning explanations
            save_report: Save report to file
            
        Returns:
            AI code review results with detailed analysis
        """
        from pathlib import Path
        
        # Initialize AI reviewer with LLM provider
        config = {
            "analysis_depth": analysis_depth,
            "educational_mode": educational_mode
        }
        
        reviewer = AICodeReviewer(llm_provider=llm_provider, config=config)
        path = Path(file_or_directory)
        
        if path.is_file():
            # Review single file
            if self.verbose:
                print(f"🤖 Starting AI code review for: {path.name}")
            
            review = reviewer.review_code(path)
            report = reviewer.generate_report(review, format=output_format)
            
            # Display results
            print(f"\n🎯 AI Code Review Complete!")
            print(f"📊 Overall Score: {review.overall_score:.1f}/100 ({review.grade})")
            print(f"🐛 Issues Found: {len(review.issues)}")
            print(f"✅ Strengths: {len(review.strengths)}")
            print(f"🔧 Improvements: {len(review.improvements)}")
            print(f"🎓 Learning Points: {len(review.learning_points)}")
            
            # Show top issues
            if review.issues:
                critical_high = [i for i in review.issues if i.severity in ['critical', 'high']]
                if critical_high:
                    print(f"\n🚨 Priority Issues:")
                    for issue in critical_high[:3]:
                        print(f"  • Line {issue.line_number}: {issue.message}")
            
            # Show strengths
            if review.strengths:
                print(f"\n✅ Code Strengths:")
                for strength in review.strengths[:3]:
                    print(f"  • {strength}")
            
            # Save report
            if save_report:
                report_path = path.parent / f"{path.stem}_ai_review.{output_format.split('_')[0]}"
                report_path.write_text(report, encoding='utf-8')
                print(f"📄 Report saved: {report_path}")
            
            return {
                "review": review,
                "report": report,
                "report_path": str(report_path) if save_report else None
            }
        
        elif path.is_dir():
            # Review directory
            if self.verbose:
                print(f"🤖 Starting AI code review for directory: {path.name}")
            
            reviews = reviewer.review_directory(path)
            
            if not reviews:
                print("⚠️ No Python files found to review")
                return {"reviews": {}, "summary": "No files found"}
            
            # Calculate summary statistics
            total_score = sum(r.overall_score for r in reviews.values()) / len(reviews)
            total_issues = sum(len(r.issues) for r in reviews.values())
            critical_issues = sum(len([i for i in r.issues if i.severity == 'critical']) for r in reviews.values())
            
            print(f"\n🎯 Directory AI Review Complete!")
            print(f"📁 Files Reviewed: {len(reviews)}")
            print(f"📊 Average Score: {total_score:.1f}/100")
            print(f"🐛 Total Issues: {total_issues}")
            if critical_issues > 0:
                print(f"🚨 Critical Issues: {critical_issues}")
            
            # Generate summary report
            summary_report = f"# AI Code Review Summary\n\n"
            summary_report += f"**Directory**: {path}\n"
            summary_report += f"**Files Reviewed**: {len(reviews)}\n"
            summary_report += f"**Average Score**: {total_score:.1f}/100\n"
            summary_report += f"**Total Issues**: {total_issues}\n"
            summary_report += f"**Critical Issues**: {critical_issues}\n\n"
            
            # Top issues across all files
            all_issues = []
            for review in reviews.values():
                all_issues.extend(review.issues)
            
            critical_high_issues = [i for i in all_issues if i.severity in ['critical', 'high']]
            if critical_high_issues:
                summary_report += "## 🚨 Priority Issues Across All Files\n\n"
                for issue in sorted(critical_high_issues, key=lambda x: x.confidence, reverse=True)[:10]:
                    file_name = Path(issue.code_snippet).name if hasattr(issue, 'file_path') else "Unknown"
                    summary_report += f"- **{issue.severity.title()}**: {issue.message} (Line {issue.line_number})\n"
            
            summary_report += "\n## 📁 File-by-File Summary\n\n"
            for file_path, review in reviews.items():
                file_name = Path(file_path).name
                summary_report += f"### {file_name}\n"
                summary_report += f"- Score: {review.overall_score:.1f}/100 ({review.grade})\n"
                summary_report += f"- Issues: {len(review.issues)}\n"
                summary_report += f"- Top Strength: {review.strengths[0] if review.strengths else 'N/A'}\n\n"
            
            # Save reports
            if save_report:
                # Save individual reports
                report_dir = path / "ai_code_reviews"
                report_dir.mkdir(exist_ok=True)
                
                for file_path, review in reviews.items():
                    report = reviewer.generate_report(review, format=output_format)
                    file_name = Path(file_path).stem
                    report_path = report_dir / f"{file_name}_ai_review.{output_format.split('_')[0]}"
                    report_path.write_text(report, encoding='utf-8')
                
                # Save summary
                summary_path = report_dir / f"summary.{output_format.split('_')[0]}"
                summary_path.write_text(summary_report, encoding='utf-8')
                print(f"📄 Reports saved to: {report_dir}")
            
            return {
                "reviews": reviews,
                "summary": summary_report,
                "average_score": total_score,
                "total_issues": total_issues,
                "critical_issues": critical_issues
            }
        
        else:
            raise ValueError(f"Path does not exist: {path}")
    
    return ai_code_review
