# exercise2
Тестовое задание
Кластер Redis ( 6 nodes )
Кластер ClickHouse ( 4 nodes )

# Суть задания
Читает задачи из очереди Redis, ищет пользователя по заданным параметрам в ClickHouse, если нашел отправляет результат ответа от ClickHouse ( json ) на https://pastebin.com/ 

KEY для https://pastebin.com/  задается либо в файле `app/config.json` либо переменной окружения сервиса app 

 `app:`
 
 `   environment:`
 
 `     - 'PASTBIN_KEY=XXXXXXXXXXXXXXXXXXXXXXX'`
 
Только демонстрация, поэтому проиложение в начале создает базу пользователей на ClickHouse, 

генерирует задачи в Redis, потом обработка очереди. После этого ждет новые задачи на отработку.

Параметры в config.json

`parallel_count - Количество процессов на отработку задач`

`valid_tasks - Сколько сгенерировать задач с параметрами которые есть в БД`

`users - Количество сгенерированных пользователей`

`tasks - Общее количество задач включая valid_tasks`

`dispatch_timeout - проверить Redis на поступление новых задач`

Сборка через docker-compose, для этого сделан Makefile

`make up` - `Создание промежуточного image для python2. Сборка сервисов `

`make stop` - `Остановить сервисы`

`make start` - `Запустить сервисы` 



