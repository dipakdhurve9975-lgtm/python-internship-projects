# Publishing the two projects

SunDrop is a Windows desktop app. Its public web page can show the current interface and provide a source download. The downloading and local audio library run on the user's computer.

MathDuel needs a running Python server. The included Render blueprint uses one Gunicorn worker and 40 threads, as supported by Flask-SocketIO with simple-websocket. One worker keeps both players in the same room. Do not increase worker count without adding shared room storage.

The free hosted demo stores anonymous statistics in temporary storage. Restarts and redeployments can erase statistics and active rooms; it is not a permanent records service. Free services may sleep when unused. HTTPS is provided by the host. Hosted mode hides local adapter addresses and trusts one hosting reverse proxy for source addresses. Do not enable hosted mode directly on an untrusted network without that proxy.

The LAN launch command remains available. Publishing status and verified URLs should be recorded only after the live service has been checked.

References: https://flask-socketio.readthedocs.io/en/stable/deployment.html and https://render.com/docs/deploy-flask
