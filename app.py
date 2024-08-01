
# Path to presistent storage folder, where pixels.json and ids.json are stored
path = "~/Library/Mobile Documents/com~apple~CloudDocs/src/grid2/"
# size of the grid
gridSize = 50
# Whether to log everything for debugging purposes
logs = False
# Delay between pixel placements in seconds
timer = 60 * 5
# Port to run the server on
port = 8080

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
    with open("pixels.json", "w") as f:
        log("Saving pixels")
        json.dump(pixels, f)
def saveIds():
    with open("ids.json", "w") as f:
        log("Saving IDs")
        json.dump(ids, f)

try:
    with open("pixels.json", "r") as f:
        pixels = json.load(f)
except:
    pass
try:
    with open("ids.json", "r") as f:
        ids = json.load(f)
except:
    pass

app = flask.Flask(__name__)

sock = flask_sock.Sock(app)

#async def server(websocket, path):
@sock.route("/ws")
def server(websocket):
    global pixels
    global ids
    global gridSize
    global logs
    global clients
    global timer
    # Get their ID
    log("New connection")
    #id = await websocket.recv()
    id = websocket.receive()
    log("ID:", id)
    # Check if it's valid
    # (Theoretically)
    # Add them to the list of clients
    clients.add(websocket)
    log("Clients:", len(clients))
    # Send them the current state of the grid
    log("Sending timer")
    #await websocket.send(str(timer))
    websocket.send(str(timer))
    log("Sending grid size")
    #await websocket.send(str(gridSize))
    websocket.send(str(gridSize))
    if logs:
        print("Sending pixels: 0/" + str(len(pixels)), end=" (0%)")
        for i in range(len(pixels)):
            print("\rSending pixels: " + str(i) + "/" + str(len(pixels)) + " (" + str(round(i/len(pixels)*100)), end="%)")
            #await websocket.send(pixels[i])
            websocket.send(pixels[i])
        print()
    else:
        for pixel in pixels:
            #await websocket.send(pixel)
            websocket.send(pixel)
    if id not in ids:
        log("New ID added")
        ids[id] = time.time()
        saveIds()
    else:
        log("ID already exists")
    # Wait for messages
    try:
        #async for message in websocket:
        while True:
            message = websocket.receive()
            log("Message (", end=message)
            # Did they last send a message less than 5 minutes ago?
            # This is a sort of rate limit, it's kind of the whole game
            if time.time() - ids[id] < 300:
            #if time.time() - ids[id] < 5: # For testing, 5 seconds instead of 5 minutes
            #if False: # For testing, no rate limit
                log(") Rate limited")
                # Close the connection
                # Wait, let's still update the time so they can't just reconnect
                ids[id] = time.time()
                return
            ids[id] = time.time()
            saveIds()
            try:
                # Parse the message
                data = json.loads(message)
                # Check if it's valid
                # Only supported colours are within 3 bits per pixel, that's one bit per channel,
                #00 or #ff for each channel, and it never sends capital letters.
                if "x" in data and "y" in data and "color" in data and data["color"][0] == "#" and data["color"][1:3] in ["00", "ff"] and data["color"][3:5] in ["00", "ff"] and data["color"][5:7] in ["00", "ff"]:
                    log(") Valid")
                    # Set the pixel
                    pixels.append(message)
                    savePixels()
                    # Send the message to all clients
                    if logs:
                        print("Updating clients: 0/" + str(len(clients)), end=" (0%)")
                        for i, client in enumerate(clients):
                            print("\rUpdating clients: " + str(i + 1) + "/" + str(len(clients)) + " (" + str(round((i+1)/len(clients)*100)), end="%)")
                            #await client.send(message)
                            client.send(message)
                        print()
                    else:
                        for client in clients:
                            # Why re-serialise the message when it's the same data that was sent?
                            #await client.send(message)
                            client.send(message)
                else:
                    log(") Invalid")
                    # Close the connection
                    clients.remove(websocket)
                    return
            except Exception as e:
                log(") Failed")
                raise e # For clients.remove below
    except Exception as e:
        clients.remove(websocket)
        log("Connection closed - ", end=e.__class__.__name__)
        log(" ", str(e))

log("Starting server")
# LAST MINUTE FLASK APP
@app.route("/")
def index():
    #return """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Place</title><script>const ws=new WebSocket('ws://localhost:8080');const tileColors={};var canvasSize=50,rateLimit=-1;ws.onmessage=(e)=>{if(!isNaN(e.data)){if(rateLimit===-1){rateLimit=parseInt(e.data);return}canvasSize=parseInt(e.data);return}const data=JSON.parse(e.data);tileColors[`${data.x},${data.y}`]=data.color};ws.onclose=()=>{location.reload()};ws.onopen=()=>{ws.send(window.location.hash.substring(window.location.hash.indexOf('access_token=')+13).split('&')[0].split('/')[0])};window.location.hash='';var canvas,chosenColor=null,ctx,tileSize=20,zoom=1,offsetX=0,offsetY=0,selectedTile=null,keysPressed={},velocity={x:0,y:0},maxSpeed=10,acceleration=0.4,deceleration=0.8;function resizeCanvas(){canvas.width=window.innerWidth;canvas.height=window.innerHeight}function drawGrid(){ctx.clearRect(0,0,canvas.width,canvas.height);const cols=Math.ceil(canvas.width/(tileSize*zoom))+2,rows=Math.ceil(canvas.height/(tileSize*zoom))+2,startX=Math.floor(offsetX)-Math.floor(cols/2),startY=Math.floor(offsetY)-Math.floor(rows/2);ctx.fillStyle='#000000';ctx.fillRect(0,0,canvas.width,canvas.height);var tileSizeTimesZoom=tileSize*zoom,tileSizeTimesZoomMinusOne=(tileSize-1)*zoom,floorColsDiv2=cols>>1,floorRowsDiv2=rows>>1;for(let x=startX;x<startX+cols;x++)for(let y=startY;y<startY+rows;y++){const color=tileColors[`${x},${y}`]||((Math.abs(x)<canvasSize&&Math.abs(y)<canvasSize)?'#ffffff':'#000000');ctx.fillStyle=color;const drawX=(x-offsetX+floorColsDiv2)*tileSizeTimesZoom,drawY=(y-offsetY+floorRowsDiv2)*tileSizeTimesZoom;ctx.fillRect(drawX,drawY,tileSizeTimesZoomMinusOne,tileSizeTimesZoomMinusOne)}}function handleTileClick(x,y){if(chosenColor){const confirmChange=confirm("Change the tile colour?");if(confirmChange){ws.send(JSON.stringify({x:x-1,y:y-2,color:chosenColor}))}}}document.addEventListener('keydown',(e)=>{keysPressed[e.key]=true});document.addEventListener('keyup',(e)=>{keysPressed[e.key]=false});function updateOffset(){if(keysPressed['ArrowUp']&&!keysPressed['ArrowDown'])velocity.y=Math.max(velocity.y-acceleration,-maxSpeed);else if(keysPressed['ArrowDown']&&!keysPressed['ArrowUp'])velocity.y=Math.min(velocity.y+acceleration,maxSpeed);else velocity.y=Math.abs(velocity.y)<deceleration?0:velocity.y+(velocity.y>0?-deceleration:deceleration);if(keysPressed['ArrowLeft']&&!keysPressed['ArrowRight'])velocity.x=Math.max(velocity.x-acceleration,-maxSpeed);else if(keysPressed['ArrowRight']&&!keysPressed['ArrowLeft'])velocity.x=Math.min(velocity.x+acceleration,maxSpeed);else velocity.x=Math.abs(velocity.x)<deceleration?0:velocity.x+(velocity.x>0?-deceleration:deceleration);offsetX+=velocity.x/(tileSize*zoom);offsetY+=velocity.y/(tileSize*zoom)}function animate(){updateOffset();drawGrid();requestAnimationFrame(animate);window.location.hash=(offsetX||offsetY||zoom)?`#x=${offsetX}&y=${offsetY}&zoom=${zoom}`:''}window.addEventListener('wheel',(e)=>{e.preventDefault();const zoomFactor=1.1;e.deltaY>0?zoom/=zoomFactor:zoom*=zoomFactor;zoom=Math.max(0.1,Math.min(zoom,10))});window.addEventListener('resize',resizeCanvas);window.addEventListener('keydown',(e)=>{if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key))e.preventDefault()});function selectColour(button){const buttons=document.querySelectorAll('button');buttons.forEach((b)=>{b.classList.remove('selected')});button.classList.add('selected');switch(button.id){case 'red':chosenColor='#ff0000';break;case 'green':chosenColor='#00ff00';break;case 'blue':chosenColor='#0000ff';break;case 'yellow':chosenColor='#ffff00';break;case 'purple':chosenColor='#ff00ff';break;case 'cyan':chosenColor='#00ffff';break;case 'white':chosenColor='#ffffff';break;case 'black':chosenColor='#000000';break}}</script><style>body{margin:0;overflow:hidden;background-color:#eee}#colours{position:absolute;display:none}canvas{display:block}button{width:5vh;height:5vh;margin:0.5vh;border-radius:0;cursor:pointer;transition:all 0.1s}#red{background-color:#ff0000;border:0.5vh solid #aa0000}#green{background-color:#00ff00;border:0.5vh solid #00aa00}#blue{background-color:#0000ff;border:0.5vh solid #0000aa}#yellow{background-color:#ffff00;border:0.5vh solid #aaaa00}#purple{background-color:#ff00ff;border:0.5vh solid #aa00aa}#cyan{background-color:#00ffff;border:0.5vh solid #00aaaa}#white{background-color:#ffffff;border:0.5vh solid #aaaaaa}#black{background-color:#000000;border:0.5vh solid #333333}button:hover{transform:scale(1.1)}#red:active{box-shadow:0 0 1vh 1vh #aa0000}#green:active{box-shadow:0 0 1vh 1vh #00aa00}#blue:active{box-shadow:0 0 1vh 1vh #0000aa}#yellow:active{box-shadow:0 0 1vh 1vh #aaaa00}#purple:active{box-shadow:0 0 1vh 1vh #aa00aa}#cyan:active{box-shadow:0 0 1vh 1vh #00aaaa}#white:active{box-shadow:0 0 1vh 1vh #aaaaaa}#black:active{box-shadow:0 0 1vh 1vh #333333}#red.selected{box-shadow:0 0 0.5vh 0.5vh #aa0000}#green.selected{box-shadow:0 0 0.5vh 0.5vh #00aa00}#blue.selected{box-shadow:0 0 0.5vh 0.5vh #0000aa}#yellow.selected{box-shadow:0 0 0.5vh 0.5vh #aaaa00}#purple.selected{box-shadow:0 0 0.5vh 0.5vh #aa00aa}#cyan.selected{box-shadow:0 0 0.5vh 0.5vh #00aaaa}#white.selected{box-shadow:0 0 0.5vh 0.5vh #aaaaaa}#black.selected{box-shadow:0 0 0.5vh 0.5vh #333333}#colours{display:flex;flex-wrap:wrap;position:absolute;top:0;left:0;z-index:1}</style></head><body><div id="colours"><button onclick="selectColour(this)" id="red"></button><button onclick="selectColour(this)" id="green"></button><button onclick="selectColour(this)" id="blue"></button><button onclick="selectColour(this)" id="yellow"></button><button onclick="selectColour(this)" id="purple"></button><button onclick="selectColour(this)" id="cyan"></button><button onclick="selectColour(this)" id="white"></button><button onclick="selectColour(this)" id="black"></button></div><canvas id="canvas"></canvas><script>canvas=document.getElementById('canvas');ctx=canvas.getContext('2d');canvas.addEventListener('click',(e)=>{const rect=canvas.getBoundingClientRect(),mouseX=e.clientX-rect.left,mouseY=e.clientY-rect.top,x=Math.floor((mouseX/(tileSize*zoom))+offsetX-Math.floor(canvas.width/(tileSize*zoom)/2)),y=Math.floor((mouseY/(tileSize*zoom))+offsetY-Math.floor(canvas.height/(tileSize*zoom)/2));handleTileClick(x,y,e.clientX,e.clientY)});resizeCanvas();animate()</script></body></html>"""
    #return """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Place</title><script>const ws=new WebSocket('""" + ws_url + """');const tileColors={};var canvasSize=50,rateLimit=-1;ws.onmessage=(e)=>{if(!isNaN(e.data)){if(rateLimit===-1){rateLimit=parseInt(e.data);return}canvasSize=parseInt(e.data);return}const data=JSON.parse(e.data);tileColors[`${data.x},${data.y}`]=data.color};ws.onclose=()=>{location.reload()};ws.onopen=()=>{ws.send(window.location.hash.substring(window.location.hash.indexOf('access_token=')+13).split('&')[0].split('/')[0])};window.location.hash='';var canvas,chosenColor=null,ctx,tileSize=20,zoom=1,offsetX=0,offsetY=0,selectedTile=null,keysPressed={},velocity={x:0,y:0},maxSpeed=10,acceleration=0.4,deceleration=0.8;function resizeCanvas(){canvas.width=window.innerWidth;canvas.height=window.innerHeight}function drawGrid(){ctx.clearRect(0,0,canvas.width,canvas.height);const cols=Math.ceil(canvas.width/(tileSize*zoom))+2,rows=Math.ceil(canvas.height/(tileSize*zoom))+2,startX=Math.floor(offsetX)-Math.floor(cols/2),startY=Math.floor(offsetY)-Math.floor(rows/2);ctx.fillStyle='#000000';ctx.fillRect(0,0,canvas.width,canvas.height);var tileSizeTimesZoom=tileSize*zoom,tileSizeTimesZoomMinusOne=(tileSize-1)*zoom,floorColsDiv2=cols>>1,floorRowsDiv2=rows>>1;for(let x=startX;x<startX+cols;x++)for(let y=startY;y<startY+rows;y++){const color=tileColors[`${x},${y}`]||((Math.abs(x)<canvasSize&&Math.abs(y)<canvasSize)?'#ffffff':'#000000');ctx.fillStyle=color;const drawX=(x-offsetX+floorColsDiv2)*tileSizeTimesZoom,drawY=(y-offsetY+floorRowsDiv2)*tileSizeTimesZoom;ctx.fillRect(drawX,drawY,tileSizeTimesZoomMinusOne,tileSizeTimesZoomMinusOne)}}function handleTileClick(x,y){if(chosenColor){const confirmChange=confirm("Change the tile colour?");if(confirmChange){ws.send(JSON.stringify({x:x-1,y:y-2,color:chosenColor}))}}}document.addEventListener('keydown',(e)=>{keysPressed[e.key]=true});document.addEventListener('keyup',(e)=>{keysPressed[e.key]=false});function updateOffset(){if(keysPressed['ArrowUp']&&!keysPressed['ArrowDown'])velocity.y=Math.max(velocity.y-acceleration,-maxSpeed);else if(keysPressed['ArrowDown']&&!keysPressed['ArrowUp'])velocity.y=Math.min(velocity.y+acceleration,maxSpeed);else velocity.y=Math.abs(velocity.y)<deceleration?0:velocity.y+(velocity.y>0?-deceleration:deceleration);if(keysPressed['ArrowLeft']&&!keysPressed['ArrowRight'])velocity.x=Math.max(velocity.x-acceleration,-maxSpeed);else if(keysPressed['ArrowRight']&&!keysPressed['ArrowLeft'])velocity.x=Math.min(velocity.x+acceleration,maxSpeed);else velocity.x=Math.abs(velocity.x)<deceleration?0:velocity.x+(velocity.x>0?-deceleration:deceleration);offsetX+=velocity.x/(tileSize*zoom);offsetY+=velocity.y/(tileSize*zoom)}function animate(){updateOffset();drawGrid();requestAnimationFrame(animate);window.location.hash=(offsetX||offsetY||zoom)?`#x=${offsetX}&y=${offsetY}&zoom=${zoom}`:''}window.addEventListener('wheel',(e)=>{e.preventDefault();const zoomFactor=1.1;e.deltaY>0?zoom/=zoomFactor:zoom*=zoomFactor;zoom=Math.max(0.1,Math.min(zoom,10))});window.addEventListener('resize',resizeCanvas);window.addEventListener('keydown',(e)=>{if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key))e.preventDefault()});function selectColour(button){const buttons=document.querySelectorAll('button');buttons.forEach((b)=>{b.classList.remove('selected')});button.classList.add('selected');switch(button.id){case 'red':chosenColor='#ff0000';break;case 'green':chosenColor='#00ff00';break;case 'blue':chosenColor='#0000ff';break;case 'yellow':chosenColor='#ffff00';break;case 'purple':chosenColor='#ff00ff';break;case 'cyan':chosenColor='#00ffff';break;case 'white':chosenColor='#ffffff';break;case 'black':chosenColor='#000000';break}}</script><style>body{margin:0;overflow:hidden;background-color:#eee}#colours{position:absolute;display:none}canvas{display:block}button{width:5vh;height:5vh;margin:0.5vh;border-radius:0;cursor:pointer;transition:all 0.1s}#red{background-color:#ff0000;border:0.5vh solid #aa0000}#green{background-color:#00ff00;border:0.5vh solid #00aa00}#blue{background-color:#0000ff;border:0.5vh solid #0000aa}#yellow{background-color:#ffff00;border:0.5vh solid #aaaa00}#purple{background-color:#ff00ff;border:0.5vh solid #aa00aa}#cyan{background-color:#00ffff;border:0.5vh solid #00aaaa}#white{background-color:#ffffff;border:0.5vh solid #aaaaaa}#black{background-color:#000000;border:0.5vh solid #333333}button:hover{transform:scale(1.1)}#red:active{box-shadow:0 0 1vh 1vh #aa0000}#green:active{box-shadow:0 0 1vh 1vh #00aa00}#blue:active{box-shadow:0 0 1vh 1vh #0000aa}#yellow:active{box-shadow:0 0 1vh 1vh #aaaa00}#purple:active{box-shadow:0 0 1vh 1vh #aa00aa}#cyan:active{box-shadow:0 0 1vh 1vh #00aaaa}#white:active{box-shadow:0 0 1vh 1vh #aaaaaa}#black:active{box-shadow:0 0 1vh 1vh #333333}#red.selected{box-shadow:0 0 0.5vh 0.5vh #aa0000}#green.selected{box-shadow:0 0 0.5vh 0.5vh #00aa00}#blue.selected{box-shadow:0 0 0.5vh 0.5vh #0000aa}#yellow.selected{box-shadow:0 0 0.5vh 0.5vh #aaaa00}#purple.selected{box-shadow:0 0 0.5vh 0.5vh #aa00aa}#cyan.selected{box-shadow:0 0 0.5vh 0.5vh #00aaaa}#white.selected{box-shadow:0 0 0.5vh 0.5vh #aaaaaa}#black.selected{box-shadow:0 0 0.5vh 0.5vh #333333}#colours{display:flex;flex-wrap:wrap;position:absolute;top:0;left:0;z-index:1}</style></head><body><div id="colours"><button onclick="selectColour(this)" id="red"></button><button onclick="selectColour(this)" id="green"></button><button onclick="selectColour(this)" id="blue"></button><button onclick="selectColour(this)" id="yellow"></button><button onclick="selectColour(this)" id="purple"></button><button onclick="selectColour(this)" id="cyan"></button><button onclick="selectColour(this)" id="white"></button><button onclick="selectColour(this)" id="black"></button></div><canvas id="canvas"></canvas><script>canvas=document.getElementById('canvas');ctx=canvas.getContext('2d');canvas.addEventListener('click',(e)=>{const rect=canvas.getBoundingClientRect(),mouseX=e.clientX-rect.left,mouseY=e.clientY-rect.top,x=Math.floor((mouseX/(tileSize*zoom))+offsetX-Math.floor(canvas.width/(tileSize*zoom)/2)),y=Math.floor((mouseY/(tileSize*zoom))+offsetY-Math.floor(canvas.height/(tileSize*zoom)/2));handleTileClick(x,y,e.clientX,e.clientY)});resizeCanvas();animate()</script></body></html>"""
    return """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Place</title><script>const ws=new WebSocket('/ws');const tileColors={};var canvasSize=50,rateLimit=-1;ws.onmessage=(e)=>{if(!isNaN(e.data)){if(rateLimit===-1){rateLimit=parseInt(e.data);return}canvasSize=parseInt(e.data);return}const data=JSON.parse(e.data);tileColors[`${data.x},${data.y}`]=data.color};ws.onclose=()=>{location.reload()};ws.onopen=()=>{ws.send(window.location.hash.substring(window.location.hash.indexOf('access_token=')+13).split('&')[0].split('/')[0])};window.location.hash='';var canvas,chosenColor=null,ctx,tileSize=20,zoom=1,offsetX=0,offsetY=0,selectedTile=null,keysPressed={},velocity={x:0,y:0},maxSpeed=10,acceleration=0.4,deceleration=0.8;function resizeCanvas(){canvas.width=window.innerWidth;canvas.height=window.innerHeight}function drawGrid(){ctx.clearRect(0,0,canvas.width,canvas.height);const cols=Math.ceil(canvas.width/(tileSize*zoom))+2,rows=Math.ceil(canvas.height/(tileSize*zoom))+2,startX=Math.floor(offsetX)-Math.floor(cols/2),startY=Math.floor(offsetY)-Math.floor(rows/2);ctx.fillStyle='#000000';ctx.fillRect(0,0,canvas.width,canvas.height);var tileSizeTimesZoom=tileSize*zoom,tileSizeTimesZoomMinusOne=(tileSize-1)*zoom,floorColsDiv2=cols>>1,floorRowsDiv2=rows>>1;for(let x=startX;x<startX+cols;x++)for(let y=startY;y<startY+rows;y++){const color=tileColors[`${x},${y}`]||((Math.abs(x)<canvasSize&&Math.abs(y)<canvasSize)?'#ffffff':'#000000');ctx.fillStyle=color;const drawX=(x-offsetX+floorColsDiv2)*tileSizeTimesZoom,drawY=(y-offsetY+floorRowsDiv2)*tileSizeTimesZoom;ctx.fillRect(drawX,drawY,tileSizeTimesZoomMinusOne,tileSizeTimesZoomMinusOne)}}function handleTileClick(x,y){if(chosenColor){const confirmChange=confirm("Change the tile colour?");if(confirmChange){ws.send(JSON.stringify({x:x-1,y:y-2,color:chosenColor}))}}}document.addEventListener('keydown',(e)=>{keysPressed[e.key]=true});document.addEventListener('keyup',(e)=>{keysPressed[e.key]=false});function updateOffset(){if(keysPressed['ArrowUp']&&!keysPressed['ArrowDown'])velocity.y=Math.max(velocity.y-acceleration,-maxSpeed);else if(keysPressed['ArrowDown']&&!keysPressed['ArrowUp'])velocity.y=Math.min(velocity.y+acceleration,maxSpeed);else velocity.y=Math.abs(velocity.y)<deceleration?0:velocity.y+(velocity.y>0?-deceleration:deceleration);if(keysPressed['ArrowLeft']&&!keysPressed['ArrowRight'])velocity.x=Math.max(velocity.x-acceleration,-maxSpeed);else if(keysPressed['ArrowRight']&&!keysPressed['ArrowLeft'])velocity.x=Math.min(velocity.x+acceleration,maxSpeed);else velocity.x=Math.abs(velocity.x)<deceleration?0:velocity.x+(velocity.x>0?-deceleration:deceleration);offsetX+=velocity.x/(tileSize*zoom);offsetY+=velocity.y/(tileSize*zoom)}function animate(){updateOffset();drawGrid();requestAnimationFrame(animate);window.location.hash=(offsetX||offsetY||zoom)?`#x=${offsetX}&y=${offsetY}&zoom=${zoom}`:''}window.addEventListener('wheel',(e)=>{e.preventDefault();const zoomFactor=1.1;e.deltaY>0?zoom/=zoomFactor:zoom*=zoomFactor;zoom=Math.max(0.1,Math.min(zoom,10))});window.addEventListener('resize',resizeCanvas);window.addEventListener('keydown',(e)=>{if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key))e.preventDefault()});function selectColour(button){const buttons=document.querySelectorAll('button');buttons.forEach((b)=>{b.classList.remove('selected')});button.classList.add('selected');switch(button.id){case 'red':chosenColor='#ff0000';break;case 'green':chosenColor='#00ff00';break;case 'blue':chosenColor='#0000ff';break;case 'yellow':chosenColor='#ffff00';break;case 'purple':chosenColor='#ff00ff';break;case 'cyan':chosenColor='#00ffff';break;case 'white':chosenColor='#ffffff';break;case 'black':chosenColor='#000000';break}}</script><style>body{margin:0;overflow:hidden;background-color:#eee}#colours{position:absolute;display:none}canvas{display:block}button{width:5vh;height:5vh;margin:0.5vh;border-radius:0;cursor:pointer;transition:all 0.1s}#red{background-color:#ff0000;border:0.5vh solid #aa0000}#green{background-color:#00ff00;border:0.5vh solid #00aa00}#blue{background-color:#0000ff;border:0.5vh solid #0000aa}#yellow{background-color:#ffff00;border:0.5vh solid #aaaa00}#purple{background-color:#ff00ff;border:0.5vh solid #aa00aa}#cyan{background-color:#00ffff;border:0.5vh solid #00aaaa}#white{background-color:#ffffff;border:0.5vh solid #aaaaaa}#black{background-color:#000000;border:0.5vh solid #333333}button:hover{transform:scale(1.1)}#red:active{box-shadow:0 0 1vh 1vh #aa0000}#green:active{box-shadow:0 0 1vh 1vh #00aa00}#blue:active{box-shadow:0 0 1vh 1vh #0000aa}#yellow:active{box-shadow:0 0 1vh 1vh #aaaa00}#purple:active{box-shadow:0 0 1vh 1vh #aa00aa}#cyan:active{box-shadow:0 0 1vh 1vh #00aaaa}#white:active{box-shadow:0 0 1vh 1vh #aaaaaa}#black:active{box-shadow:0 0 1vh 1vh #333333}#red.selected{box-shadow:0 0 0.5vh 0.5vh #aa0000}#green.selected{box-shadow:0 0 0.5vh 0.5vh #00aa00}#blue.selected{box-shadow:0 0 0.5vh 0.5vh #0000aa}#yellow.selected{box-shadow:0 0 0.5vh 0.5vh #aaaa00}#purple.selected{box-shadow:0 0 0.5vh 0.5vh #aa00aa}#cyan.selected{box-shadow:0 0 0.5vh 0.5vh #00aaaa}#white.selected{box-shadow:0 0 0.5vh 0.5vh #aaaaaa}#black.selected{box-shadow:0 0 0.5vh 0.5vh #333333}#colours{display:flex;flex-wrap:wrap;position:absolute;top:0;left:0;z-index:1}</style></head><body><div id="colours"><button onclick="selectColour(this)" id="red"></button><button onclick="selectColour(this)" id="green"></button><button onclick="selectColour(this)" id="blue"></button><button onclick="selectColour(this)" id="yellow"></button><button onclick="selectColour(this)" id="purple"></button><button onclick="selectColour(this)" id="cyan"></button><button onclick="selectColour(this)" id="white"></button><button onclick="selectColour(this)" id="black"></button></div><canvas id="canvas"></canvas><script>canvas=document.getElementById('canvas');ctx=canvas.getContext('2d');canvas.addEventListener('click',(e)=>{const rect=canvas.getBoundingClientRect(),mouseX=e.clientX-rect.left,mouseY=e.clientY-rect.top,x=Math.floor((mouseX/(tileSize*zoom))+offsetX-Math.floor(canvas.width/(tileSize*zoom)/2)),y=Math.floor((mouseY/(tileSize*zoom))+offsetY-Math.floor(canvas.height/(tileSize*zoom)/2));handleTileClick(x,y,e.clientX,e.clientY)});resizeCanvas();animate()</script></body></html>"""
#threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 8080}).start()

#start_server = websockets.serve(server, "localhost", 8080)
#asyncio.get_event_loop().run_until_complete(start_server)
#asyncio.get_event_loop().run_forever()

app.run(host="0.0.0.0", port=port)
