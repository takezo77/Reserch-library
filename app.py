from flask import Flask, render_template, request
import requests
import time
import os

app = Flask(__name__)

# ★ 本物のカーリルAPIキーを入れる ★
CALIL_API_KEY = os.environ.get("CALIL_API_KEY")

SYSTEM_IDS = [
    "Mie_Tsu",
    "Mie_Yokkaichi",
    "Mie_Suzuka",
    "Mie_Matsusaka",
    "Mie_Ise"
]

SYSTEM_NAMES = {
    "Mie_Tsu": "津市立図書館",
    "Mie_Yokkaichi": "四日市市立図書館",
    "Mie_Suzuka": "鈴鹿市立図書館",
    "Mie_Matsusaka": "松阪市立図書館",
    "Mie_Ise": "伊勢市立図書館"
}


# -------------------------------
# Google Books API：タイトル→ISBN
# -------------------------------
def search_isbns(title):
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": f"intitle:{title}",
        "maxResults": 3,
        "langRestrict": "ja"
    }

    r = requests.get(url, params=params)
    if r.status_code != 200:
        return []

    try:
        data = r.json()
    except:
        return []

    results = []
    for item in data.get("items", []):
        info = item.get("volumeInfo", {})
        for i in info.get("industryIdentifiers", []):
            if i.get("type") == "ISBN_13":
                results.append({
                    "title": info.get("title", "不明"),
                    "isbn": i.get("identifier")
                })
                break

    return results


# -------------------------------
# カーリルAPI
# -------------------------------
def search_calil(isbn):
    url = "https://api.calil.jp/check"
    params = {
        "appkey": CALIL_API_KEY,
        "isbn": isbn,
        "systemid": ",".join(SYSTEM_IDS),
        "format": "json",
        "callback": "no"
    }

    r = requests.get(url, params=params)
    if not r.text.strip():
        return []

    try:
        data = r.json()
    except:
        return []

    session = data.get("session")

    while data.get("continue") == 1:
        time.sleep(1)
        r = requests.get(url, params={
            "session": session,
            "format": "json",
            "callback": "no"
        })
        if not r.text.strip():
            break
        try:
            data = r.json()
        except:
            break

    results = []
    systems = data.get("books", {}).get(isbn, {})

    for systemid, info in systems.items():
        for branch, status in info.get("libkey", {}).items():
            results.append({
                "library": f"{SYSTEM_NAMES.get(systemid, systemid)}（{branch}）",
                "status": status
            })

    return results


# -------------------------------
# ルーティング
# -------------------------------
@app.route("/", methods=["GET"])
def index():
    q = request.args.get("q", "")
    books = []

    if q:
        isbn_list = search_isbns(q)
        for book in isbn_list:
            book["libraries"] = search_calil(book["isbn"])
            books.append(book)

    return render_template("index.html", q=q, books=books)


if __name__ == "__main__":
    app.run(debug=True)
