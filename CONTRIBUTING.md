# Contributing to Jinkies

Thank you for your interest in contributing to Jinkies! This document provides guidelines and instructions for contributing.

## 🚀 Getting Started

1. **Fork the repository**
   ```bash
   git clone https://github.com/your-username/jinkies.git
   cd jinkies
   ```

2. **Set up development environment**
   ```bash
   python setup.py
   ```

3. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 📝 Development Guidelines

### Code Style

- Follow PEP 8 style guide for Python code
- Use type hints where appropriate
- Add docstrings to all functions and classes
- Keep functions focused and single-purpose

### Commit Messages

Use conventional commit messages:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Example:
```
feat: add support for filtering logs by request ID
```

### Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Run tests with: `python -m pytest tests/`

### Documentation

- Update README.md if adding new features
- Add docstrings to new functions/classes
- Include examples in docstrings when helpful

## 🔧 Pull Request Process

1. **Update documentation** if needed
2. **Add tests** for new functionality
3. **Ensure all tests pass**
4. **Update CHANGELOG.md** with your changes
5. **Submit PR** with clear description

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] Tests added/updated
- [ ] All tests passing
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

## 🐛 Bug Reports

When reporting bugs, include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, etc.)
- Relevant logs or error messages

## 💡 Feature Requests

For feature requests:
- Describe the feature and its benefits
- Explain use cases
- Consider backward compatibility
- Discuss potential implementation approaches

## 📞 Questions?

- Open an issue for questions
- Tag with `question` label
- Check existing issues first

## 🙏 Thank You!

Your contributions make Jinkies better for everyone!
