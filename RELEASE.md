# Release Playbook

This project is ready for two distribution channels:
- `pip` package on PyPI (`trade-engine-cli`)
- Windows executable (`trade-engine.exe`) attached to GitHub Releases

## 1) One-time Setup

1. Add GitHub remote:
   ```bash
   git remote add origin <your-github-repo-url>
   ```
2. Push branch:
   ```bash
   git push -u origin main
   ```
3. Create PyPI project `trade-engine-cli` (once) at `https://pypi.org`.
4. Configure PyPI Trusted Publishing:
   - Owner: your GitHub username/org
   - Repository: your repo name
   - Workflow: `release.yml`
   - Environment: `pypi`

## 2) Local Smoke Build (optional)

```bash
pip install ".[build,groww]"
python -m build
pyinstaller --clean trade_engine.spec
```

## 3) Create a Release

1. Commit changes:
   ```bash
   git add .
   git commit -m "chore: package and release automation setup"
   ```
2. Tag and push:
   ```bash
   git tag v1.0.0
   git push origin main
   git push origin v1.0.0
   ```
3. Publish GitHub release from tag `v1.0.0`.

On release publish, GitHub Actions will:
- Build wheel + sdist
- Publish to PyPI
- Build `trade-engine.exe`
- Attach EXE to the release

## 4) Manual Workflow Dispatch (without release publish)

From GitHub Actions, run `Release` workflow with:
- `publish_to_pypi = true` to publish package
- `publish_to_pypi = false` to only build artifacts
