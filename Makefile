.PHONY: install test demo run clean help

help:
	@echo "Available commands:"
	@echo "  make install   - Install dependencies + Playwright"
	@echo "  make test      - Run all tests"
	@echo "  make demo      - Run demo with mock mode (Stripe)"
	@echo "  make run       - Run with LinkedIn URL (usage: make run URL=... )"
	@echo "  make clean     - Remove Python cache files"

install:
	pip install -r requirements.txt
	playwright install chromium

 test:
	pytest tests/ -v

demo:
	python main.py --linkedin-url "https://www.linkedin.com/company/stripe" --mock

run:
	python main.py --linkedin-url "$(URL)"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cache cleaned."
