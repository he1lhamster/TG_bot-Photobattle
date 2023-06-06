buildup:
	# docker-compose rm
	docker-compose build
	docker-compose up

alembic:
	docker-compose exec web alembic init -t async migrations
	docker-compose exec web alembic upgrade head

connect_db:
	docker-compose exec db psql -U kts_user kts