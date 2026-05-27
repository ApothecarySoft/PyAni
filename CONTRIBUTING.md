# Contributing to PyAni

Thank you for your interest in contributing to PyAni! I'm just doing this as a hobby project so I'll take the help!

## How to Contribute

### Reporting Bugs

If you discover a bug, please open an issue on GitHub with:
- A clear description of the problem
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Your Python version and operating system

### Suggesting Enhancements

I'd love to hear your ideas for improving PyAni! Please open an issue with:
- A clear description of the enhancement
- Why you think it would be useful
- Any relevant examples or mockups

### Submitting Pull Requests

1. **Fork the Repository**: Click the "Fork" button on the repository page
2. **Clone Your Fork**: 
   ```bash
   git clone https://github.com/YOUR-USERNAME/PyAni.git
   cd PyAni
   ```
3. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Make Your Changes**: Implement your feature or fix
5. **Commit Your Changes**:
   ```bash
   git commit -m "Add a clear, descriptive commit message"
   ```
6. **Push to Your Fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Open a Pull Request**: Go to the original repository and click "New Pull Request"

### Pull Request Guidelines

- Provide a clear title and description
- Reference any related issues (e.g., "Fixes #123")
- Keep commits focused and logical

## Development Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Code Style

- Try to follow general Python best practices
- Use clear and descriptive variable names
- Add docstrings to functions and classes
- Keep functions focused and modular
- Format code using `black`

### Using Black

First, install Black:
```bash
pip install black
```

Then format your code with Black, run:
```bash
black .
```

Or to format specific files:
```bash
black path/to/file.py
```

Black will automatically format your code to follow PEP 8 style guidelines. For more information, visit the [Black documentation](https://black.readthedocs.io/).

## License

By contributing to PyAni, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for helping make PyAni better! 🎉
