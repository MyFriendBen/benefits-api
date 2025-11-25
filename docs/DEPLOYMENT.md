# Deployment Guide

## Overview

We use a **trunk-based development** workflow with automated deployments:

- **All PRs target `main`** - No separate development branch
- **Staging deployments are automatic** - Merging to `main` → Auto-deploy to Staging
- **Production deployments use GitHub Releases** - Create a release → Auto-deploy to Production
- **All deployment steps are automated** - No manual Heroku UI clicks or CLI commands needed

---

## Composite Actions Architecture

Our deployment workflows use **composite actions** to maintain DRY (Don't Repeat Yourself) principles and ensure consistency across all workflows.

### Available Composite Actions

All composite actions are located in `.github/actions/`:

1. **setup-python-django** - Sets up Python 3.10 with pip caching and installs dependencies from `requirements.txt`
2. **run-django-checks** - Runs Django system checks and database migrations
3. **deploy-to-heroku** - Installs Heroku CLI and deploys using `akhileshns/heroku-deploy@v3.14.15`
4. **heroku-post-deploy** - Runs post-deployment scripts (migrations, config, validations)
5. **slack-notify** - Sends deployment notifications with status (success/failure/in-progress/completed-with-warnings)
6. **run-tests** - Configurable test execution with VCR modes and optional Codecov upload

### Benefits

- **Consistency**: Same setup steps across all workflows
- **Maintainability**: Update action logic in one place
- **Reduced duplication**: Workflows reduced by 36-43% in line count
- **Reusability**: Actions can be composed together for different workflows

### Workflow Structure

**PR Validation** (`pr-validation.yaml`):
- Triggers on PRs to `main`
- Runs tests with VCR `new_episodes` mode
- Uploads coverage to Codecov
- Uses: `setup-python-django`, `run-django-checks`, `run-tests`

**Staging Deployment** (`deploy-staging.yml`):
- Triggers on push to `main`
- Runs tests with VCR `new_episodes` mode
- Deploys to Heroku staging
- Sends Slack notification on failure only
- Uses: `setup-python-django`, `run-django-checks`, `run-tests`, `deploy-to-heroku`, `slack-notify`

**Production Deployment** (`deploy-production.yml`):
- Triggers on GitHub Release publication
- Runs tests with VCR `all` mode (real API calls)
- Deploys to Heroku production with 30-minute timeout
- Runs post-deployment scripts
- Syncs translations to staging
- Sends comprehensive Slack notifications
- Uses: All composite actions

---

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

### 2. Make Changes & Commit

```bash
# Make your changes
git add .
git commit -m "feat: add new feature"
git push origin feature/your-feature-name
```

### 3. Open Pull Request

```bash
# PRs target main by default
gh pr create --base main --title "Add new feature" --fill

# Or use GitHub UI
```

**What happens automatically when PR is created**:
1. **PR Validation workflow runs** (`.github/workflows/pr-validation.yaml`)
2. **Tests execute** with VCR `new_episodes` mode (uses cached API responses)
3. **Code coverage uploaded** to Codecov for review
4. **Status checks must pass** before PR can be merged

**Workflow file**: [`.github/workflows/pr-validation.yaml`](../.github/workflows/pr-validation.yaml)

**Monitoring PR validation**:
```bash
# View PR check status
gh pr checks

# View detailed logs
gh run list --workflow=pr-validation.yaml --limit 5
gh run view <RUN_ID> --log
```

### 4. Review & Merge

- Get approval from team members
- Merge PR (squash, merge commit, or rebase based on team preference)
- **Automatic deployment to Staging happens immediately**

### 5. Test on Staging

```bash
# Visit staging environment
open https://cobenefits-api-staging.herokuapp.com

# Check deployment logs
gh workflow view "Deploy to Staging"
```

---

## Staging Deployments

**Trigger**: Automatically when code is merged to `main`

**What happens automatically**:
1. **Tests run** - Full test suite with pytest (VCR `new_episodes` mode - uses cached API responses)
2. **Linting checks** - Code formatting validated with Black (line-length = 120)
3. **Code deploys to Heroku Staging** (only if tests pass)
4. Database migrations run (`python manage.py migrate`)
5. Configurations are added (`python manage.py add_config --all`)
6. Validations run (`python manage.py validate`)
7. Slack notification sent on failure only

**Important**: Deployment will NOT proceed if tests or linting fail. Fix the issues and push again.

**Workflow file**: [`.github/workflows/deploy-staging.yml`](../.github/workflows/deploy-staging.yml)

**Monitoring**:
```bash
# View recent staging deployments
gh run list --workflow=deploy-staging.yml --limit 5

# View logs for specific deployment
gh run view <RUN_ID> --log

# Check Heroku
heroku releases -a cobenefits-api-staging
```

---

## Production Deployments

### Creating a Production Release

**When to release**: After testing changes on staging and coordinating with the team

**How to release**:

#### Via GitHub UI (Recommended)

1. Go to [Releases page](https://github.com/MyFriendBen/benefits-api/releases)
2. Click **"Draft a new release"**
3. Click **"Choose a tag"** → Type new version (e.g., `v1.2.3`)
4. Click **"Create new tag: v1.2.3 on publish"**
5. Set release title: `Release v1.2.3` or descriptive name
6. Click **"Generate release notes"** (auto-generates changelog from PRs)
7. Edit notes as needed, add highlights or important changes
8. **Check "Set as a pre-release" if this is a beta/RC**
9. Click **"Save draft"** (DO NOT click "Publish release" yet)

#### Via GitHub CLI

```bash
# Create a draft release
gh release create v1.2.3 \
  --draft \
  --title "Release v1.2.3" \
  --generate-notes

# Or with custom notes
gh release create v1.2.3 \
  --draft \
  --title "Release v1.2.3" \
  --notes "Description of changes"
```

### What Happens Automatically

When you create a draft release, the following automated process begins:

#### Stage 1: Pre-Deployment Validation (runs on draft creation)
1. **Comprehensive test suite runs with REAL API calls** (`VCR_MODE=all`)
   - All integration tests make actual calls to external APIs (HUD, Policy Engine, etc.)
   - Validates that API contracts haven't changed
   - Ensures all external dependencies are working
   - Takes 5-10 minutes to complete
2. **Slack notification sent with test results**
   - ✅ If tests PASS: "Pre-Release Tests Passed - Ready to publish manually"
   - ❌ If tests FAIL: "Pre-Release Tests Failed - Review logs and fix issues"
3. **Release stays as DRAFT** regardless of test results
4. **You manually review and publish** when ready

#### Stage 2: Production Deployment (runs when you manually publish)
1. **You click "Publish release"** in GitHub UI (after reviewing test results)
2. **Code deployment** - Exact code from the release tag is deployed to Heroku Production (30-minute timeout)
3. **Database migrations** - `python manage.py migrate`
4. **Configuration updates** - `python manage.py add_config --all`
5. **Pull validations** - `python manage.py pull_validations` from staging
6. **Run validations** - `python manage.py validate`
7. **Sync translations** - Export from production → Validate JSON → Save to `mfb-translations` repo → Import to staging
8. **Slack notifications** - Status updates sent to team at each stage (in-progress, success/warnings, or failure)

**Important**:
- Tests run automatically on draft creation, but **do not block** manual publishing
- You have full control over when to publish the release
- Tests use real API credentials to ensure production-like validation
- If tests fail, you can still manually publish (not recommended), or fix issues and create a new draft
- Publishing the release triggers the production deployment

**Workflow file**: [`.github/workflows/deploy-production.yml`](../.github/workflows/deploy-production.yml)

### Monitoring Production Deployments

```bash
# Watch the pre-release tests (after creating draft)
gh run list --workflow=deploy-production.yml --limit 1
gh run watch  # Watch the latest run

# View test results
gh run view <RUN_ID> --log

# After manually publishing, watch the deployment
gh workflow view "Deploy to Production" --web

# Verify on Heroku
heroku releases -a cobenefits-api
```

### How to Publish a Release

After creating a draft release and reviewing test results:

**Via GitHub UI:**
1. Go to the draft release on GitHub
2. Review the test results notification in Slack
3. Click **"Edit release"**
4. Click **"Publish release"**
5. Deployment to production begins automatically

**Via GitHub CLI:**
```bash
# Publish a draft release
gh release edit v1.2.3 --draft=false

# Or mark as latest and publish
gh release edit v1.2.3 --draft=false --latest
```

---

## Versioning Strategy

We use [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`

### Version Types

- **MAJOR** (v2.0.0): Breaking changes, API changes, major refactors
  - Example: Removing deprecated endpoints, changing response formats

- **MINOR** (v1.3.0): New features, backward-compatible additions
  - Example: New programs, new API endpoints, enhancements

- **PATCH** (v1.2.4): Bug fixes, small improvements, backward-compatible
  - Example: Fixing calculation errors, updating copy, dependency updates

### Pre-release Tags (Optional)

- `v1.3.0-rc.1` - Release candidate
- `v1.3.0-beta.1` - Beta release
- `v1.3.0-alpha.1` - Alpha release

### Choosing the Next Version

```bash
# Check current production version
gh release list --limit 1

# Examples:
# Current: v1.2.3
# Bug fix → v1.2.4
# New feature → v1.3.0
# Breaking change → v2.0.0
```

---

## Hotfix Workflow

When a critical bug is found in production, choose the appropriate workflow based on whether `main` is production-ready:

### Scenario 1: Main Branch is Production-Ready (Standard Flow)

**Use this when**: `main` has only changes that are ready for production.

#### 1. Create Hotfix Branch

```bash
# Start from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug-fix
```

#### 2. Make the Fix

```bash
# Fix the bug
git add .
git commit -m "hotfix: fix critical bug in eligibility calculation"
git push origin hotfix/critical-bug-fix
```

#### 3. Create PR and Merge

```bash
# Create PR against main
gh pr create --base main --title "Hotfix: Critical bug in eligibility calculation" --fill

# Get quick review and merge (automatically deploys to staging)
gh pr merge --squash
```

#### 4. Test on Staging & Release Immediately

```bash
# Verify fix on staging
open https://cobenefits-api-staging.herokuapp.com

# Create DRAFT release for testing
gh release create v1.2.4 \
  --draft \
  --title "Hotfix v1.2.4" \
  --notes "
## Hotfix
- Fixed critical bug in eligibility calculation

This is a hotfix release to address a critical issue in production.
"

# Monitor the pre-deployment tests
gh run watch

# After tests pass, manually publish the release
gh release edit v1.2.4 --draft=false
```

### Scenario 2: Main Branch Has Unreleased Work (Emergency Hotfix)

**Use this when**: `main` contains commits that are NOT ready for production.

⚠️ **Important**: This should be rare in trunk-based development. Ideally, use feature flags to keep `main` always production-ready (planned for future implementation).

#### 1. Create Hotfix Branch from Last Production Release

```bash
# Find the current production version
gh release list --limit 1

# Create hotfix branch from the production tag (NOT from main)
git fetch --tags
git checkout v1.2.3  # Replace with actual production version
git checkout -b hotfix/critical-bug-fix
```

#### 2. Make the Fix

```bash
# Fix the bug
git add .
git commit -m "hotfix: fix critical bug in eligibility calculation"
git push origin hotfix/critical-bug-fix
```

#### 3. Create Release Directly from Hotfix Branch

```bash
# Create release targeting the hotfix branch (bypasses main)
gh release create v1.2.4 \
  --target hotfix/critical-bug-fix \
  --title "Hotfix v1.2.4" \
  --notes "
## Hotfix
- Fixed critical bug in eligibility calculation

This is an emergency hotfix released directly from a hotfix branch.

**Note**: This hotfix bypassed main branch due to unreleased work in main.
"

# Monitor and approve deployment
gh run watch
```

#### 4. Backport Fix to Main

```bash
# After production deployment succeeds, backport to main
gh pr create \
  --base main \
  --head hotfix/critical-bug-fix \
  --title "Backport: Hotfix v1.2.4" \
  --body "Backporting production hotfix to main branch"

# Merge after review
gh pr merge --squash
```

### Future Improvement: Feature Flags

**Planned Enhancement**: We plan to implement feature flagging to ensure `main` is always production-ready. This will eliminate Scenario 2 by allowing incomplete features to be merged to `main` behind feature flags, ensuring emergency hotfixes can always follow the standard workflow.

---

## Rollback Procedures

If something goes wrong in production, you have multiple rollback options:

### ⚠️ Important: Database Migration Limitations

**Critical**: Heroku rollbacks only roll back application code, **NOT database migrations**.

If your deployment included database migrations:
- The migrations will remain applied even after rollback
- You may need to manually revert schema changes
- Consider the data compatibility when rolling back code
- Test rollback scenarios in staging first

**Migration conflicts cannot be resolved on Heroku** (read-only slug). All migration issues must be fixed locally:
1. Pull the latest code
2. Resolve conflicts with `python manage.py makemigrations --merge`
3. Commit and push changes
4. Deploy through normal workflow

### Option 1: Heroku Rollback (Fastest - ~30 seconds)

```bash
# View recent releases
heroku releases -a cobenefits-api

# Rollback to previous release
heroku rollback -a cobenefits-api

# Or rollback to specific version
heroku rollback v123 -a cobenefits-api
```

**Best for**: Quick rollback when no database migrations were included in the deployment.

### Option 2: Re-deploy Previous Release (Clean - ~5 minutes)

#### Via GitHub UI:
1. Go to [Releases page](https://github.com/MyFriendBen/benefits-api/releases)
2. Find the previous good release (e.g., `v1.2.2`)
3. Click **"Edit release"**
4. Check **"Set as the latest release"**
5. Click **"Update release"**
6. This triggers automatic re-deployment

#### Via CLI:
```bash
# List recent releases
gh release list --limit 5

# Mark previous release as latest
gh release edit v1.2.2 --latest
```

### Option 3: Create Revert Release (Auditable - ~10 minutes)

```bash
# Find the problematic commit
git log --oneline -10

# Create revert commit
git checkout main
git pull origin main
git revert <commit-hash>
git push origin main

# After staging deployment, create new release
gh release create v1.2.4 \
  --title "Release v1.2.4 - Revert problematic changes" \
  --notes "Reverts changes from v1.2.3 due to production issues" \
  --latest
```

---

## Integration Testing Strategy (VCR)

### Overview

The codebase uses [VCR.py](https://vcrpy.readthedocs.io/) to record and replay HTTP interactions with external APIs (HUD, Policy Engine, etc.). This provides:
- **Fast test execution** by replaying recorded API responses (cassettes)
- **Cost savings** by reducing actual API calls
- **Deterministic tests** that work offline
- **API contract validation** when re-recording cassettes

### VCR Modes Across Workflows

Different workflows use different VCR modes based on their validation needs:

| Workflow | VCR Mode | Uses Real APIs? | Purpose |
|----------|----------|-----------------|---------|
| **PR Tests** | `new_episodes` (default) | Only for new tests | Fast feedback on PRs |
| **Staging Deploy** | `new_episodes` (default) | Only for new tests | Quick validation before staging |
| **Production Deploy** | `all` | ✅ YES - All tests | Comprehensive validation |

### What Happens in Each Mode

#### `new_episodes` Mode (PR & Staging)
- Uses existing cassette recordings when available
- Only makes real API calls if:
  - A cassette doesn't exist yet
  - A new test scenario is added
- **Fast**: Typically 1-2 minutes for full test suite
- **Cost-effective**: Minimal API usage

#### `all` Mode (Production Pre-Deployment)
- **Re-records ALL cassettes** with real API calls
- Validates that external API contracts haven't changed
- Catches breaking changes from third-party APIs
- **Slower**: 5-10 minutes for full test suite
- **Thorough**: Production-level validation

### When Tests Fail

#### PR/Staging Test Failures
If tests fail during PR or staging deployment:
1. Fix the code issue
2. Push changes
3. Tests automatically re-run with cassettes

#### Production Pre-Deployment Test Failures
If real API tests fail during draft release creation:
1. **Release stays in draft** - not published
2. **Deployment does NOT proceed** - production is protected
3. Investigate the failure:
   - Check workflow logs: `gh run view <RUN_ID> --log`
   - Look for API authentication errors
   - Check for API contract changes
4. Fix the issue and create a new draft release

Common reasons for production test failures:
- External API is down or rate-limiting
- API credentials expired or invalid
- API contract changed (breaking change from provider)
- Test environment configuration issue

### Updating VCR Cassettes

When external APIs change or new integration tests are added, cassettes need updating:

```bash
# Run tests locally with VCR_MODE=all to re-record all cassettes
VCR_MODE=all pytest

# Or record only new episodes
pytest  # Uses new_episodes mode by default

# Commit updated cassettes
git add tests/cassettes/
git commit -m "chore: update VCR cassettes for API changes"
```

**Important**: Cassettes automatically scrub sensitive data (tokens, API keys) before being committed to the repository.

### Required API Credentials for Production Tests

The production pre-deployment workflow requires these API credentials to be set as GitHub secrets:

- `HUD_API_TOKEN` - Required for HUD API integration tests
- Add additional API tokens as your integration tests grow

Without these tokens, production pre-deployment tests will fail.

### Troubleshooting VCR Issues

**"No cassette found" errors**:
- Run tests locally to generate cassette: `pytest path/to/test.py`
- Commit the new cassette file

**"Cassette has no matching request" errors**:
- API request changed (URL, headers, body)
- Re-record cassette: `VCR_MODE=all pytest path/to/test.py`

**Production tests failing with authentication errors**:
- Verify GitHub secret is set: `gh secret list`
- Check token hasn't expired
- Verify token has correct API permissions

---

## Troubleshooting

### Staging Didn't Deploy After Merging

```bash
# Check workflow run status
gh run list --workflow=deploy-staging.yml --limit 3

# View logs for failed run
gh run view <RUN_ID> --log
```

**Common issues**:
- Heroku API key expired
- Migration conflicts
- Syntax errors in code
- Tests failing in CI

### Production Deployment Failed

```bash
# Check production workflow
gh run list --workflow=deploy-production.yml --limit 3
gh run view <RUN_ID> --log

# Quick rollback while investigating
heroku rollback -a cobenefits-api
```

### Migration Conflicts

Migration conflicts **cannot** be resolved on Heroku (read-only slug). You must fix locally:

```bash
# Fix locally
git checkout main
python manage.py makemigrations --merge
git add .
git commit -m "fix: resolve migration conflicts"
git push origin main

# Wait for staging deployment to complete and verify

# Create new patch release
gh release create v1.2.4 --generate-notes --latest
```

### Check Deployment Status

```bash
# Staging status
heroku ps -a cobenefits-api-staging
heroku logs --tail -a cobenefits-api-staging

# Production status
heroku ps -a cobenefits-api
heroku logs --tail -a cobenefits-api

# GitHub Actions status
gh run list --limit 10
```

### Verifying Heroku Configuration

```bash
# Check staging app info
heroku apps:info -a cobenefits-api-staging

# Check production app info
heroku apps:info -a cobenefits-api

# Verify CLI authentication
heroku auth:whoami
```

### Translation Sync Issues

The translation sync process now includes comprehensive error handling and validation:

**Error Detection:**
- Export failures are properly detected and reported
- JSON validation ensures data integrity before processing
- Import failures are captured and logged
- All errors fail the step visibly (no silent failures)

**Monitoring translation sync:**
```bash
# Check production deployment logs for translation sync step
gh run view <RUN_ID> --log | grep -A 20 "Sync translations"

# Verify translations were committed to mfb-translations repo
gh repo view MyFriendBen/mfb-translations

# Test token manually if sync is failing
git clone https://x-access-token:YOUR_TOKEN@github.com/MyFriendBen/mfb-translations.git /tmp/test-clone
```

**Common Issues:**
- **Token expired**: Regenerate `TRANSLATIONS_REPO_TOKEN` with `repo` scope
- **Export failed**: Check production Heroku logs for `bulk_export` errors
- **JSON invalid**: Review export output format, may indicate data corruption
- **Import failed**: Check staging Heroku logs for `bulk_import` errors

### Workflow Doesn't Trigger

```bash
# Check workflow syntax
gh workflow list

# View workflow runs
gh run list --workflow=deploy-production.yml

# Re-run failed workflow
gh run rerun <RUN_ID>
```

---

## Required GitHub Secrets

These secrets are configured in the repository settings and used by the deployment workflows:

**Location**: `https://github.com/MyFriendBen/benefits-api/settings/secrets/actions`

### Current Secrets

#### Heroku Deployment
- `HEROKU_API_KEY` - Heroku authentication token
- `HEROKU_STAGING_APP_NAME` - Set to `cobenefits-api-staging`
- `HEROKU_PROD_APP_NAME` - Set to `cobenefits-api`
- `HEROKU_STAGING_URL` - Set to `https://cobenefits-api-staging.herokuapp.com`
- `HEROKU_EMAIL` - Email associated with Heroku account

#### Notifications & Monitoring
- `SLACK_WEBHOOK_URL` - Webhook for deployment notifications
- `VALIDATION_SHEET_ID` - Google Sheets ID for validation results (e.g., `1JRsCKm9KeeatVoW3wjsT2YqSy63js53Ib3vivK5NFYY`)

#### External API Integrations (for production pre-deployment tests)
- `HUD_API_TOKEN` - HUD API authentication token (required for real API integration tests)
- Add other API tokens as needed for integration tests

#### Code Coverage & Quality
- `CODECOV_TOKEN` - Codecov authentication token (required for PR validation coverage uploads)

#### Translations
- `TRANSLATIONS_REPO_TOKEN` - GitHub Personal Access Token with repo permissions for `mfb-translations`

### Verifying Secrets

```bash
# List all secrets
gh secret list

# Add a new secret (if needed)
gh secret set SECRET_NAME --body "secret-value"
```

### Production Environment Protection

The production deployment workflow uses GitHub Environments with required approvals for added safety.

**Setup (one-time)**:

1. Go to: `https://github.com/MyFriendBen/benefits-api/settings/environments`
2. Click **"New environment"**
3. Name: `production`
4. Check **"Required reviewers"**
5. Add team members who can approve production deployments
6. Optionally set a deployment delay (e.g., 5 minutes to allow cancellation)
7. Click **"Save protection rules"**

**How it works**:
- When a release is published, the workflow will pause and request approval
- Designated reviewers will receive a notification
- Reviewer can view the release notes and approve or reject
- Only after approval will the deployment proceed
- All approval activity is logged for audit purposes

### Creating GitHub Personal Access Token for Translations

If you need to regenerate the `TRANSLATIONS_REPO_TOKEN`:

1. Go to: `https://github.com/settings/tokens/new`
2. Set **Token name**: `benefits-api-translations-sync`
3. Set **Expiration**: **Minimum 1 year** (recommended for production automation)
   - Shorter expirations require more frequent rotation
   - Set calendar reminder 2 weeks before expiration
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
   - Required for both read and write access to `mfb-translations` repository
5. Click **"Generate token"**
6. Copy the token immediately (you won't see it again)
7. **Store securely**: Save token in your team's password manager
8. Add it as a secret:
   ```bash
   gh secret set TRANSLATIONS_REPO_TOKEN --body "<paste-token-here>"
   ```

### Token Lifecycle & Rotation

**Expiration Impact:**
- Production deployments will fail if `TRANSLATIONS_REPO_TOKEN` expires
- Translation sync step will error, but deployment will still complete
- Set up monitoring/alerts for token expiration

**Rotation Schedule:**
- Review token annually (or per org security policy)
- Rotate immediately if:
  - Token may have been compromised
  - Team member with access leaves
  - Security audit requires it

**Rotation Process:**
1. Generate new token with same scopes
2. Update GitHub secret with new token
3. Test with a production deployment
4. Delete old token from GitHub
5. Update team password manager

---

## Deployment Checklist

### Before Merging to Main (Staging)
- [ ] Code reviewed and approved
- [ ] Tests passing
- [ ] No merge conflicts
- [ ] Migration files reviewed (if any)
- [ ] Dependencies updated (if needed)

### Before Creating Release (Production)
- [ ] All changes tested on staging
- [ ] Team notified of upcoming release
- [ ] Frontend coordinated (if applicable)
- [ ] Release notes prepared
- [ ] Correct semantic version chosen
- [ ] Database migration plan reviewed (if needed)
- [ ] Rollback plan ready
- [ ] VCR cassettes updated if API contracts changed (tests will validate)

### After Production Deployment
- [ ] Verify app is running: `heroku ps -a cobenefits-api`
- [ ] Check for errors: `heroku logs --tail -a cobenefits-api`
- [ ] Test critical user flows
- [ ] Verify in Sentry/monitoring tools
- [ ] Notify team of successful deployment

---

## Workflow Comparison

| Action | Command/Steps |
|--------|---------------|
| **Deploy to Staging** | Merge PR to `main` (automatic) |
| **Deploy to Production** | Create GitHub Release |
| **Rollback Production** | `heroku rollback -a cobenefits-api` |
| **Check Staging Logs** | `gh run list --workflow=deploy-staging.yml` |
| **Check Production Logs** | `gh run list --workflow=deploy-production.yml` |
| **View Current Version** | `gh release list --limit 1` |

---

## Additional Resources

- [GitHub Releases Documentation](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [Semantic Versioning](https://semver.org/)
- [Heroku Release Phase](https://devcenter.heroku.com/articles/release-phase)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Heroku CLI Commands](https://devcenter.heroku.com/articles/heroku-cli-commands)

---

## Getting Help

- **GitHub Actions logs**: `gh run list`
- **Heroku logs**: `heroku logs --tail -a cobenefits-api`
- **Team discussion**: Post in Slack #deployments channel
- **File issue**: `gh issue create`
