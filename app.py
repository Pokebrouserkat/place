# Path to presistent storage folder, where pixels.json and ids.json are stored
path = "app/data"
# Path to index.html, rather than, well, """<!DOCTYPE html>...""" in the code
index = "index.html"
# size of the grid
gridSize = 50
# Whether to log everything for debugging purposes
logs = True
# Delay between pixel placements in seconds
timer = 60 * 5
# Port to run the server on
port = 8080
# Whether the server is down, and will not accept new connections or serve the document
down = False
# Path to boop.mp3, boop.wav, etc
boops = []
# TEMPORARY: Open the web browser
import webbrowser
webbrowser.open("http://localhost:" + str(port))

#import websockets
#import asyncio
import flask
import flask_sock
import json
import time

# All the connected clients
clients = set()
ids = {}
pixels = []

def log(*args, **kwargs):
    if logs:
        print(*args, **kwargs)

def savePixels():
    try:
        with open(path + "pixels.json", "w") as f:
            log("Saving pixels")
            json.dump(pixels, f)
    except Exception as e:
        log("Failed to save pixels - ", e.__class__.__name__, " ", str(e))
def saveIds():
    try:
        with open(path + "ids.json", "w") as f:
            log("Saving IDs")
            json.dump(ids, f)
    except Exception as e:
        log("Failed to save IDs - ", e.__class__.__name__, " ", str(e))

try:
    with open(path + "pixels.json", "r") as f:
        pixels = json.load(f)
except:
    pass
try:
    with open(path + "ids.json", "r") as f:
        ids = json.load(f)
except:
    pass

app = flask.Flask(__name__)

sock = flask_sock.Sock(app)

@sock.route("/ws")
def server(websocket):
    global down
    global pixels
    global gridSize
    if down:
        websocket.receive()
        # Send a very large number for the timer
        websocket.send("999999999")
        # Send the grid size
        websocket.send(str(gridSize))
        # Send all the pixels
        for pixel in pixels:
            websocket.send(pixel)
        # Wait for messages
        try:
            while True:
                websocket.receive()
        except:
            pass
        return
    global ids
    global logs
    global clients
    global timer
    # Get their ID
    log("New connection")
    id = websocket.receive()
    log("ID:", id)
    # Check if it's valid
    # (Theoretically)
    # Add them to the list of clients
    clients.add(websocket)
    log("Clients:", len(clients))
    # Send them the current state of the grid
    log("Sending timer")
    websocket.send(str(timer))
    # Send the time they have left until they can place another pixel, in seconds
    #websocket.send(str(timer - (time.time() - ids[id]))) # This line is broken... Why?
    #str(time.time() - ids[id]) # Will simply calculating what to send to the client cause problems?
    # Yes, it will. For whatever reason, this calculation causes the server to crash, which is caught, but still crashes the client, which causes it to relaunch, and we get a loop of crashing and relaunching.
    # So, what is failing..? Is it ids[id]?
    #ids[id]
    # Yes... It is. Why?
    # "KeyError: 'auth'"
    # Huh, the seever can't find the ID in the dictionary. Shouldn't it be set to time.time() when the ID is added?
    if id not in ids:
        log("New ID added")
        ids[id] = time.time()
        saveIds()
    # Now, let's try again
    websocket.send(str(timer - (time.time() - ids[id])))
    # Send the grid size
    log("Sending grid size")
    websocket.send(str(gridSize))
    if logs:
        print("Sending pixels: 0/" + str(len(pixels)), end=" (0%)")
        for i in range(len(pixels)):
            print("\rSending pixels: " + str(i) + "/" + str(len(pixels)) + " (" + str(round(i/len(pixels)*100)), end="%)")
            websocket.send(pixels[i])
        print()
    else:
        for pixel in pixels:
            websocket.send(pixel)
#    if id not in ids:
#        log("New ID added")
#        ids[id] = time.time()
#        saveIds()
#    else:
#        log("ID already exists")
    # Wait for messages
    try:
        while not down:
            message = websocket.receive()
            log("Message (", end=message)
            if down:
                log(") Ignored - server is down")
                return
            # Did they last send a message less than 5 minutes ago?
            if time.time() - ids[id] < timer:
                log(") Rate limited")
                ids[id] = time.time()
                return
            ids[id] = time.time()
            saveIds()
            try:
                # Parse the message
                data = json.loads(message)
                if "colour" in data:
                    data["color"] = data["colour"] # I'm Canadian, but the parsing below uses American spelling since it's slightly shorter
                # For performance reasons, pre-serialise the message
                message = json.dumps({"x": data["x"], "y": data["y"], "color": data["color"]})
                # Check if it's valid
                # Only supported colours are within 3 bits per pixel, that's one bit per channel,
                #00 or #ff for each channel.
                # The client will never send non-capitalised hex codes, but it's not technically invalid
                if "x" in data and "y" in data and "color" in data and data["color"][0] == "#" and data["color"][1:3] in ["00", "ff", "FF"] and data["color"][3:5] in ["00", "ff", "FF"] and data["color"][5:7] in ["00", "ff", "FF"]:
                    log(") Valid")
                    # Set the pixel
                    pixels.append(message)
                    savePixels()
                    # Send the message to all clients
                    if logs:
                        tolog = "\n"
                        print("Updating clients: 0/" + str(len(clients)), end=" (0%)")
                        for i, client in enumerate(clients):
                            print("\rUpdating clients: " + str(i + 1) + "/" + str(len(clients)) + " (" + str(round((i+1)/len(clients)*100)), end="%)")
                            try:
                                client.send(message)
                            except Exception as e:
                                #log("Failed to send to client - ", e.__class__.__name__, " ", str(e))
                                #log("Client index:", i)
                                tolog += "Failed to send to client " + str(i) + " - " + e.__class__.__name__ + " " + str(e) + "\nClient index: " + str(i) + "\n"
                        print(tolog)
                    else:
                        for client in clients:
                            # Why re-serialise the message when it's the same data that was sent?
                            client.send(message)
                else:
                    log(") Invalid")
                    # Close the connection
                    clients.remove(websocket)
                    return
            except Exception as e:
                log(") Failed")
                raise e
    except Exception as e:
        clients.remove(websocket)
        log("Connection closed - ", end=e.__class__.__name__)
        log(" ", str(e))

log("Starting server")
with open(index, "r") as f:
    index = f.read()
@app.route("/")
def root(): # Can't call it index because that's the name of the file
    #return flask.send_file(index)
    global down
    global index
    if down:
        return index, 100
    return index, 200
    #return flask.send_file(index, download_name="index.html")



@app.route("/boop")
def boop():
    global boops
    # Check the accept header and return a boop in the appropriate format
    accept = flask.request.headers.get("Accept", "")
    # Prioritise lossless compression, then lossless uncompressed, then lossy
    if len(boops) != 0:
        if "audio/ogg" in accept:
            # Find a .ogg boop
            for boop in boops:
                if boop.endswith(".ogg"):
                    return flask.send_file(boop)
        if "audio/wav" in accept:
            # Find a .wav boop
            for boop in boops:
                if boop.endswith(".wav"):
                    return flask.send_file(boop)
        if "audio/flac" in accept:
            # Find a .flac boop
            for boop in boops:
                if boop.endswith(".flac"):
                    return flask.send_file(boop)
        if "audio/aac" in accept:
            # Find a .aac boop
            for boop in boops:
                if boop.endswith(".aac"):
                    return flask.send_file(boop)
        if "audio/mpeg" in accept:
            # Find a .mp3 boop
            for boop in boops:
                if boop.endswith(".mp3"):
                    return flask.send_file(boop)
    # We have no boops that match what the client asked for, so here are some special cases
        if "audio/*" in accept or "*/*" in accept:
            # Find the first boop
            return flask.send_file(boops[0])
    if "text/html" in accept:
        # Return a page with a link to the boop
        return """<!DOCTYPE html><html><head><title>Boop</title></head><body><audio controls src="/boop"></audio></body></html>"""
    if "application/json" in accept:
        # Return *all* the boops
        return json.dumps(boops) # As this is outside the `if len(boops) != 0:` block, there is a possibility of returning an empty list ([]), which still perfectly valid and there is no need to fix it.
    if "text/plain" in accept:
        # Return "boop"
        response = flask.make_response("boop")
        response.headers["Content-Type"] = "text/plain"
        return response
    # Return a 406 Not Acceptable
    return "", 406

@app.route("/boop<string:ext>")
def boopExt(ext):
    global boops
    # Find a boop with the extension
    for boop in boops:
        if boop.endswith(ext):
            # I like caching
            return flask.send_file(boop, as_attachment=True, download_name="boop" + ext, max_age=3600)
    # Special cases
    if ext == ".html":
        # Return a page with a link to the boop
        return """<!DOCTYPE html><html><head><title>Boop</title></head><body><audio controls src="/boop"></audio></body></html>"""
    if ext == ".json":
        # Return *all* the boops
        return json.dumps(boops)
    if ext == ".txt":
        # Return "boop"
        response = flask.make_response("boop")
        response.headers["Content-Type"] = "text/plain"
        return response
    # Return a 404 Not Found
    return catchAll("boop" + ext)

# Catch all other requests
@app.route("/<path:path>")
def catchAll(path):
    response = flask.make_response("")
    response.status_code = 404
    # I like caching
    response.cache_control.max_age = 3600
    return response

app.run(host="0.0.0.0", port=port)
