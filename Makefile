.PHONY: ingest analyst impact docs orchestrator stop start evals

ingest:
	python ingest/embedder.py sample_code/

analyst:
	cd agents/code_analyst && python main.py

impact:
	cd agents/impact_analyzer && python main.py

docs:
	cd agents/doc_generator && python main.py

orchestrator:
	cd orchestrator && python main.py

start:
	python agents/code_analyst/main.py &
	python agents/impact_analyzer/main.py &
	python agents/doc_generator/main.py &
	python orchestrator/main.py

stop:
	pkill -f "uvicorn" || true

evals:
	python evals/run_evals.py --skip-generation --json
