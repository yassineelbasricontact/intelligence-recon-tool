# Intelligence Reconnaissance Tool - Operational Procedures

This document contains procedures for maintaining and operating the Intelligence Reconnaissance Tool. Follow these procedures to ensure consistent operation and maintenance.

## 📋 Table of Contents
1. [Verification Procedures](#-verification-procedures)
2. [GitHub Synchronization](#-github-synchronization)
3. [Threshold Validation](#-threshold-validation)
4. [Results Management](#-results-management)
5. [Dependency Management](#-dependency-management)
6. [Troubleshooting](#-troubleshooting)

## 🔍 Verification Procedures

### Pre-Task Verification
Before every task:
1. Read CLAUDE.md to understand the 100 IP threshold requirement at each level
2. Run verification: `python3 intel_recon.py --query="ics" --thread=4`
3. Verify output shows:
   - "[+] Big cities (>100 IPs, drill to ASN): N"
   - "[+] Small cities (≤100 IPs, scrape directly): M"
4. Confirm ≥40% scrape rate (actual IPs vs. reported count)
5. If test fails: fix code, re-run, verify again

### Post-Change Verification
After any code or configuration change:
1. Run verification alone (do not wait for user input)
2. Use the same test command: `python3 intel_recon.py --query="ics" --thread=4`
3. Verify threshold logic is maintained
4. Never skip verification - it runs automatically every time

## ☁️ GitHub Synchronization

### Setting Up GitHub Remote (One-Time Setup)
To connect this repository to GitHub:
```bash
# From the project root directory
git remote add origin https://github.com/[YOUR_USERNAME]/intelligence-recon-tool.git
```

### Pushing Changes to GitHub
To push local changes to GitHub:
```bash
# Push to GitHub (set upstream on first push)
git push -u origin master

# For subsequent pushes
git push
```

### Pulling Changes from GitHub
To update local repository with GitHub changes:
```bash
git pull
```

### Verifying GitHub Connection
To check remote repository configuration:
```bash
git remote -v
```

## 🎯 Threshold Validation

### Hierarchy Threshold Requirements
The tool enforces a strict 100 IP threshold at each level of the hierarchy:
1. **Country Level**: If total IPs ≤ 100, scrape directly; if > 100, proceed to cities
2. **City Level**: If city IPs ≤ 100, scrape directly; if > 100, proceed to ASNs  
3. **ASN Level**: If ASN IPs ≤ 100, scrape directly; if > 100, proceed to orgs
4. **Org Level**: Always scrape IPs directly

### Verification Points
During operation, verify you see output like:
- `[+] Big cities (>100 IPs, drill to ASN): N` 
- `[+] Small cities (≤100 IPs, scrape directly): M`
- Hierarchical drilling only occurs when counts exceed 100 at each level

## 💾 Results Management

### Old Results Location
All historical scan results are archived in:
```
/home/viper/Projects/shodan_old_results/
```

### Result Directory Structure
Archived results include:
- Scan-specific directories (7-eleven, ftp_anonymous_login_successful, hikvision*, etc.)
- IP lists and reconnaissance data
- Test files and temporary results

### Current Results Location
Active scan results are stored in:
- `[query_dir]/ips.txt` - Main IP list output
- `[query_dir]/recon/` - Reconnaissance data (when enabled)
- `[query_dir]/logs/` - Operational logs

## 📦 Dependency Management

### Python Dependencies
Core dependencies are listed in `requirements.txt`:
```
shodan==1.31.0
# ... other dependencies
```

### Installing/Updating Dependencies
```bash
# Install from requirements.txt
pip install -r requirements.txt

# Update specific package
pip install --upgrade shodan

# Generate updated requirements file
pip freeze > requirements.txt
```

### Virtual Environment
The project uses a Python virtual environment located at `venv/`:
- To activate: `source venv/bin/activate`
- To deactivate: `deactivate`
- The environment is already configured with all required dependencies

## 🔧 Troubleshooting

### Common Issues

#### GitHub Authentication Errors
If you encounter authentication errors when pushing to GitHub:
1. Ensure you have a valid GitHub personal access token
2. Use HTTPS URL with token: `https://[TOKEN]@github.com/yassineelbasricontact/intelligence-recon-tool.git`
3. Or use SSH key authentication instead

#### Threshold Logic Not Working
If the 100 IP threshold is not being respected:
1. Verify no pagination limits were added (prohibited by CLAUDE.md)
2. Check that the hierarchy drilling logic is intact
3. Run the verification test to confirm behavior

#### Missing Dependencies
If you get import errors:
1. Ensure virtual environment is activated: `source venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Check Python version compatibility

### Getting Help
For issues not covered here:
1. Consult the CLAUDE.md file for project-specific guidelines
2. Check the code comments in `intel_recon.py` and other scripts
3. Review the verification output for clues about system state

## 🔄 Maintenance Schedule

### Daily
- Run verification test after any changes
- Check for unusual error patterns in logs

### Weekly  
- Review and update dependencies if needed
- Verify GitHub synchronization is working
- Check results directory sizes

### Before Major Changes
- Backup current state
- Run full verification suite
- Document changes in commit messages

---

*Last Updated: $(date)*
*Version: 1.0*
*Follow all procedures in CLAUDE.md for project-specific requirements.*
