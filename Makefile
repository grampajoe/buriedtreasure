.PHONY: test
test:
	docker-compose build
	docker-compose run web /bin/sh -c 'pip install -r test_requirements.txt && pytest'	
