#!/usr/bin/env python3
"""
PR Reviewer using Gemini API
"""
import logging
import os
import re
import yaml
from pprint import pp
from pathlib import Path
import google.generativeai as genai
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class PRReviewer:
    """Review pull requests using Gemini API"""

    def __init__(self, api_key: Optional[str] = None, config_path: Optional[str] = None):
        """Initialize the PR reviewer with Gemini API key"""
        if api_key:
            genai.configure(api_key=api_key)
            for model in genai.list_models():
                print(model)
            print(genai.list_models)
            self.model = genai.GenerativeModel("gemini-2.5-pro")
        else:
            self.model = None
            logger.warning("Gemini API key not provided")

        # Load prompt configuration
        self.prompt_config = self._load_prompt_config(config_path)
        logger.info(f"Loaded prompt configuration with repo types: {list(self.prompt_config.get('prompts', {}).keys())}")

    def _load_prompt_config(self, config_path: Optional[str] = None) -> Dict:
        """Load prompt configuration from YAML file"""
        if config_path is None:
            # Default to prompt_config.yml in the same directory as this file
            config_path = Path(__file__).parent / "prompt_config.yml"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            logger.warning(f"Prompt config file not found: {config_path}. Using default prompts.")
            return self._get_default_config()

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Successfully loaded prompt config from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading prompt config: {e}. Using default prompts.")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Return default configuration if YAML file is not available"""
        return {
            "repo_mappings": {},
            "prompts": {
                "default": {
                    "pr_review": {
                        "system_role": "You are an expert code reviewer. Review the following pull request and provide constructive feedback.",
                        "review_structure": """Please provide a comprehensive code review with the following structure:

1. **Overall Assessment**: Brief summary of the PR
2. **Strengths**: What was done well
3. **Issues Found**: List any bugs, security issues, performance problems, or code quality concerns
4. **Suggestions**: Recommendations for improvement
5. **File-specific Comments**: For each file with issues, provide:
   - File path
   - Line number (if applicable)
   - Specific comment
6. Every new function should contain a docstring explaining its purpose and parameters. Please point it out.

Format your response clearly with markdown. Be constructive and professional.""",
                        "workflow_analysis": """Please provide:
1. **Summary**: Brief overview of the workflow execution
2. **Success Analysis**: If successful, highlight what worked well
3. **Failure Analysis**: If failed, identify:
   - Root causes of failures
   - Common patterns in errors
   - Suggestions for fixing the issues
4. **Recommendations**: Actionable steps to improve the workflow or fix issues
5. **Best Practices**: Suggestions for workflow improvements

Be concise, actionable, and helpful. Format your response with clear markdown sections."""
                    }
                }
            }
        }

    def _get_repo_type(self, repo_url: str) -> str:
        """Determine repo type based on URL patterns"""
        if not repo_url:
            return "default"

        repo_mappings = self.prompt_config.get("repo_mappings", {})

        # Check each repo type's URL patterns
        for repo_type, patterns in repo_mappings.items():
            for pattern in patterns:
                try:
                    if re.search(pattern, repo_url, re.IGNORECASE):
                        logger.info(f"Matched repo URL '{repo_url}' to type '{repo_type}' using pattern '{pattern}'")
                        return repo_type
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{pattern}': {e}")

        logger.info(f"No match found for repo URL '{repo_url}', using default prompt")
        return "default"

    def _get_prompt(self, prompt_type: str, repo_type: str = "default") -> Dict:
        """Get prompt configuration for a specific type and repo"""
        prompts = self.prompt_config.get("prompts", {})

        # Try to get repo-specific prompt
        if repo_type in prompts:
            repo_prompts = prompts[repo_type]
            if prompt_type in repo_prompts:
                return repo_prompts[prompt_type]

        # Fallback to default
        default_prompts = prompts.get("default", {})
        if prompt_type in default_prompts:
            return default_prompts[prompt_type]

        # Ultimate fallback
        logger.warning(f"Prompt type '{prompt_type}' not found, using empty dict")
        return {}

    def _get_workflow_analysis_prompt(self, repo_type: str = "default") -> str:
        """Get workflow analysis prompt template for a specific repo type"""
        prompts = self.prompt_config.get("prompts", {})

        # Try to get repo-specific workflow analysis
        if repo_type in prompts:
            repo_prompts = prompts[repo_type]
            if "pr_review" in repo_prompts and "workflow_analysis" in repo_prompts["pr_review"]:
                return repo_prompts["pr_review"]["workflow_analysis"]

        # Fallback to default
        default_prompts = prompts.get("default", {})
        if "pr_review" in default_prompts and "workflow_analysis" in default_prompts["pr_review"]:
            return default_prompts["pr_review"]["workflow_analysis"]

        return ""

    def review_pr(self, title: str, body: str, file_changes: List[Dict], repo_url: Optional[str] = None) -> Dict:
        """
        Review a pull request and generate comments

        Args:
            title: PR title
            body: PR description
            file_changes: List of file change dictionaries

        Returns:
            Dictionary containing review summary and file comments
        """
        if not self.model:
            logger.error("Gemini model not initialized")
            return {}

        try:
            # Determine repo type and get appropriate prompt
            repo_type = self._get_repo_type(repo_url or "")
            # Prepare context for review
            review_prompt = self._build_review_prompt(title, body, file_changes, repo_type)

            # Generate review
            logger.info("Generating review with Gemini API...")
            response = self.model.generate_content(review_prompt)

            # Parse response
            review_text = response.text

            # Structure the review
            review_comments = self._parse_review(review_text, file_changes)

            return review_comments

        except Exception as e:
            logger.error(f"Error generating review: {e}")
            return {
                "summary": f"Error generating review: {str(e)}",
                "file_comments": [],
            }

    def _build_review_prompt(
        self, title: str, body: str, file_changes: List[Dict], repo_type: str = "default"
    ) -> str:
        """Build the prompt for Gemini API using repo-specific configuration"""
        # Get prompt configuration for this repo type
        prompt_config = self._get_prompt("pr_review", repo_type)
        system_role = prompt_config.get("system_role", "You are an expert code reviewer. Review the following pull request and provide constructive feedback.")
        review_structure = prompt_config.get("review_structure", "")

        # Build the prompt
        prompt = f"""{system_role}

Pull Request Title: {title}

Pull Request Description:
{body}

Changed Files:
"""

        for file_change in file_changes:
            filename = file_change.get("filename", "unknown")
            status = file_change.get("status", "unknown")
            additions = file_change.get("additions", 0)
            deletions = file_change.get("deletions", 0)
            patch = file_change.get("patch", "")

            prompt += f"\n--- File: {filename} ({status}) ---\n"
            prompt += f"Additions: +{additions}, Deletions: -{deletions}\n"

            if patch:
                # Limit patch size to avoid token limits
                patch_preview = patch[:5000] if len(patch) > 5000 else patch
                prompt += f"\nDiff:\n{patch_preview}\n"
                if len(patch) > 5000:
                    prompt += "\n[... diff truncated ...]\n"

        prompt += f"\n{review_structure}"

        return prompt

    def _parse_review(self, review_text: str, file_changes: List[Dict]) -> Dict:
        """Parse the review response into structured format"""
        # Extract file-specific comments
        file_comments = []

        # Try to extract file-specific comments from the review
        lines = review_text.split("\n")
        current_file = None
        current_line = None

        for i, line in enumerate(lines):
            # Look for file references
            if "File:" in line or "**" in line:
                # Try to extract filename
                for file_change in file_changes:
                    filename = file_change.get("filename", "")
                    if filename in line:
                        current_file = filename
                        break

            # Look for line numbers
            if "line" in line.lower() and any(char.isdigit() for char in line):
                try:
                    # Extract line number
                    words = line.split()
                    for word in words:
                        if word.isdigit():
                            current_line = int(word)
                            break
                except:
                    pass

        # Create structured review
        review_comments = {"summary": review_text, "file_comments": file_comments}

        # If we found file-specific references, add them
        if current_file:
            review_comments["file_comments"].append(
                {
                    "path": current_file,
                    "line": current_line,
                    "comment": review_text[:500],  # Truncate if too long
                }
            )

        return review_comments

    def format_review_summary(self, review_comments: Dict) -> str:
        """Format review comments for GitHub comment"""
        summary = review_comments.get("summary", "")

        # Add header
        formatted = "## 🤖 AI Code Review (Powered by Gemini)\n\n"
        formatted += summary

        # Add file-specific comments if any
        file_comments = review_comments.get("file_comments", [])
        if file_comments:
            formatted += "\n\n### File-specific Comments\n\n"
            for comment in file_comments:
                path = comment.get("path", "unknown")
                line = comment.get("line", "")
                comment_text = comment.get("comment", "")

                formatted += f"**`{path}`**"
                if line:
                    formatted += f" (line {line})"
                formatted += f":\n{comment_text}\n\n"

        formatted += "\n---\n*This review was generated automatically by the Gemini AI Code Review Bot.*"

        return formatted

    def analyze_workflow_run(
        self,
        workflow_name: str,
        conclusion: str,
        jobs: List[Dict],
        failed_jobs: List[str],
        workflow_url: str = "",
        repo_url: Optional[str] = None
    ) -> str:
        """
        Analyze a GitHub Actions workflow run and provide insights

        Args:
            workflow_name: Name of the workflow
            conclusion: Workflow conclusion (success, failure, cancelled, etc.)
            jobs: List of job information dictionaries
            failed_jobs: List of failed job names
            workflow_url: URL to the workflow run

        Returns:
            Analysis text string
        """
        if not self.model:
            logger.error("Gemini model not initialized")
            return self._format_basic_workflow_analysis(conclusion, failed_jobs)

        try:
            # Determine repo type and get appropriate prompt
            repo_type = self._get_repo_type(repo_url or "")
            # Build prompt for workflow analysis
            prompt = self._build_workflow_analysis_prompt(
                workflow_name, conclusion, jobs, failed_jobs, repo_type
            )

            # Generate analysis
            logger.info("Generating workflow analysis with Gemini API...")
            response = self.model.generate_content(prompt)
            analysis = response.text

            return analysis

        except Exception as e:
            logger.error(f"Error generating workflow analysis: {e}")
            return self._format_basic_workflow_analysis(conclusion, failed_jobs)

    def _build_workflow_analysis_prompt(
        self,
        workflow_name: str,
        conclusion: str,
        jobs: List[Dict],
        failed_jobs: List[str],
        repo_type: str = "default"
    ) -> str:
        """Build the prompt for workflow analysis using repo-specific configuration"""
        # Get workflow analysis template for this repo type
        workflow_analysis_template = self._get_workflow_analysis_prompt(repo_type)

        prompt = f"""You are analyzing a GitHub Actions workflow run. Provide insights about the workflow execution.

Workflow Name: {workflow_name}
Conclusion: {conclusion}

Jobs Executed:
"""

        for job in jobs:
            job_name = job.get("name", "Unknown")
            job_conclusion = job.get("conclusion", "unknown")
            job_status = job.get("status", "unknown")
            steps = job.get("steps", [])

            prompt += f"\n- **{job_name}**\n"
            prompt += f"  Status: {job_status}, Conclusion: {job_conclusion}\n"

            if steps:
                prompt += "  Steps:\n"
                for step in steps:
                    step_name = step.get("name", "Unknown")
                    step_conclusion = step.get("conclusion", "unknown")
                    step_status = step.get("status", "unknown")
                    status_icon = "✅" if step_conclusion == "success" else "❌" if step_conclusion == "failure" else "⏳"
                    prompt += f"    {status_icon} {step_name}: {step_status} ({step_conclusion})\n"

        if failed_jobs:
            prompt += f"\n**Failed Jobs:** {', '.join(failed_jobs)}\n"

        if workflow_analysis_template:
            prompt += f"\n{workflow_analysis_template}"
        else:
            # Fallback to default structure
            prompt += """
Please provide:
1. **Summary**: Brief overview of the workflow execution
2. **Success Analysis**: If successful, highlight what worked well
3. **Failure Analysis**: If failed, identify:
   - Root causes of failures
   - Common patterns in errors
   - Suggestions for fixing the issues
4. **Recommendations**: Actionable steps to improve the workflow or fix issues
5. **Best Practices**: Suggestions for workflow improvements

Be concise, actionable, and helpful. Format your response with clear markdown sections.
"""

        return prompt

    def _format_basic_workflow_analysis(
        self, conclusion: str, failed_jobs: List[str]
    ) -> str:
        """Fallback basic analysis when Gemini is not available"""
        if conclusion == "success":
            return "✅ **Workflow completed successfully!**\n\nAll jobs passed. Great work!"
        elif conclusion == "failure":
            analysis = "❌ **Workflow failed**\n\n"
            if failed_jobs:
                analysis += f"**Failed Jobs:** {', '.join(failed_jobs)}\n\n"
            analysis += "Please review the workflow logs to identify the issues."
            return analysis
        else:
            return f"⚠️ **Workflow {conclusion}**\n\nPlease check the workflow logs for details."
