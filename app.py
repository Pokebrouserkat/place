# Path to presistent storage folder, where pixels.json and ids.json are stored
path = "data"
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
# If true, refuse all pixel data outside of the canvas, otherwise allow it
restrict = True

#import websockets
#import asyncio
import flask
import flask_sock
import json
import time
import os

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
    # Wait for messages
    try:
        while True:
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
                if restrict:
                    # Check if it's more than gridSize away from the canvas in any direction
                    if data["x"] >= gridSize or data["y"] >= gridSize or data["x"] < -gridSize or data["y"] < -gridSize:
                        log(") Out of bounds")
                        # This is a hack to re-allow them to place a pixel
                        # Yeah, I could actually impliment a new message type, or better yet not even send the server invalid messages, but do I look like I would do that?
                        # (Don't answer that)
                        ids[id] -= timer
                        # Explicitly close the connection instead of just returning
                        clients.remove(websocket)
                        websocket.close()
                        return
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
def root():
    global down
    global index
    if down:
        return index, 100
    return index, 200

@app.route("/boop.mp3")
def boop():
    return flask.send_file(os.path.join(app.root_path, "boop.mp3")), 200

app.run(host="0.0.0.0", port=port)
