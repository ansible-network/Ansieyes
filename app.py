#!/usr/bin/env python3
"""
GitHub Bot for PR Reviews using Gemini API
"""
import os
import hmac
import hashlib
import base64
import logging
import subprocess
import tempfile
import shutil
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from github import Github
from github.GithubException import GithubException
import google.generativeai as genai
from pr_reviewer import PRReviewer
from issue_triager import IssueTriager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GITHUB_APP_ID = os.getenv('GITHUB_APP_ID')
GITHUB_PRIVATE_KEY_PATH = os.getenv('GITHUB_PRIVATE_KEY_PATH')
GITHUB_WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET')
AI_TRIAGE_PATH = os.getenv('AI_TRIAGE_PATH', '/Users/shvenkat/Documents/AI/AI-Issue-Triage')
PORT = int(os.getenv('PORT', 3000))
HOST = os.getenv('HOST', '0.0.0.0')

# Initialize Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not set. Gemini API will not work.")

# Initialize PR Reviewer
pr_reviewer = PRReviewer(GEMINI_API_KEY)

# Initialize Issue Triager
issue_triager = IssueTriager(GEMINI_API_KEY, AI_TRIAGE_PATH)


def verify_webhook_signature(payload_body, signature_header):
    """Verify GitHub webhook signature"""
    if not GITHUB_WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET not set. Skipping signature verification.")
        return True

    if not signature_header:
        return False

    hash_object = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()

    return hmac.compare_digest(expected_signature, signature_header)


def get_github_client(installation_id):
    """Get authenticated GitHub client for an installation"""
    # Try to get private key from environment variable (base64 encoded) first
    private_key = None
    private_key_b64 = os.getenv('GITHUB_PRIVATE_KEY_B64')

    if private_key_b64:
        try:
            private_key = base64.b64decode(private_key_b64).decode('utf-8')
            logger.info("Using private key from GITHUB_PRIVATE_KEY_B64 environment variable")
        except Exception as e:
            logger.warning(f"Failed to decode GITHUB_PRIVATE_KEY_B64: {e}")

    # Fallback to file path
    if not private_key and GITHUB_PRIVATE_KEY_PATH:
        if os.path.exists(GITHUB_PRIVATE_KEY_PATH):
            try:
                with open(GITHUB_PRIVATE_KEY_PATH, 'r') as key_file:
                    private_key = key_file.read()
                logger.info(f"Using private key from file: {GITHUB_PRIVATE_KEY_PATH}")
            except Exception as e:
                logger.error(f"Error reading private key file: {e}")
        else:
            logger.error(f"Private key file not found: {GITHUB_PRIVATE_KEY_PATH}")

    if not private_key:
        logger.error("No private key available. Set GITHUB_PRIVATE_KEY_B64 or GITHUB_PRIVATE_KEY_PATH")
        return None

    try:
        from github import GithubIntegration

        integration = GithubIntegration(GITHUB_APP_ID, private_key)
        access_token = integration.get_access_token(installation_id).token

        return Github(access_token)
    except Exception as e:
        logger.error(f"Error creating GitHub client: {e}")
        return None


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "github-pr-review-bot"}), 200


@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle GitHub webhook events"""
    # Verify webhook signature
    signature = request.headers.get('X-Hub-Signature-256', '')
    if not verify_webhook_signature(request.data, signature):
        logger.warning("Invalid webhook signature")
        return jsonify({"error": "Invalid signature"}), 401

    # Parse webhook event
    event_type = request.headers.get('X-GitHub-Event')
    payload = request.json

    logger.info(f"Received webhook event: {event_type}")

    # Handle pull request events
    if event_type == 'pull_request':
        action = payload.get('action')
        logger.info(f"PR action: {action}")

        if action in ['opened', 'synchronize', 'reopened']:
            installation_id = payload.get('installation', {}).get('id')
            if not installation_id:
                logger.error("No installation ID found in webhook payload")
                return jsonify({"error": "No installation ID"}), 400

            # Process PR review asynchronously
            try:
                review_pr(payload, installation_id)
            except Exception as e:
                logger.error(f"Error processing PR review: {e}")
                return jsonify({"error": str(e)}), 500

        return jsonify({"status": "processed"}), 200

    # Handle workflow run events (GitHub Actions)
    if event_type == 'workflow_run':
        action = payload.get('action')
        logger.info(f"Workflow run action: {action}")

        if action in ['completed']:
            installation_id = payload.get('installation', {}).get('id')
            if not installation_id:
                logger.error("No installation ID found in webhook payload")
                return jsonify({"error": "No installation ID"}), 400

            # Process workflow run analysis
            try:
                analyze_workflow_run(payload, installation_id)
            except Exception as e:
                logger.error(f"Error processing workflow run: {e}")
                return jsonify({"error": str(e)}), 500

        return jsonify({"status": "processed"}), 200

    # Handle issue comment events (for mention-based triggers)
    if event_type == 'issue_comment':
        action = payload.get('action')
        logger.info(f"Issue comment action: {action}")

        if action == 'created':
            comment_body = payload.get('comment', {}).get('body', '').strip()
            installation_id = payload.get('installation', {}).get('id')
            
            if not installation_id:
                logger.error("No installation ID found in webhook payload")
                return jsonify({"error": "No installation ID"}), 400

            # Check for EXACT mention triggers (no extra text allowed)
            if comment_body == '@_ab_triage':
                logger.info("Detected exact @_ab_triage mention")
                try:
                    handle_triage_mention(payload, installation_id)
                except Exception as e:
                    logger.error(f"Error processing triage mention: {e}")
                    return jsonify({"error": str(e)}), 500
                    
            elif comment_body == '@_ab_prreview':
                logger.info("Detected exact @_ab_prreview mention")
                try:
                    handle_pr_review_mention(payload, installation_id)
                except Exception as e:
                    logger.error(f"Error processing PR review mention: {e}")
                    return jsonify({"error": str(e)}), 500

        return jsonify({"status": "processed"}), 200

    return jsonify({"status": "ignored"}), 200


def review_pr(payload, installation_id):
    """Review a pull request using Gemini API"""
    pr_data = payload.get('pull_request', {})
    repo_full_name = pr_data.get('base', {}).get('repo', {}).get('full_name')
    pr_number = pr_data.get('number')
    pr_url = pr_data.get('html_url')

    logger.info(f"Reviewing PR #{pr_number} in {repo_full_name}")

    # Get GitHub client
    github_client = get_github_client(installation_id)
    if not github_client:
        logger.error("Failed to create GitHub client")
        return

    try:
        repo = github_client.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)

        # Get PR details
        title = pr.title
        body = pr.body or ""
        base_sha = pr.base.sha
        head_sha = pr.head.sha

        # Get file changes
        files = pr.get_files()
        file_changes = []

        for file in files:
            file_info = {
                'filename': file.filename,
                'status': file.status,
                'additions': file.additions,
                'deletions': file.deletions,
                'changes': file.changes,
                'patch': file.patch if hasattr(file, 'patch') else None
            }
            file_changes.append(file_info)

        logger.info(f"Found {len(file_changes)} changed files")

        # Get repo URL for prompt selection
        repo_url = pr_data.get('base', {}).get('repo', {}).get('html_url', '') or repo.html_url

        # Generate review using Gemini
        review_comments = pr_reviewer.review_pr(
            title=title,
            body=body,
            file_changes=file_changes,
            repo_url=repo_url
        )

        if not review_comments:
            logger.info("No review comments generated")
            return

        # Post review comments
        post_review_comments(pr, review_comments)

    except GithubException as e:
        logger.error(f"GitHub API error: {e}")
    except Exception as e:
        logger.error(f"Error reviewing PR: {e}")


def post_review_comments(pr, review_comments):
    """Post review comments to the PR"""
    try:
        # Create a review summary comment
        summary_body = pr_reviewer.format_review_summary(review_comments)

        # Post as a PR comment
        pr.create_issue_comment(summary_body)
        logger.info("Posted review summary comment")

        # Post inline comments for specific files
        for comment in review_comments.get('file_comments', []):
            if comment.get('line') and comment.get('path'):
                try:
                    pr.create_review_comment(
                        body=comment['comment'],
                        commit_id=pr.head.sha,
                        path=comment['path'],
                        line=comment['line']
                    )
                    logger.info(f"Posted inline comment on {comment['path']}:{comment['line']}")
                except Exception as e:
                    logger.warning(f"Could not post inline comment: {e}")
                    # Fallback to general comment
                    pr.create_issue_comment(
                        f"**{comment['path']}** (line {comment['line']}):\n{comment['comment']}"
                    )

    except Exception as e:
        logger.error(f"Error posting review comments: {e}")


def analyze_workflow_run(payload, installation_id):
    """Analyze GitHub Actions workflow run and comment on PR"""
    workflow_run = payload.get('workflow_run', {})
    workflow_name = workflow_run.get('name', 'Unknown Workflow')
    conclusion = workflow_run.get('conclusion')  # success, failure, cancelled, etc.
    status = workflow_run.get('status')  # completed, in_progress, etc.
    workflow_id = workflow_run.get('id')
    head_branch = workflow_run.get('head_branch', '')
    head_sha = workflow_run.get('head_sha', '')

    repo_full_name = workflow_run.get('repository', {}).get('full_name')
    if not repo_full_name:
        repo_full_name = payload.get('repository', {}).get('full_name')

    logger.info(f"Analyzing workflow run: {workflow_name} (ID: {workflow_id}) - Status: {status}, Conclusion: {conclusion}")

    # Get GitHub client
    github_client = get_github_client(installation_id)
    if not github_client:
        logger.error("Failed to create GitHub client")
        return

    try:
        repo = github_client.get_repo(repo_full_name)

        # Find associated PR for this workflow run
        prs = repo.get_pulls(state='open', head=head_branch)
        pr = None
        for pr_candidate in prs:
            if pr_candidate.head.sha == head_sha:
                pr = pr_candidate
                break

        # If no open PR found, try closed PRs
        if not pr:
            prs = repo.get_pulls(state='closed', head=head_branch)
            for pr_candidate in prs:
                if pr_candidate.head.sha == head_sha:
                    pr = pr_candidate
                    break

        if not pr:
            logger.warning(f"No PR found for workflow run {workflow_id} (branch: {head_branch}, sha: {head_sha})")
            return

        logger.info(f"Found PR #{pr.number} for workflow run")

        # Get repo URL for prompt selection
        repo_url = repo.html_url

        # Get workflow run details
        jobs_info = []
        failed_jobs = []

        try:
            workflow_run_obj = repo.get_workflow_run(workflow_id)
            jobs = workflow_run_obj.jobs()

            # Collect job information
            for job in jobs:
                job_info = {
                    'name': job.name,
                    'conclusion': job.conclusion,
                    'status': job.status,
                    'steps': []
                }

                # Get job steps
                try:
                    for step in job.steps:
                        job_info['steps'].append({
                            'name': step.name,
                            'conclusion': step.conclusion,
                            'status': step.status
                        })
                except Exception as e:
                    logger.warning(f"Could not fetch steps for job {job.name}: {e}")

                jobs_info.append(job_info)
                if job.conclusion == 'failure':
                    failed_jobs.append(job.name)
        except Exception as e:
            logger.warning(f"Could not fetch detailed workflow run info: {e}")
            # Use basic info from webhook payload
            if workflow_run.get('jobs'):
                for job in workflow_run['jobs']:
                    jobs_info.append({
                        'name': job.get('name', 'Unknown'),
                        'conclusion': job.get('conclusion', 'unknown'),
                        'status': job.get('status', 'unknown'),
                        'steps': []
                    })
                    if job.get('conclusion') == 'failure':
                        failed_jobs.append(job.get('name', 'Unknown'))

        # Generate analysis using Gemini
        analysis = pr_reviewer.analyze_workflow_run(
            workflow_name=workflow_name,
            conclusion=conclusion,
            jobs=jobs_info,
            failed_jobs=failed_jobs,
            workflow_url=workflow_run.get('html_url', ''),
            repo_url=repo_url
        )

        # Post comment on PR
        comment_body = format_workflow_comment(analysis, workflow_name, conclusion, failed_jobs, workflow_run.get('html_url', ''))
        pr.create_issue_comment(comment_body)
        logger.info(f"Posted workflow analysis comment on PR #{pr.number}")

    except GithubException as e:
        logger.error(f"GitHub API error: {e}")
    except Exception as e:
        logger.error(f"Error analyzing workflow run: {e}")


def format_workflow_comment(analysis, workflow_name, conclusion, failed_jobs, workflow_url):
    """Format workflow analysis comment for GitHub"""
    status_emoji = "✅" if conclusion == "success" else "❌" if conclusion == "failure" else "⚠️"

    comment = f"## {status_emoji} GitHub Actions Workflow: {workflow_name}\n\n"
    comment += f"**Status:** `{conclusion.upper()}`\n\n"

    if workflow_url:
        comment += f"[View Workflow Run]({workflow_url})\n\n"

    if failed_jobs:
        comment += f"**Failed Jobs:** {', '.join(failed_jobs)}\n\n"

    comment += "### Analysis\n\n"
    comment += analysis

    comment += "\n\n---\n*This analysis was generated automatically by the Gemini AI Code Review Bot.*"

    return comment


def handle_triage_mention(payload, installation_id):
    """Handle @_ab_triage mention in issue or PR comments"""
    issue_data = payload.get('issue', {})
    repo_full_name = payload.get('repository', {}).get('full_name')
    issue_number = issue_data.get('number')
    comment_url = payload.get('comment', {}).get('html_url')
    
    # Check if this is a PR (pull_request field exists in issue data)
    is_pull_request = 'pull_request' in issue_data
    
    logger.info(f"Triage mention on {'PR' if is_pull_request else 'issue'} #{issue_number} in {repo_full_name}")
    
    # Get GitHub client
    github_client = get_github_client(installation_id)
    if not github_client:
        logger.error("Failed to create GitHub client")
        return
    
    try:
        repo = github_client.get_repo(repo_full_name)
        issue = repo.get_issue(issue_number)
        
        # Validation: @_ab_triage should only work on issues, not PRs
        if is_pull_request:
            error_comment = """## ⚠️ Invalid Command

`@_ab_triage` can only be used on **issues**, not pull requests.

For PR reviews, please use `@_ab_prreview` instead.

---
*This is an automated response from Ansieyes.*"""
            issue.create_comment(error_comment)
            logger.warning(f"@_ab_triage used on PR #{issue_number}, posted error message")
            return
        
        # Post processing message
        processing_comment = issue.create_comment(
            "## Ansieyes Issue Triage has been Initiated\n\n"
            "This may take a few minutes. Results will be posted here.\n\n"
            "---\n*Powered by Ansieyes using AI-Issue-Triage*"
        )
        
        # Get issue details
        title = issue.title
        body = issue.body or ""
        repo_url = payload.get('repository', {}).get('clone_url')
        
        # Clone repository to check for triage.config.json and .omit-triage
        logger.info("Cloning repository to fetch configuration files...")
        temp_dir = tempfile.mkdtemp()
        cloned_repo_path = os.path.join(temp_dir, 'repo')
        
        try:
            subprocess.run(
                ['git', 'clone', '--depth', '1', repo_url, cloned_repo_path],
                capture_output=True,
                check=True,
                timeout=300  # 5 minute timeout
            )
            logger.info(f"Repository cloned to {cloned_repo_path}")
        except subprocess.TimeoutExpired:
            logger.error("Repository clone timeout")
            issue.create_comment(
                "## ⚠️ Timeout Error\n\n"
                "Repository clone took too long (>5 minutes).\n\n"
                "This might be due to:\n"
                "- Very large repository\n"
                "- Network issues\n"
                "- GitHub API rate limits\n\n"
                "Please try again later or contact support.\n\n"
                "---\n*Powered by Ansieyes*"
            )
            shutil.rmtree(temp_dir, ignore_errors=True)
            return
        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
            issue.create_comment(
                "## ⚠️ Configuration Error\n\n"
                "Could not clone repository to fetch triage configuration.\n\n"
                f"Error: {str(e)}\n\n"
                "---\n*Powered by Ansieyes*"
            )
            shutil.rmtree(temp_dir, ignore_errors=True)
            return
        
        # Fetch existing issues for duplicate detection
        logger.info("Fetching existing issues for duplicate detection...")
        existing_issues = []
        try:
            for existing_issue in repo.get_issues(state='open'):
                if existing_issue.number != issue_number:
                    existing_issues.append({
                        'issue_id': str(existing_issue.number),
                        'title': existing_issue.title,
                        'description': existing_issue.body or '',
                        'status': existing_issue.state,
                        'created_date': existing_issue.created_at.isoformat(),
                        'url': existing_issue.html_url
                    })
        except Exception as e:
            logger.warning(f"Could not fetch existing issues: {e}")
        
        # Run triage with cloned repo path (contains config files)
        logger.info(f"Running triage for issue #{issue_number}...")
        triage_result = issue_triager.triage_issue(
            title=title,
            description=body,
            repo_url=repo_url,
            existing_issues=existing_issues if existing_issues else None,
            repo_path=cloned_repo_path
        )
        
        # Clean up cloned repository (CRITICAL: Always cleanup)
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info(f"Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Failed to clean up temp directory: {e}")
            # Log this for monitoring - disk space issues can be serious
        
        # Check if triage_result is valid
        if not triage_result:
            logger.error("Triage returned None - something went wrong")
            # Delete processing comment
            try:
                processing_comment.delete()
            except:
                pass
            return
        
        # Format and post results
        comment_body = issue_triager.format_triage_comment(triage_result)
        issue.create_comment(comment_body)
        
        # Delete processing comment
        try:
            processing_comment.delete()
        except:
            pass
        
        # Add/Update labels based on analysis results
        labels_to_add = []
        
        # Remove old Type and Severity labels first (do this for all cases)
        try:
            existing_labels = [label.name for label in issue.labels]
            labels_to_remove = []
            
            for label in existing_labels:
                if label.startswith("Type :") or label.startswith("Severity :"):
                    labels_to_remove.append(label)
            
            for label in labels_to_remove:
                issue.remove_from_labels(label)
                logger.info(f"Removed old label: {label}")
        except Exception as e:
            logger.warning(f"Could not remove old labels: {e}")
        
        # Case 1: Prompt injection (HIGH/CRITICAL) - blocked
        if triage_result.get("prompt_injection_check"):
            injection = triage_result["prompt_injection_check"]
            risk_level = injection.get("risk_level", "").lower()
            
            if injection.get("is_injection") and risk_level in ['high', 'critical']:
                labels_to_add.append("security-alert")
                labels_to_add.append("invalid")
                labels_to_add.append("ai-triaged")
                logger.info("Adding security and invalid labels for prompt injection")
        
        # Case 2: Duplicate issue detected
        elif triage_result.get("duplicate_check", {}).get("is_duplicate"):
            labels_to_add.append("duplicate")
            labels_to_add.append("ai-triaged")
            logger.info("Adding duplicate label")
        
        # Case 3: Normal triage with Surgeon results
        elif triage_result.get("surgeon"):
            surgeon = triage_result["surgeon"]
            
            if not surgeon.get("error") and "formatted_output" in surgeon:
                # Extract type and severity from formatted text output
                import re
                formatted_text = surgeon["formatted_output"]
                
                # Extract: 🐛 **Type:** `BUG`
                type_match = re.search(r'\*\*Type:\*\*\s+`([^`]+)`', formatted_text)
                issue_type = type_match.group(1).lower() if type_match else ""
                
                # Extract: 🟡 **Severity:** `MEDIUM`
                severity_match = re.search(r'\*\*Severity:\*\*\s+`([^`]+)`', formatted_text)
                severity = severity_match.group(1).lower() if severity_match else ""
                
                # Add Type and Severity labels
                if issue_type:
                    type_label = f"Type : {issue_type.capitalize()}"
                    labels_to_add.append(type_label)
                
                if severity:
                    severity_label = f"Severity : {severity.capitalize()}"
                    labels_to_add.append(severity_label)
                
                labels_to_add.append("ai-triaged")
        
        # Apply all labels
        if labels_to_add:
            try:
                issue.add_to_labels(*labels_to_add)
                logger.info(f"Added labels: {labels_to_add}")
            except Exception as e:
                logger.warning(f"Could not add labels: {e}")
        
        logger.info(f"Triage completed for issue #{issue_number}")
        
    except GithubException as e:
        logger.error(f"GitHub API error: {e}")
    except Exception as e:
        logger.error(f"Error handling triage mention: {e}")
        import traceback
        traceback.print_exc()


def handle_pr_review_mention(payload, installation_id):
    """Handle @_ab_prreview mention in issue or PR comments"""
    issue_data = payload.get('issue', {})
    repo_full_name = payload.get('repository', {}).get('full_name')
    issue_number = issue_data.get('number')
    comment_url = payload.get('comment', {}).get('html_url')
    
    # Check if this is a PR (pull_request field exists in issue data)
    is_pull_request = 'pull_request' in issue_data
    
    logger.info(f"PR review mention on {'PR' if is_pull_request else 'issue'} #{issue_number} in {repo_full_name}")
    
    # Get GitHub client
    github_client = get_github_client(installation_id)
    if not github_client:
        logger.error("Failed to create GitHub client")
        return
    
    try:
        repo = github_client.get_repo(repo_full_name)
        issue = repo.get_issue(issue_number)
        
        # Validation: @_ab_prreview should only work on PRs, not issues
        if not is_pull_request:
            error_comment = """## ⚠️ Invalid Command

`@_ab_prreview` can only be used on **pull requests**, not regular issues.

For issue triage, please use `@_ab_triage` instead.

---
*This is an automated response from Ansieyes.*"""
            issue.create_comment(error_comment)
            logger.warning(f"@_ab_prreview used on issue #{issue_number}, posted error message")
            return
        
        # Get the PR object
        pr = repo.get_pull(issue_number)
        
        # Post processing message
        processing_comment = issue.create_comment(
            "## Ansieyes PR Review Initiated\n\n"
            "Analyzing pull request changes...\n\n"
            "This may take a few moments. Results will be posted here.\n\n"
            "---\n*Powered by Ansieyes using AI-Issue-Triage*"
        )
        
        # Get PR details
        title = pr.title
        body = pr.body or ""
        
        # Get file changes
        files = pr.get_files()
        file_changes = []
        
        for file in files:
            file_info = {
                'filename': file.filename,
                'status': file.status,
                'additions': file.additions,
                'deletions': file.deletions,
                'changes': file.changes,
                'patch': file.patch if hasattr(file, 'patch') else None
            }
            file_changes.append(file_info)
        
        logger.info(f"Found {len(file_changes)} changed files in PR #{issue_number}")
        
        # Get repo URL for prompt selection
        repo_url = payload.get('repository', {}).get('html_url', '') or repo.html_url
        
        # Generate review using AI-Issue-Triage
        review_text = pr_reviewer.review_pr(
            title=title,
            body=body,
            file_changes=file_changes,
            repo_url=repo_url
        )
        
        if not review_text or review_text.startswith("❌"):
            logger.warning("No review generated or error occurred")
            issue.create_comment(review_text or 
                "## ⚠️ Review Failed\n\n"
                "Could not generate review comments. Please check logs.\n\n"
                "---\n*Powered by Ansieyes*"
            )
            return
        
        # Post review (already formatted by AI-Issue-Triage)
        issue.create_comment(review_text)
        
        # Delete processing comment
        try:
            processing_comment.delete()
        except:
            pass
        
        logger.info(f"PR review completed for PR #{issue_number}")
        
    except GithubException as e:
        logger.error(f"GitHub API error: {e}")
    except Exception as e:
        logger.error(f"Error handling PR review mention: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY environment variable is required")
        exit(1)

    logger.info(f"Starting GitHub PR Review Bot on {HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=False)

