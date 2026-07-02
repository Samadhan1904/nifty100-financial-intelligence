.PHONY: load ratios test report dashboard api clean help

help:
	@echo Available commands:
	@echo   make load       - Run ETL pipeline
	@echo   make ratios     - Compute financial ratios
	@echo   make test       - Run test suite
	@echo   make dashboard  - Start Streamlit on :8501
	@echo   make api        - Start FastAPI on :8000
	@echo   make clean      - Remove cache files

load:
	python src\etl\loader.py

ratios:
	python src\analytics\ratios.py

test:
	pytest tests\ --html=reports\pytest_report.html -v

dashboard:
	streamlit run src\dashboard\app.py

api:
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

clean:
	del /s /q *.pyc 2>nul