#!/usr/bin/env python3
"""
PR Reviewer using AI-Issue-Triage
"""
import logging
import os
import json
import subprocess
import tempfile
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class PRReviewer:
    """Review pull requests using AI-Issue-Triage"""

    def __init__(self, api_key: Optional[str] = None, ai_triage_path: Optional[str] = None):
        """Initialize the PR reviewer"""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            logger.warning("Gemini API key not provided")
        
        # Path to AI-Issue-Triage installation
        self.ai_triage_path = ai_triage_path or os.getenv("AI_TRIAGE_PATH", "/root/AI-Issue-Triage")
        
        if not os.path.exists(self.ai_triage_path):
            raise ValueError(f"AI-Issue-Triage not found at {self.ai_triage_path}")
        
        logger.info(f"Initialized PRReviewer with AI-Issue-Triage at {self.ai_triage_path}")

    def review_pr(self, title: str, body: str, file_changes: List[Dict], repo_url: Optional[str] = None) -> str:
        """
        Review a pull request using AI-Issue-Triage

        Args:
            title: PR title
            body: PR description
            file_changes: List of file change dictionaries
            repo_url: Repository URL for context

        Returns:
            Formatted review text (markdown)
        """
        if not self.api_key:
            logger.error("Gemini API key not available")
            return "❌ **Error**: Gemini API key not configured"

        try:
            # Create temporary file for PR data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as pr_file:
                pr_data = {
                    "title": title,
                    "body": body or "No description provided",
                    "repo_url": repo_url or "",
                    "file_changes": file_changes
                }
                json.dump(pr_data, pr_file, indent=2)
                pr_file_path = pr_file.name
            
            # Create temporary file for output
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as output_file:
                output_file_path = output_file.name
            
            try:
                # Run AI-Issue-Triage PR review CLI
                env = os.environ.copy()
                env['GEMINI_API_KEY'] = self.api_key
                
                cmd = [
                    'python3', '-m', 'cli.pr_review',
                    '--pr-file', pr_file_path,
                    '--output', output_file_path,
                    '--format', 'markdown'
                ]
                
                logger.info(f"Running AI-Issue-Triage PR review: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    cwd=self.ai_triage_path,
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=300
                )
                
                if result.returncode == 0 and os.path.exists(output_file_path):
                    with open(output_file_path, 'r') as f:
                        review_text = f.read()
                    
                    # Replace "AI Code Review" header with "Ansieyes PR Review"
                    review_text = review_text.replace(
                        "## 🤖 AI Code Review (Powered by Gemini)",
                        "## 🤖 Ansieyes Report"
                    )
                    
                    return review_text
                else:
                    logger.error(f"AI-Issue-Triage PR review failed: {result.stderr}")
                    return f"❌ **PR Review Failed**\n\n```\n{result.stderr}\n```"
            
            finally:
                # Cleanup temporary files
                if os.path.exists(pr_file_path):
                    os.unlink(pr_file_path)
                if os.path.exists(output_file_path):
                    os.unlink(output_file_path)

        except subprocess.TimeoutExpired:
            logger.error("PR review timed out")
            return "❌ **PR Review Failed**: Analysis timed out after 5 minutes"
        except Exception as e:
            logger.error(f"Error during PR review: {e}")
            return f"❌ **PR Review Failed**\n\n```\n{str(e)}\n```"

    def format_review_summary(self, review_text: str) -> str:
        """
        Format review (passthrough since AI-Issue-Triage already formats it)
        
        Args:
            review_text: Already formatted review text from AI-Issue-Triage
            
        Returns:
            Formatted review text
        """
        # AI-Issue-Triage already formats the output beautifully
        # Just return it as-is
        return review_text
