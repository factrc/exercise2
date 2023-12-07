.PHONY: config
config:
	rm -rf ${PWD}/clickhouse/clickhouse01 ${PWD}/clickhouse/clickhouse02 ${PWD}/clickhouse/clickhouse03 ${PWD}/clickhouse/clickhouse04
	mkdir -p ${PWD}/clickhouse/clickhouse01 ${PWD}/clickhouse/clickhouse02 ${PWD}/clickhouse/clickhouse03 ${PWD}/clickhouse/clickhouse04
	REPLICA=01 SHARD=01 envsubst < ${PWD}/clickhouse/config.xml > ${PWD}/clickhouse/clickhouse01/config.xml
	REPLICA=02 SHARD=01 envsubst < ${PWD}/clickhouse/config.xml > ${PWD}/clickhouse/clickhouse02/config.xml
	REPLICA=03 SHARD=02 envsubst < ${PWD}/clickhouse/config.xml > ${PWD}/clickhouse/clickhouse03/config.xml
	REPLICA=04 SHARD=02 envsubst < ${PWD}/clickhouse/config.xml > ${PWD}/clickhouse/clickhouse04/config.xml
	cp ${PWD}/clickhouse/users.xml ${PWD}/clickhouse/clickhouse01/users.xml
	cp ${PWD}/clickhouse/users.xml ${PWD}/clickhouse/clickhouse02/users.xml
	cp ${PWD}/clickhouse/users.xml ${PWD}/clickhouse/clickhouse03/users.xml
	cp ${PWD}/clickhouse/users.xml ${PWD}/clickhouse/clickhouse04/users.xml

.PHONY: up
up: config
	echo 'Prepare create python2 image, support Clickhouse-driver&Redis Cluster'
	docker images factrc/python2 | grep -q '^factrc/python2\s\+v1' || cd ${PWD}/python2image && docker build -t factrc/python2:v1 .
	docker-compose up -d
	echo 'Wait 5 sec ' && sleep 5
	echo "Result file in $PWD/data"
	docker logs app

.PHONY: start
start:
	docker-compose start

.PHONY: stop
stop:
	docker-compose stop

.PHONY: down
down:
	docker-compose down

.PHONY: build
build:
	docker-compose build
