from sqlalchemy import event


def test_create_and_list(client):
    res = client.post("/tasks", json={"title": "테스트 할 일", "tags": ["개인", "긴급"]})
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "테스트 할 일"
    assert {t["name"] for t in body["tags"]} == {"개인", "긴급"}

    res = client.get("/tasks")
    assert res.status_code == 200
    tasks = res.json()
    assert len(tasks) == 1
    assert tasks[0]["tags"]


def test_list_tasks_query_count(client, db_session):
    for i in range(5):
        res = client.post("/tasks", json={"title": f"할 일 {i}", "tags": [f"태그{i}", "공통"]})
        assert res.status_code == 201
    # POST 응답 직렬화로 이미 로딩된 태그를 비워, GET에서 실제 조회 쿼리 수를 잽니다.
    db_session.expire_all()

    queries = []
    engine = db_session.get_bind()

    def count_query(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    event.listen(engine, "before_cursor_execute", count_query)
    try:
        res = client.get("/tasks")
    finally:
        event.remove(engine, "before_cursor_execute", count_query)

    assert res.status_code == 200
    tasks = res.json()
    assert len(tasks) == 5
    assert all(len(t["tags"]) == 2 for t in tasks)
    # 할 일 조회 1번 + 태그 일괄 조회 1번. 할 일 수에 비례해 늘어나면 N+1입니다.
    assert len(queries) <= 2
