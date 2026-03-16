.PHONY: install start test build-docker run-docker clean clean-recordings clean-recordings-apply

# Default retention for recordings cleanup (days)
RETENTION_DAYS ?= 7

install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt

start:
	@echo "Starting the Streamlit application..."
	streamlit run src/app.py

test:
	@echo "Running tests..."
	pytest

build-docker:
	@echo "Building Docker image..."
	docker build -t carescore-ai .

run-docker:
	@echo "Running Docker container..."
	@echo "Remember to set API_KEY environment variables, e.g.:"
	@echo "  GEMINI_AI_KEY=\"your_key\" DAILY_API_KEY=\"your_key\" make run-docker"
	docker run -p 8501:8501 \
		-e GEMINI_AI_KEY="$(GEMINI_AI_KEY)" \
		-e DAILY_API_KEY="$(DAILY_API_KEY)" \
		--name carescore-app carescore-ai

clean:
	@echo "Cleaning up build artifacts and temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + || true
	find . -type f -name "*.pyc" -delete || true
	rm -f .pytest_cache/* || true
	rm -rf .pytest_cache || true
	rm -f *.docx *.pdf *.mp4 *.ini || true
	find . -type f -name "*.pdf" -delete || true
	find . -type f -name "*.mp4" -delete || true
	find . -type f -name "*.ini" -delete || true
	rm -rf soap_notes || true
	@echo "Clean up complete."

# Dry-run cleanup of Daily recordings older than RETENTION_DAYS
clean-recordings:
	@echo "Dry-run: listing Daily recordings older than $(RETENTION_DAYS) days that would be deleted..."
	@echo "Tip: ensure DAILY_API_KEY is set in your environment."
	python scripts/cleanup_recordings.py --retention-days $(RETENTION_DAYS)

# Apply cleanup (destructive): actually delete Daily recordings older than RETENTION_DAYS
clean-recordings-apply:
	@echo "WARNING: This will DELETE Daily recordings older than $(RETENTION_DAYS) days."
	@echo "Tip: ensure DAILY_API_KEY is set in your environment."
	python scripts/cleanup_recordings.py --retention-days $(RETENTION_DAYS) --yes