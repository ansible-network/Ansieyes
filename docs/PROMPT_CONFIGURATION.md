# Prompt Configuration Guide

The bot uses a YAML configuration file (`prompt_config.yml`) to customize prompts based on repository types and URLs.

## Overview

The prompt system allows you to:
- Define different prompt types (network, devtools, default)
- Map repository URLs to specific prompt types using regex patterns
- Customize both PR review prompts and workflow analysis prompts per repo type

## Configuration Structure

```yaml
repo_mappings:
  network:
    - "github.com/.*/ansible.*"
    - "github.com/.*/network.*"

  devtools:
    - "github.com/.*/devtools.*"
    - "github.com/.*/tool.*"

prompts:
  default:
    pr_review:
      system_role: "..."
      review_structure: "..."
      workflow_analysis: "..."

  network:
    pr_review:
      system_role: "..."
      review_structure: "..."
      workflow_analysis: "..."
```

## How It Works

1. **Repository Matching**: When a PR or workflow run is received, the bot extracts the repository URL
2. **Pattern Matching**: The bot checks the URL against regex patterns in `repo_mappings`
3. **Prompt Selection**: Based on the match, it selects the appropriate prompt type (network, devtools, or default)
4. **Fallback**: If no pattern matches, the `default` prompt is used

## Adding New Repo Types

### Step 1: Add URL Patterns

Edit `prompt_config.yml` and add patterns to `repo_mappings`:

```yaml
repo_mappings:
  your_new_type:
    - "github.com/.*/your-pattern.*"
    - "github.com/org/.*"
```

### Step 2: Add Prompt Templates

Add prompt configuration under `prompts`:

```yaml
prompts:
  your_new_type:
    pr_review:
      system_role: "You are an expert in [your domain]..."
      review_structure: |
        Your custom review structure here...
      workflow_analysis: |
        Your custom workflow analysis template...
```

## Customizing Prompts

### PR Review Prompts

Each repo type can have:
- **system_role**: The AI's role and expertise area
- **review_structure**: Instructions for the review format and content
- **workflow_analysis**: Template for analyzing GitHub Actions workflows

### Example: Network Repositories

Network prompts focus on:
- Network device configurations
- Security vulnerabilities
- Ansible playbook best practices
- Network operations and reliability

### Example: DevTools Repositories

DevTools prompts focus on:
- API design and usability
- Developer experience
- Documentation quality
- CLI and SDK best practices

## URL Pattern Matching

Patterns use Python regex syntax:
- `github.com/.*/ansible.*` - Matches any repo with "ansible" in the name
- `github.com/org/.*` - Matches all repos in an organization
- `github.com/.*/network.*` - Matches repos with "network" in the name

**Note**: Patterns are case-insensitive and matched against the full repository URL.

## Testing

To test your configuration:

1. Check logs when processing a PR:
   ```bash
   pm2 logs Ansieyes | grep "Matched repo URL"
   ```

2. The log will show which repo type was matched:
   ```
   Matched repo URL 'github.com/org/ansible-playbooks' to type 'network' using pattern 'github.com/.*/ansible.*'
   ```

3. If no match is found:
   ```
   No match found for repo URL 'github.com/org/my-repo', using default prompt
   ```

## Default Behavior

If `prompt_config.yml` is missing or invalid:
- The bot falls back to hardcoded default prompts
- A warning is logged but the bot continues to function
- Default prompts are generic code review prompts

## File Location

The configuration file should be located at:
- `prompt_config.yml` in the same directory as `pr_reviewer.py`
- Or specify a custom path when initializing `PRReviewer`:
  ```python
  pr_reviewer = PRReviewer(api_key=GEMINI_API_KEY, config_path="/path/to/prompt_config.yml")
  ```

## Best Practices

1. **Start with Default**: Use the default prompt as a baseline
2. **Be Specific**: Make repo type patterns specific enough to avoid false matches
3. **Test Patterns**: Test regex patterns before deploying
4. **Document Changes**: Update this guide when adding new repo types
5. **Version Control**: Keep `prompt_config.yml` in version control

## Troubleshooting

### Prompts Not Matching

- Check regex patterns are correct
- Verify repository URLs in logs match expected format
- Test patterns using Python regex: `re.search(pattern, url)`

### Configuration Not Loading

- Check file path is correct
- Verify YAML syntax is valid
- Check file permissions
- Review logs for loading errors

### Wrong Prompt Used

- Check logs for which repo type was matched
- Verify URL patterns are in correct order (first match wins)
- Ensure default prompt is properly configured

