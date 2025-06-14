import os
from flask import Flask, render_template, request, send_file
import io, csv, time, re
import googlemaps, requests

app = Flask(__name__)

# Load your hard-coded key from Replit Secrets
API_KEY = os.environ["API_KEY"]

def geocode_city(gmaps, city):
    geo = gmaps.geocode(city)
    if not geo:
        raise ValueError("Cannot geocode city.")
    loc = geo[0]["geometry"]["location"]
    return loc["lat"], loc["lng"]

def fetch_places(gmaps, query, max_results):
    places, seen = [], set()
    resp = gmaps.places_text(query=query, region="cy")
    places += resp.get("results", [])
    while "next_page_token" in resp and len(places) < max_results:
        time.sleep(2)
        resp = gmaps.places_text(page_token=resp["next_page_token"])
        places += resp.get("results", [])
    unique = []
    for p in places:
        if p["place_id"] not in seen:
            seen.add(p["place_id"])
            unique.append(p)
            if len(unique) >= max_results:
                break
    return unique

def get_details(gmaps, pid):
    fields = ["name","formatted_address","formatted_phone_number","website"]
    r = gmaps.place(place_id=pid, fields=fields).get("result", {})
    return {
        "name":    r.get("name"),
        "address": r.get("formatted_address"),
        "phone":   r.get("formatted_phone_number"),
        "website": r.get("website")
    }

def scrape_email(url):
    if not url:
        return ""
    try:
        txt = requests.get(url, timeout=5).text
        em  = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", txt)
        return em[0] if em else ""
    except:
        return ""

@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        city    = request.form["city"].strip()
        kw      = request.form["keyword"].strip()
        maximum = int(request.form.get("max", 50))
        gmaps   = googlemaps.Client(key=API_KEY)

        # Run scraper logic
        _, _ = geocode_city(gmaps, city)
        query  = f"{kw} in {city}"
        places = fetch_places(gmaps, query, maximum)

        # Build CSV in memory
        buf    = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["name","address","phone","website","email"])
        for p in places:
            info = get_details(gmaps, p["place_id"])
            info["email"] = scrape_email(info["website"])
            writer.writerow([info[k] for k in ["name","address","phone","website","email"]])
        buf.seek(0)

        return send_file(
            io.BytesIO(buf.getvalue().encode("utf-8")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"{city.replace(' ','_')}_{kw.replace(' ','_')}.csv"
        )

    return render_template("index.html")

if __name__ == "__main__":
    # Replit expects port 3000 and host 0.0.0.0
    app.run(host="0.0.0.0", port=3000)