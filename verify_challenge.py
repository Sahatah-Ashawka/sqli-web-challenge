import json

import app


def post(client, query):
    response = client.post(
        "/execute",
        data=json.dumps({"query": query}),
        content_type="application/json",
    )
    return response.status_code, response.get_json()


def expect_ok(client, query, needle):
    status, data = post(client, query)
    assert status == 200, data
    text = json.dumps(data)
    assert needle in text, data
    return data


def expect_blocked(client, query, needle):
    status, data = post(client, query)
    assert status == 400, data
    assert needle in data["error"], data
    return data


def main():
    client = app.app.test_client()

    page = client.get("/")
    assert page.status_code == 200
    page_html = page.get_data(as_text=True).lower()
    assert "<script" not in page_html
    assert client.get("/assets/box").status_code == 404
    assert client.get("/assets/input").status_code == 404
    assert client.get("/static/app.js").status_code == 404

    expect_ok(client, "select\nsqlite_version()", "sqlite_version()")
    expect_ok(client, "select\nname\nfrom\nsqlite_schema\nwhere\ntype='table'", "archive_7d2e")
    expect_ok(client, "pragma\ntable_info(archive_7d2e)", "flag_9a61")
    expect_blocked(client, "select\nsql\nfrom\nsqlite_master", "Database structure is blocked.")
    expect_blocked(client, "SELECT\nsql\nFROM\nsqlite_schema", "Database structure is blocked.")

    for keyword in (
        "flag",
        "flaG",
        "flAg",
        "flAG",
        "fLag",
        "fLaG",
        "fLAg",
        "fLAG",
        "Flag",
        "FlaG",
        "FlAg",
        "FlAG",
        "FLag",
        "FLaG",
        "FLAg",
    ):
        expect_blocked(
            client,
            f"select\n{keyword}_9a61\nfrom\narchive_7d2e",
            f'"{keyword}" keyword is blocked.',
        )

    expect_ok(client, "select\nFLAG_9a61\nfrom\narchive_7d2e", "CTF{newline_case_filter_bypass}")
    expect_ok(client, "select\nFLAG_9A61\nfrom\narchive_7d2e", "CTF{newline_case_filter_bypass}")

    page_result = client.post(
        "/",
        data={"query": "select\nFLAG_9a61\nfrom\narchive_7d2e"},
        content_type="multipart/form-data",
    )
    page_result_html = page_result.get_data(as_text=True)
    assert page_result.status_code == 200
    assert "CTF{newline_case_filter_bypass}" in page_result_html
    assert "<script" not in page_result_html.lower()

    raw_encoded = client.post(
        "/execute",
        data='{"query":"select%0aFLAG_9a61%0afrom%0aarchive_7d2e"}',
        content_type="application/json",
    )
    assert raw_encoded.status_code == 400, raw_encoded.get_data(as_text=True)
    assert "%0a is blocked." in raw_encoded.get_json()["error"]

    compact = client.post(
        "/execute",
        data=json.dumps({"query": "select(FLAG_9a61)from(archive_7d2e)"}),
        content_type="application/json",
    )
    assert compact.status_code == 400, compact.get_json()

    print("challenge verified")


if __name__ == "__main__":
    main()
