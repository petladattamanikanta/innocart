# Contributing to InnoCart V2

Thank you for contributing to InnoCart V2!

## Code Contributions

1. Fork the repository and create your feature branch (`git checkout -b feature/AmazingFeature`).
2. Run backend tests before submitting:
   ```bash
   cd backend
   python -m unittest discover -s tests
   ```
3. Test frontend build:
   ```bash
   cd frontend
   npm run build
   ```
4. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
5. Push to the branch (`git push origin feature/AmazingFeature`).
6. Open a Pull Request.

## Code Style & Guidelines

- **Python**: Follow PEP 8 guidelines. Keep backend routes clean and business logic inside `app/services/`.
- **Frontend**: Keep UI components inside `src/components/`, styles in `src/index.css` or Tailwind classes.
- **Documentation**: Update markdown documentation inside `docs/` or `README.md` if changing public contracts.
