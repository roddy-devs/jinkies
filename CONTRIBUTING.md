# Contributing to Jinkies

Thank you for your interest in contributing to Jinkies! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/jinkies.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Commit: `git commit -m "Add your feature"`
7. Push: `git push origin feature/your-feature-name`
8. Open a Pull Request

## Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your test credentials

# Run the bot
python run.py
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where possible
- Add docstrings to functions and classes
- Keep functions focused and small
- Use meaningful variable names

## Testing

Before submitting a PR:

1. Test your changes locally
2. Ensure existing functionality still works
3. Add tests for new features (if applicable)
4. Check for any errors in logs

## Pull Request Guidelines

- **Title**: Clear and descriptive
- **Description**: Explain what changes you made and why
- **Testing**: Describe how you tested your changes
- **Screenshots**: Include if UI changes are involved

## Feature Requests

Have an idea? Open an issue with:
- Clear description of the feature
- Use case / why it's needed
- Proposed implementation (optional)

## Bug Reports

Found a bug? Open an issue with:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment (OS, Python version, etc.)
- Logs (if applicable)

## Areas for Contribution

- 📝 Documentation improvements
- 🐛 Bug fixes
- ✨ New features
- 🧪 Tests
- 🎨 UI/UX improvements
- 🌍 Internationalization

## Questions?

Open a discussion in GitHub Discussions or reach out in issues.

Thank you for contributing! 🎉
