.PHONY: dev agent stop bookings logs install

install:
	poetry install

dev:
	docker compose up -d
	@echo "LiveKit server running at ws://localhost:7880"

agent:
	poetry run python -m agent.main dev

stop:
	docker compose down

bookings:
	@poetry run python -c "import json; data=json.load(open('data/bookings.json')); \
	[print(f\"{b['booking_id']}  {b['guest_name']}  {b['guest_phone']}  {b['room_name']}  {b['check_in']} -> {b['check_out']}\") for b in data['bookings']]"

logs:
	docker compose logs -f livekit
