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
import sys
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
        
        # Try to load prompt injection detector from AI-Issue-Triage
        self.detect_prompt_injection_func = None
        self.InjectionRisk = None
        
        try:
            # Add AI-Issue-Triage to Python path for imports
            ai_triage_str = str(self.ai_triage_path)
            if ai_triage_str not in sys.path:
                sys.path.insert(0, ai_triage_str)
            
            # Import prompt injection detector from AI-Issue-Triage
            from utils.security.prompt_injection import detect_prompt_injection, InjectionRisk
            self.detect_prompt_injection_func = detect_prompt_injection
            self.InjectionRisk = InjectionRisk
            logger.info("✓ Loaded prompt injection detector from AI-Issue-Triage")
        except ImportError as e:
            logger.warning(f"Failed to import prompt injection detector: {e}")
            logger.warning("Prompt injection detection will be disabled")
        except Exception as e:
            logger.error(f"Unexpected error loading prompt injection detector: {e}")
            logger.warning("Prompt injection detection will be disabled")
        
        if not self.ai_triage_path.exists():
            raise ValueError(f"AI-Issue-Triage not found at {ai_triage_path}")
        
        if not self.api_key:
            logger.warning("Gemini API key not provided")

    def check_prompt_injection(self, text: str) -> Dict:
        """
        Check if text contains prompt injection attempts using AI-Issue-Triage's detector
        
        Args:
            text: Text to check for prompt injection
            
        Returns:
            Dictionary with:
            - is_injection: bool
            - risk_level: str (safe, low, medium, high, critical)
            - confidence: float (0-1)
            - detected_patterns: list of detected patterns
        """
        if not self.detect_prompt_injection_func:
            logger.debug("Prompt injection detection not available - skipping check")
            return {
                "is_injection": False,
                "risk_level": "safe",
                "confidence": 0.0,
                "detected_patterns": [],
                "disabled": True
            }
        
        try:
            # Use AI-Issue-Triage's comprehensive detection
            result = self.detect_prompt_injection_func(text, strict_mode=False)
            
            return {
                "is_injection": result.is_injection,
                "risk_level": result.risk_level.value,
                "confidence": result.confidence_score,
                "detected_patterns": result.detected_patterns[:5],  # Limit to top 5
                "method": "ai-issue-triage",
                "details": result.details
            }
        except Exception as e:
            logger.error(f"Prompt injection check failed: {e}", exc_info=True)
            # Return safe to not block analysis if detector fails
            return {
                "is_injection": False,
                "risk_level": "safe",
                "confidence": 0.0,
                "detected_patterns": [],
                "error": str(e)
            }

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
        repomix_file: str,
        config: Optional[Dict] = None,
        repo_path: Optional[str] = None
    ) -> Dict:
        """
        Pass 2: Surgeon - Deep analysis with targeted files
        
        Args:
            title: Issue title
            description: Issue description
            repomix_file: Path to repomix output file with targeted code
            config: Triage configuration from triage.config.json
            repo_path: Path to cloned repository (for custom prompt resolution)
            
        Returns:
            Dictionary with analysis results
        """
        if not self.api_key:
            return {"error": "API key not configured"}
        
        config = config or {}
        
        try:
            # Create output file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                output_file = f.name
            
            # Run Surgeon (analyzer) using AI-Issue-Triage CLI
            env = os.environ.copy()
            env['GEMINI_API_KEY'] = self.api_key
            
            # Build command with config options
            cmd = [
                'python3', '-m', 'cli.analyze',
                '--title', title,
                '--description', description,
                '--source-path', repomix_file,
                '--output', output_file,
                '--format', 'text',  # Get formatted text output
                '--retries', '2'
            ]
            
            # Add custom model if specified in config
            if config.get('gemini', {}).get('model'):
                model = config['gemini']['model']
                cmd.extend(['--model', model])
                logger.info(f"Using custom Gemini model from config: {model}")
            
            # Add custom prompt if specified in config
            if config.get('analysis', {}).get('custom_prompt_path') and repo_path:
                prompt_path = config['analysis']['custom_prompt_path']
                # Resolve path relative to repo root
                full_prompt_path = os.path.join(repo_path, prompt_path)
                if os.path.exists(full_prompt_path):
                    cmd.extend(['--custom-prompt', full_prompt_path])
                    logger.info(f"Using custom prompt from: {prompt_path}")
                else:
                    logger.warning(f"Custom prompt file not found: {full_prompt_path}")
            
            result = subprocess.run(
                cmd,
                cwd=self.ai_triage_path,
                capture_output=True,
                text=True,
                env=env
            )
            
            if result.returncode == 0 and os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    surgeon_result = f.read()  # Read as text, not JSON
                os.unlink(output_file)
                return {"formatted_output": surgeon_result}  # Return formatted text
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
        Generate repomix chunks for a repository, respecting .omit-triage
        
        Args:
            repo_path: Path to cloned repository
            
        Returns:
            Path to directory containing chunks
        """
        chunks_dir = os.path.join(repo_path, 'repomix-chunks')
        os.makedirs(chunks_dir, exist_ok=True)
        
        try:
            # Load .omit-triage to get excluded directories
            omit_triage_path = os.path.join(repo_path, '.omit-triage')
            excluded_dirs = set()
            if os.path.exists(omit_triage_path):
                with open(omit_triage_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Remove leading/trailing slashes
                            excluded_dirs.add(line.strip('/'))
                logger.info(f"Loaded .omit-triage exclusions: {excluded_dirs}")
            
            # Get root directories
            repo_path_obj = Path(repo_path)
            root_dirs = [d for d in repo_path_obj.iterdir() 
                        if d.is_dir() and not d.name.startswith('.')]
            
            # Generate chunk for each directory (excluding omitted ones)
            for dir_path in root_dirs:
                dir_name = dir_path.name
                
                # Skip if directory is in .omit-triage
                if dir_name in excluded_dirs:
                    logger.info(f"Skipping {dir_name} (excluded by .omit-triage)")
                    continue
                
                clean_name = dir_name.replace('/', '_')
                output_file = os.path.join(chunks_dir, f'{clean_name}.txt')
                
                # Try to find repomix (might be in npx, node_modules, or PATH)
                repomix_cmd = self._find_repomix()
                
                cmd = [
                    *repomix_cmd,
                    '--include', f'./{dir_name}/**',
                    '--style', 'plain',
                    '--compress',
                    '--remove-comments',
                    '--remove-empty-lines',
                    '--no-file-summary',
                    '--no-directory-structure',
                    '--output', output_file
                ]
                
                logger.debug(f"Running repomix for {dir_name}: {' '.join(cmd)}")
                result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=300)
                
                if result.returncode != 0:
                    logger.warning(f"Repomix failed for {dir_name}: {result.stderr}")
                elif os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    logger.info(f"Generated chunk for {dir_name}: {output_file}")
                else:
                    logger.warning(f"Repomix generated empty file for {dir_name}")
            
            return chunks_dir
            
        except Exception as e:
            logger.error(f"Error generating repomix chunks: {e}")
            return chunks_dir

    def _load_triage_config(self, repo_path: str) -> Dict:
        """
        Load triage.config.json from repository
        
        Args:
            repo_path: Path to cloned repository
            
        Returns:
            Dictionary with config, or empty dict if not found
        """
        config_path = os.path.join(repo_path, 'triage.config.json')
        if not os.path.exists(config_path):
            logger.info("No triage.config.json found, using defaults")
            return {}
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded triage.config.json: {config}")
            return config
        except Exception as e:
            logger.error(f"Failed to load triage.config.json: {e}")
            return {}

    def _find_repomix(self) -> List[str]:
        """
        Find repomix command (could be global, npx, or local node_modules)
        
        Returns:
            List containing the command to run repomix
        """
        import shutil
        
        # Check if repomix is in PATH
        if shutil.which('repomix'):
            return ['repomix']
        
        # Check if npx is available (can run from npm registry)
        if shutil.which('npx'):
            return ['npx', '-y', 'repomix']
        
        # Check common node_modules locations
        possible_paths = [
            '/usr/local/lib/node_modules/.bin/repomix',
            os.path.expanduser('~/.local/lib/node_modules/.bin/repomix'),
            '/home/ubuntu/.local/lib/node_modules/.bin/repomix',
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return [path]
        
        # Default to repomix and hope it's in PATH
        logger.warning("Could not find repomix, using default 'repomix' command")
        return ['repomix']

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
            - prompt_injection_check: Prompt injection detection results
            - duplicate_check: Duplicate detection results
            - librarian: File identification results
            - surgeon: Deep analysis results
        """
        result = {
            "prompt_injection_check": None,
            "duplicate_check": None,
            "librarian": None,
            "surgeon": None
        }
        
        # Step 0: Check for prompt injection attempts
        logger.info("Running prompt injection check...")
        combined_text = f"{title}\n\n{description}"
        injection_check = self.check_prompt_injection(combined_text)
        result["prompt_injection_check"] = injection_check
        
        # Block only if HIGH or CRITICAL risk detected
        risk_levels_to_block = ['high', 'critical']
        if injection_check.get("is_injection") and injection_check.get("risk_level") in risk_levels_to_block:
            logger.warning(f"High-risk prompt injection detected: {injection_check}")
            result["error"] = "High-risk prompt injection attempt detected"
            return result
        
        # Log but continue for MEDIUM/LOW risk
        if injection_check.get("is_injection"):
            logger.info(f"Low/medium risk patterns detected but continuing: {injection_check.get('risk_level')}")
        
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
            # Load triage configuration
            config = self._load_triage_config(repo_path)
            
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
                # Run Surgeon with config and repo_path
                logger.info("Running Surgeon (Pass 2: Deep Analysis)...")
                result["surgeon"] = self.run_surgeon(
                    title, description, targeted_repomix_path, config, repo_path
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
        Format triage results as a GitHub comment using AI-Issue-Triage style
        
        Args:
            triage_result: Results from triage_issue()
            
        Returns:
            Formatted markdown comment
        """
        from datetime import datetime
        
        # Prompt injection check - HIGH/CRITICAL blocks (formatted like AI-Issue-Triage)
        if triage_result.get("prompt_injection_check"):
            injection = triage_result["prompt_injection_check"]
            risk_level = injection.get("risk_level", "").lower()
            
            # Get emoji based on risk level
            risk_emoji_map = {
                "safe": "✅",
                "low": "🟢", 
                "medium": "🟡",
                "high": "🟠",
                "critical": "🔴"
            }
            risk_emoji = risk_emoji_map.get(risk_level, "⚠️")
            
            if injection.get("is_injection") and risk_level in ['high', 'critical']:
                comment = "# 🤖 Ansieyes Report\n\n"
                comment += f"## {risk_emoji} Security Alert: High-Risk Prompt Injection Detected\n\n"
                comment += "This issue contains patterns that are attempting to manipulate the AI analysis.\n\n"
                
                confidence_percent = int(injection.get("confidence", 0) * 100)
                comment += f"🔴 **Risk Level:** `{risk_level.upper()}`  \n"
                comment += f"📊 **Confidence:** `{confidence_percent}%`  \n"
                comment += f"⏰ **Generated:** `{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}`\n\n"
                comment += "---\n\n"
                
                if injection.get("detected_patterns"):
                    comment += "### 🚨 Flagged Patterns\n\n"
                    for i, pattern in enumerate(injection['detected_patterns'][:3], 1):
                        pattern_preview = pattern[:50] + '...' if len(pattern) > 50 else pattern
                        comment += f"{i}. `{pattern_preview}`\n"
                    comment += "\n"
                
                comment += "### 🚫 Action Taken\n\n"
                comment += "**Analysis has been halted for security reasons.**\n\n"
                comment += "If this is a false positive, please rephrase the issue and try again.\n\n"
                comment += "---\n"
                comment += "<sub>🔒 *Powered by Ansieyes Security (AI-Issue-Triage)*</sub>"
                return comment
        
        # Duplicate check (formatted like AI-Issue-Triage)
        if triage_result.get("duplicate_check"):
            dup = triage_result["duplicate_check"]
            if dup.get("is_duplicate"):
                comment = "# 🤖 Ansieyes Report\n\n"
                comment += "## 🔍 Duplicate Issue Detected\n\n"
                
                dup_of = dup.get('duplicate_of') or {}
                dup_issue_id = dup_of.get('issue_id', 'unknown') if dup_of else 'unknown'
                dup_title = dup_of.get('title', 'Unknown Title') if dup_of else 'Unknown Title'
                
                comment += f"This issue appears to be a duplicate of **#{dup_issue_id}**: *{dup_title}*\n\n"
                
                similarity_percent = int(dup.get('similarity_score', 0) * 100)
                confidence_percent = int(dup.get('confidence_score', 0) * 100)
                
                comment += f"📊 **Similarity Score:** `{similarity_percent}%`  \n"
                comment += f"🎯 **Confidence:** `{confidence_percent}%`  \n"
                comment += f"⏰ **Generated:** `{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}`\n\n"
                comment += "---\n\n"
                
                # Show why it's considered duplicate
                if dup.get('similarity_reasons'):
                    comment += "### 🔗 Similarity Reasons\n\n"
                    for i, reason in enumerate(dup['similarity_reasons'][:5], 1):
                        comment += f"{i}. {reason}\n"
                    comment += "\n"
                
                comment += "### 💡 Recommendation\n\n"
                comment += f"Please review issue #{dup_issue_id} and consider closing this as a duplicate if they address the same problem.\n\n"
                comment += "---\n"
                comment += "<sub>🤖 *Powered by Ansieyes (AI-Issue-Triage)*</sub>"
                return comment
        
        # Main report - Use AI-Issue-Triage's formatted output directly
        if not triage_result.get("surgeon"):
            return "## ⚠️ Analysis Incomplete\n\nNo analysis results available.\n\n---\n*Powered by Ansieyes*"
        
        surg = triage_result["surgeon"]
        
        if "error" in surg:
            return f"## ❌ Analysis Failed\n\n{surg['error']}\n\n---\n*Powered by Ansieyes*"
        
        # If we have formatted_output, use it directly (from AI-Issue-Triage)
        if "formatted_output" in surg:
            formatted = surg["formatted_output"]
            # Replace "Gemini Analysis Report" with "Ansieyes Report"
            formatted = formatted.replace("# 🤖 Gemini Analysis Report", "# 🤖 Ansieyes Report")
            formatted = formatted.replace("This analysis was generated by Gemini AI", "This analysis was generated by Ansieyes AI")
            return formatted
        
        # Fallback if no formatted output
        return "## ⚠️ Analysis Incomplete\n\nNo formatted output available.\n\n---\n*Powered by Ansieyes*"

