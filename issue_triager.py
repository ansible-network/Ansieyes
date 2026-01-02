#!/usr/bin/env python3
"""
Issue Triager using AI-Issue-Triage package
Implements two-pass architecture: Librarian (file identification) + Surgeon (deep analysis)
"""
import logging
import os
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class IssueTriager:
    """Handle AI-powered issue triage using two-pass architecture"""

    def __init__(self, api_key: Optional[str] = None, ai_triage_path: str = "/Users/shvenkat/Documents/AI/AI-Issue-Triage"):
        """Initialize the issue triager
        
        Args:
            api_key: Gemini API key
            ai_triage_path: Path to AI-Issue-Triage repository
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.ai_triage_path = Path(ai_triage_path)
        
        if not self.ai_triage_path.exists():
            raise ValueError(f"AI-Issue-Triage not found at {ai_triage_path}")
        
        if not self.api_key:
            logger.warning("Gemini API key not provided")

    def check_for_duplicates(
        self,
        title: str,
        description: str,
        existing_issues: List[Dict]
    ) -> Dict:
        """
        Check if an issue is a duplicate of existing issues
        
        Args:
            title: Issue title
            description: Issue description
            existing_issues: List of existing issues to compare against
            
        Returns:
            Dictionary with duplicate check results
        """
        if not self.api_key:
            return {"is_duplicate": False, "error": "API key not configured"}
        
        try:
            # Create temporary file for existing issues
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(existing_issues, f)
                issues_file = f.name
            
            # Run duplicate check using AI-Issue-Triage CLI
            env = os.environ.copy()
            env['GEMINI_API_KEY'] = self.api_key
            
            cmd = [
                'python3', '-m', 'cli.duplicate_check',
                '--title', title,
                '--description', description,
                '--issues', issues_file,
                '--output', 'json'
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.ai_triage_path,
                capture_output=True,
                text=True,
                env=env
            )
            
            # Clean up temp file
            os.unlink(issues_file)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.error(f"Duplicate check failed: {result.stderr}")
                return {"is_duplicate": False, "error": result.stderr}
                
        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")
            return {"is_duplicate": False, "error": str(e)}

    def run_librarian(
        self,
        title: str,
        description: str,
        repo_path: str,
        chunks_dir: Optional[str] = None
    ) -> Dict:
        """
        Pass 1: Librarian - Identify relevant files from directory chunks
        
        Args:
            title: Issue title
            description: Issue description
            repo_path: Path to cloned repository
            chunks_dir: Path to directory containing repomix chunks
            
        Returns:
            Dictionary with identified files and analysis summary
        """
        if not self.api_key:
            return {"relevant_files": [], "error": "API key not configured"}
        
        try:
            # If chunks_dir not provided, generate it
            if not chunks_dir:
                chunks_dir = self._generate_repomix_chunks(repo_path)
            
            # Create output file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                output_file = f.name
            
            # Run Librarian using AI-Issue-Triage CLI
            env = os.environ.copy()
            env['GEMINI_API_KEY'] = self.api_key
            
            cmd = [
                'python3', '-m', 'cli.librarian',
                '--title', title,
                '--description', description,
                '--chunks-dir', chunks_dir,
                '--output', output_file,
                '--verbose'
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.ai_triage_path,
                capture_output=True,
                text=True,
                env=env
            )
            
            if result.returncode == 0 and os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    librarian_result = json.load(f)
                os.unlink(output_file)
                return librarian_result
            else:
                logger.error(f"Librarian failed: {result.stderr}")
                os.unlink(output_file)
                return {"relevant_files": [], "error": result.stderr}
                
        except Exception as e:
            logger.error(f"Error running Librarian: {e}")
            return {"relevant_files": [], "error": str(e)}

    def run_surgeon(
        self,
        title: str,
        description: str,
        repomix_file: str
    ) -> Dict:
        """
        Pass 2: Surgeon - Deep analysis with targeted files
        
        Args:
            title: Issue title
            description: Issue description
            repomix_file: Path to repomix output file with targeted code
            
        Returns:
            Dictionary with analysis results
        """
        if not self.api_key:
            return {"error": "API key not configured"}
        
        try:
            # Create output file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                output_file = f.name
            
            # Run Surgeon (analyzer) using AI-Issue-Triage CLI
            env = os.environ.copy()
            env['GEMINI_API_KEY'] = self.api_key
            
            cmd = [
                'python3', '-m', 'cli.analyze',
                '--title', title,
                '--description', description,
                '--source-path', repomix_file,
                '--output', output_file,
                '--format', 'json',
                '--retries', '2'
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.ai_triage_path,
                capture_output=True,
                text=True,
                env=env
            )
            
            if result.returncode == 0 and os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    surgeon_result = json.load(f)
                os.unlink(output_file)
                return surgeon_result
            else:
                logger.error(f"Surgeon failed: {result.stderr}")
                if os.path.exists(output_file):
                    os.unlink(output_file)
                return {"error": result.stderr}
                
        except Exception as e:
            logger.error(f"Error running Surgeon: {e}")
            return {"error": str(e)}

    def _generate_repomix_chunks(self, repo_path: str) -> str:
        """
        Generate repomix chunks for a repository
        
        Args:
            repo_path: Path to cloned repository
            
        Returns:
            Path to directory containing chunks
        """
        chunks_dir = os.path.join(repo_path, 'repomix-chunks')
        os.makedirs(chunks_dir, exist_ok=True)
        
        try:
            # Get root directories
            repo_path_obj = Path(repo_path)
            root_dirs = [d for d in repo_path_obj.iterdir() 
                        if d.is_dir() and not d.name.startswith('.')]
            
            # Generate chunk for each directory
            for dir_path in root_dirs:
                clean_name = dir_path.name.replace('/', '_')
                output_file = os.path.join(chunks_dir, f'{clean_name}.txt')
                
                cmd = [
                    'repomix',
                    '--include', f'./{dir_path.name}/**',
                    '--style', 'plain',
                    '--compress',
                    '--remove-comments',
                    '--remove-empty-lines',
                    '--no-file-summary',
                    '--no-directory-structure',
                    '--output', output_file
                ]
                
                subprocess.run(cmd, cwd=repo_path, capture_output=True)
            
            return chunks_dir
            
        except Exception as e:
            logger.error(f"Error generating repomix chunks: {e}")
            return chunks_dir

    def triage_issue(
        self,
        title: str,
        description: str,
        repo_url: str,
        existing_issues: Optional[List[Dict]] = None,
        repo_path: Optional[str] = None
    ) -> Dict:
        """
        Full two-pass triage of an issue
        
        Args:
            title: Issue title
            description: Issue description
            repo_url: Repository URL to clone
            existing_issues: List of existing issues for duplicate detection
            
        Returns:
            Dictionary with complete triage results including:
            - duplicate_check: Duplicate detection results
            - librarian: File identification results
            - surgeon: Deep analysis results
        """
        result = {
            "duplicate_check": None,
            "librarian": None,
            "surgeon": None
        }
        
        # Step 1: Check for duplicates if existing issues provided
        if existing_issues:
            logger.info("Running duplicate check...")
            result["duplicate_check"] = self.check_for_duplicates(
                title, description, existing_issues
            )
            
            if result["duplicate_check"].get("is_duplicate"):
                logger.info("Duplicate detected, skipping analysis")
                return result
        
        # Step 2: Clone repository and run Librarian
        # Note: Using outer temp_dir from app.py if repo_path provided
        cleanup_needed = False
        local_temp_dir = None
        
        if not repo_path:
            # Create our own temp directory if no repo_path provided
            local_temp_dir = tempfile.mkdtemp()
            repo_path = os.path.join(local_temp_dir, 'repo')
            cleanup_needed = True
            
            try:
                logger.info(f"Cloning repository: {repo_url}")
                subprocess.run(
                    ['git', 'clone', '--depth', '1', repo_url, repo_path],
                    capture_output=True,
                    check=True,
                    timeout=300  # 5 minute timeout
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Git clone failed: {e}")
                result["error"] = f"Failed to clone repository: {e}"
                if cleanup_needed and local_temp_dir:
                    import shutil
                    shutil.rmtree(local_temp_dir, ignore_errors=True)
                return result
            except subprocess.TimeoutExpired:
                logger.error("Git clone timeout")
                result["error"] = "Repository clone timeout"
                if cleanup_needed and local_temp_dir:
                    import shutil
                    shutil.rmtree(local_temp_dir, ignore_errors=True)
                return result
        else:
            logger.info(f"Using existing repo path: {repo_path}")
        
        try:
            # Run Librarian
            logger.info("Running Librarian (Pass 1: File Identification)...")
            result["librarian"] = self.run_librarian(title, description, repo_path)
            
            if not result["librarian"].get("relevant_files"):
                logger.warning("No relevant files identified")
                if cleanup_needed and local_temp_dir:
                    import shutil
                    shutil.rmtree(local_temp_dir, ignore_errors=True)
                return result
            
            # Step 3: Generate targeted repomix and run Surgeon
            logger.info("Generating targeted repomix...")
            
            # Create a temp file for targeted repomix (will be cleaned up)
            targeted_repomix_fd, targeted_repomix_path = tempfile.mkstemp(suffix='.txt')
            os.close(targeted_repomix_fd)  # Close file descriptor
            
            # Generate repomix with identified files
            file_list = result["librarian"]["relevant_files"]
            include_args = []
            for file in file_list:
                include_args.extend(['--include', file])
            
            cmd = ['repomix', '--remote', repo_url, '--style', 'plain', 
                   '--output', targeted_repomix_path] + include_args
            
            try:
                subprocess.run(cmd, capture_output=True, timeout=300, check=True)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                logger.warning(f"Targeted repomix failed: {e}, trying fallback")
                # Fallback: use full repo
                subprocess.run(['repomix', '--remote', repo_url, '--style', 'plain',
                              '--output', targeted_repomix_path], 
                             capture_output=True, timeout=300)
            
            if os.path.exists(targeted_repomix_path) and os.path.getsize(targeted_repomix_path) > 0:
                # Run Surgeon
                logger.info("Running Surgeon (Pass 2: Deep Analysis)...")
                result["surgeon"] = self.run_surgeon(
                    title, description, targeted_repomix_path
                )
            else:
                logger.error("Failed to generate targeted repomix")
                result["surgeon"] = {"error": "Failed to generate targeted repomix"}
            
            # CLEANUP: Remove targeted repomix file
            try:
                os.unlink(targeted_repomix_path)
                logger.debug(f"Cleaned up targeted repomix: {targeted_repomix_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up repomix file: {e}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git clone failed: {e}")
            result["error"] = f"Failed to clone repository: {e}"
        except Exception as e:
            logger.error(f"Triage failed: {e}")
            result["error"] = str(e)
        finally:
            # CLEANUP: Remove local temp directory if we created it
            if cleanup_needed and local_temp_dir:
                try:
                    import shutil
                    shutil.rmtree(local_temp_dir, ignore_errors=True)
                    logger.debug(f"Cleaned up temp directory: {local_temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp directory: {e}")
        
        return result

    def format_triage_comment(self, triage_result: Dict) -> str:
        """
        Format triage results as a GitHub comment
        
        Args:
            triage_result: Results from triage_issue()
            
        Returns:
            Formatted markdown comment
        """
        comment = "## 🤖 AI Two-Pass Issue Triage\n\n"
        
        # Duplicate check
        if triage_result.get("duplicate_check"):
            dup = triage_result["duplicate_check"]
            if dup.get("is_duplicate"):
                comment += "### 🔍 Duplicate Issue Detected\n\n"
                comment += f"This issue appears to be a duplicate of #{dup['duplicate_of']['issue_id']}\n\n"
                comment += f"**Similarity Score**: {dup.get('similarity_score', 0) * 100:.1f}%\n"
                comment += f"**Confidence**: {dup.get('confidence_score', 0) * 100:.1f}%\n\n"
                return comment
        
        # Librarian results
        if triage_result.get("librarian"):
            lib = triage_result["librarian"]
            files = lib.get("relevant_files", [])
            comment += f"### 📚 Pass 1: Librarian (File Identification)\n\n"
            comment += f"Identified **{len(files)}** relevant file(s) for deep analysis:\n\n"
            comment += "<details>\n<summary><b>View Identified Files</b></summary>\n\n"
            for i, file in enumerate(files, 1):
                comment += f"{i}. `{file}`\n"
            comment += "\n</details>\n\n---\n\n"
        
        # Surgeon results
        if triage_result.get("surgeon"):
            surg = triage_result["surgeon"]
            if "error" not in surg:
                comment += "### 🔬 Pass 2: Surgeon (Deep Analysis)\n\n"
                
                # Issue classification
                issue_type = surg.get("issue_type", "unknown")
                severity = surg.get("severity", "unknown")
                confidence = surg.get("confidence_score", 0) * 100
                
                comment += f"**Type**: `{issue_type.upper()}`  \n"
                comment += f"**Severity**: `{severity.upper()}`  \n"
                comment += f"**Confidence**: `{confidence:.0f}%`\n\n"
                
                # Summary
                if surg.get("analysis_summary"):
                    comment += "#### Summary\n\n"
                    comment += surg["analysis_summary"] + "\n\n"
                
                # Root cause
                if surg.get("root_cause_analysis"):
                    rca = surg["root_cause_analysis"]
                    comment += "#### Root Cause\n\n"
                    comment += f"> {rca.get('primary_cause', 'Not identified')}\n\n"
                
                # Proposed solutions
                if surg.get("proposed_solutions"):
                    comment += "#### Proposed Solutions\n\n"
                    for i, sol in enumerate(surg["proposed_solutions"], 1):
                        comment += f"{i}. {sol.get('description', 'No description')}\n"
                    comment += "\n"
        
        comment += "---\n\n"
        comment += "<sub>🤖 *This analysis used the Two-Pass Architecture: "
        comment += "Librarian identified relevant files, then Surgeon performed deep analysis.*</sub>"
        
        return comment

